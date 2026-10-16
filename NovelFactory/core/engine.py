# -*- coding: utf-8 -*-
"""NovelFactory 核心引擎：上下文组装 → LLM 写作 → 审稿 → 记忆更新 → 落盘。

- 文件优先：设定/大纲/章节/记忆全部存 md 文件，按需加载，杜绝吃书。
- 双后端：provider=ollama（本地默认）或 openai（OpenAI 兼容接口）。
- 零第三方依赖（标准库 urllib / sqlite3 / re）。
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from .database import NovelDB
from .models import ChapterPlan, ReviewReport, list_chapter_ids
from .utils import (append_text, load_config, read_text, save_text, tail,
                    word_count)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "prompts"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


class NovelFactoryEngine:
    def __init__(self, workspace: str | Path, dry_run: bool = False):
        self.workspace = Path(workspace)
        self.config = load_config(self.workspace)
        self.dry_run = dry_run
        self.db = NovelDB(self.workspace)
        self.manuscript_dir = self.workspace / "manuscript"
        self.plans_dir = self.workspace / "plot" / "chapter_plans"
        self._ctx_cache: Dict[int, Dict[str, Any]] = {}

    # ---------------------------------------------------------------- 上下文
    def _read_prompt(self, name: str) -> str:
        p = PROMPTS_DIR / name
        return read_text(p).strip()

    def load_context(self, chapter_no: int) -> Dict[str, Any]:
        """按需加载第 N 章写作上下文：细纲 + 出场人物 + 记忆 + 上一章结尾。

        记忆裁剪（控制 prompt 长度、提速）：
        - 时间线只取最近 N 章（config memory.timeline_recent_n，默认 15）
        - 伏笔清单只保留【未回收】条目（已回收的不再进入上下文）
        - 人物档案按细纲提及的人名过滤，细纲未提及时才全量加载
        """
        if chapter_no in self._ctx_cache:
            return self._ctx_cache[chapter_no]

        ch_id = f"ch{chapter_no:03d}"
        plan_path = self.plans_dir / f"{ch_id}_plan.md"
        plan = ChapterPlan.load(plan_path)

        characters: List[str] = []
        chars_dir = self.workspace / "characters"
        if chars_dir.exists():
            char_files = sorted(chars_dir.glob("*.md"))
            plan_brief = plan.brief
            mentioned = [p for p in char_files if p.stem in plan_brief]
            selected = mentioned if mentioned else char_files
            for p in selected:
                characters.append(f"### {p.stem}\n{read_text(p).strip()}")

        memory = ""
        mem_dir = self.workspace / "memory"
        mcfg = self.config.get("memory", {})
        recent_n = int(mcfg.get("timeline_recent_n", 15))
        timeline = _recent_timeline(read_text(mem_dir / "timeline.md").strip(), recent_n)
        foreshadow = _active_foreshadow(read_text(mem_dir / "foreshadow.md").strip())
        if timeline:
            memory += f"【时间线】\n{timeline}\n"
        if foreshadow:
            memory += f"\n【伏笔清单】（仅未回收）\n{foreshadow}\n"

        prev_id = f"ch{chapter_no - 1:03d}"
        prev_text = read_text(self.manuscript_dir / f"{prev_id}.md")
        prev_tail = tail(prev_text, 600) if prev_text else "（这是第一章，无前文）"

        ctx = {
            "chapter_id": ch_id,
            "chapter_no": chapter_no,
            "plan": plan,
            "characters": "\n\n".join(characters),
            "memory": memory,
            "prev_tail": prev_tail,
            "world": read_text(self.workspace / "world.md").strip(),
        }
        self._ctx_cache[chapter_no] = ctx
        return ctx

    # ---------------------------------------------------------------- LLM
    def call_llm(self, system: str, user: str, temperature: float) -> str:
        """调用后端 LLM。ollama 用 /api/chat，openai 用 /v1/chat/completions。"""
        if self.dry_run:
            return "[dry-run] 模拟模型输出：未实际调用后端。"
        provider = self.config["llm"]["provider"].lower()
        base = self.config["llm"]["base_url"].rstrip("/")
        model = self.config["llm"]["model"]
        timeout = int(self.config["llm"].get("timeout", 300))
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        headers: dict = {}
        if provider == "ollama":
            url = f"{base}/api/chat"
            # think=False 关闭 Qwen3 系列思考模式，显著提速（否则每次先输出大段思考链）
            # num_ctx / keep_alive 可配：keep_alive 避免模型反复卸载加载（加载一次 10~30s）
            options = {"temperature": temperature}
            num_ctx = self.config["llm"].get("num_ctx")
            if num_ctx:
                options["num_ctx"] = int(num_ctx)
            body = {"model": model, "messages": messages, "stream": False,
                    "think": False, "options": options}
            keep_alive = self.config["llm"].get("keep_alive")
            if keep_alive:
                body["keep_alive"] = keep_alive
        elif provider in ("openai", "openai-compatible", "codex"):
            url = f"{base}/v1/chat/completions"
            # API Key 优先级：config.toml 的 [llm].api_key > 环境变量 NVIDIA_API_KEY / OPENAI_API_KEY / CODEX_API_KEY
            key = (str(self.config["llm"].get("api_key") or "").strip()
                   or os.environ.get("NVIDIA_API_KEY")
                   or os.environ.get("OPENAI_API_KEY")
                   or os.environ.get("CODEX_API_KEY") or "")
            body = {"model": model, "messages": messages,
                    "temperature": temperature, "stream": False}
            headers = {"Authorization": f"Bearer {key}"} if key else {}
        else:
            raise ValueError(f"未知 provider: {provider}")

        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"LLM HTTP {e.code}: {detail}") from e

        if provider == "ollama":
            return payload.get("message", {}).get("content", "").strip()
        return payload["choices"][0]["message"]["content"].strip()

    # ---------------------------------------------------------------- 主笔
    def generate_chapter(self, chapter_no: int) -> str:
        ctx = self.load_context(chapter_no)
        cfg = self.config["novel"]
        writer_prompt = self._read_prompt("agent_writer.md")
        user = (
            f"请为《{cfg['title']}》（{cfg['genre']}）写作第 {ctx['chapter_no']} 章正文。\n\n"
            f"目标字数：{cfg['chapter_word_count']} 字左右（允许 ±{int(cfg['word_tolerance'] * 100)}%）。\n"
            f"文风要求：{cfg['tone']}\n\n"
            f"===== 本章细纲 =====\n{ctx['plan'].brief}\n\n"
            f"===== 出场人物档案 =====\n{ctx['characters'] or '（暂无人物档案）'}\n\n"
            f"===== 世界观 =====\n{ctx['world'] or '（暂无）'}\n\n"
            f"===== 记忆（时间线/伏笔） =====\n{ctx['memory'] or '（暂无记忆）'}\n\n"
            f"===== 上一章结尾 =====\n{ctx['prev_tail']}\n\n"
            f"输出要求：只输出本章正文（可含章节标题），不要输出细纲、不要输出解释。"
        )
        content = self.call_llm(
            writer_prompt,
            user,
            float(self.config["llm"]["temperature_write"]),
        )
        return content.strip()

    # ---------------------------------------------------------------- 审稿
    def review_chapter(self, chapter_no: int, content: str) -> ReviewReport:
        if self.dry_run:
            return ReviewReport(verdict=ReviewReport.REVIEW_PASS,
                                problems="", report="[dry-run] 审稿模拟通过。")
        ctx = self.load_context(chapter_no)
        cfg = self.config["novel"]
        reviewer_prompt = self._read_prompt("agent_reviewer.md")
        expected = int(cfg["chapter_word_count"])
        user = (
            f"请审核《{cfg['title']}》第 {ctx['chapter_no']} 章。\n\n"
            f"目标字数：{expected}（当前字数：{word_count(content)}）\n\n"
            f"===== 本章细纲 =====\n{ctx['plan'].brief}\n\n"
            f"===== 人物档案 =====\n{ctx['characters'] or '（暂无）'}\n\n"
            f"===== 记忆 =====\n{ctx['memory'] or '（暂无）'}\n\n"
            f"===== 本章正文 =====\n{content}\n\n"
            f"输出格式：先输出【判定】通过|重写|人工，再输出《审稿报告》（人设/设定/文字/结构四项）。"
        )
        raw = self.call_llm(
            reviewer_prompt,
            user,
            float(self.config["llm"]["temperature_review"]),
        )
        report = ReviewReport.parse(raw)
        # 硬性字数校验：严重不足直接判重写
        if word_count(content) < expected * 0.5 and report.passed:
            report = ReviewReport(
                verdict=ReviewReport.REVIEW_REWRITE,
                problems=f"字数严重不足（{word_count(content)}/{expected}）",
                report=raw.strip(),
            )
        return report

    # ---------------------------------------------------------------- 记忆
    def update_memory(self, chapter_no: int, content: str) -> None:
        if self.dry_run:
            return
        ctx = self.load_context(chapter_no)
        memory_prompt = self._read_prompt("agent_memory.md")
        foreshadow_path = self.workspace / "memory" / "foreshadow.md"
        existing = read_text(foreshadow_path).strip()
        user = (
            f"请处理《{self.config['novel']['title']}》第 {ctx['chapter_no']} 章的记忆更新。\n\n"
            f"===== 本章正文 =====\n{content}\n\n"
            f"===== 现有伏笔清单 =====\n{existing or '（暂无）'}\n\n"
            f"按三段格式输出：时间线 / 伏笔-新增 / 伏笔-回收。"
        )
        extracted = self.call_llm(memory_prompt, user, 0.1)
        # 剥离标题标记，按内容块分别处理：时间线追加、新增伏笔追加、回收伏笔标记旧条目
        timeline_block, new_foreshadow, resolved = _split_memory_output(extracted)
        ch_id = ctx["chapter_id"]
        if timeline_block:
            append_text(self.workspace / "memory" / "timeline.md",
                        f"\n> {ch_id}\n" + _indent_quote(timeline_block))
        if new_foreshadow:
            append_text(foreshadow_path,
                        f"\n> {ch_id}\n> 【伏笔】\n" + _indent_quote(new_foreshadow))
        if resolved:
            marked = _mark_foreshadow_resolved(foreshadow_path, resolved)
            print(f"  🔗 伏笔回收：已标记 {marked} 条【未回收】→【已回收】")

    # ---------------------------------------------------------------- 流水线
    def run_pipeline(self, start: int | None = None, end: int | None = None,
                     max_retry: int | None = None) -> Dict[str, Any]:
        """章节生产主循环：写作 → 审稿 → （重写至多1次）→ 记忆更新 → 落盘。"""
        pcfg = self.config["pipeline"]
        start = start or int(pcfg.get("start", 1))
        end = end or int(pcfg.get("end", 5))
        max_retry = max_retry if max_retry is not None else int(pcfg.get("max_retry", 1))
        results: List[str] = []

        print(f"\n===== NovelFactory 流水线：第 {start} ~ {end} 章 =====\n")
        for no in range(start, end + 1):
            ch_id = f"ch{no:03d}"
            out_path = self.manuscript_dir / f"{ch_id}.md"

            if out_path.exists():
                print(f"⏭  {ch_id} 已存在，跳过（断点续跑）")
                results.append(f"{ch_id}:跳过")
                continue

            print(f"--- 开始 {ch_id} ---")
            plan = self.load_context(no)["plan"]
            if not plan.is_valid:
                print(f"  ❌ {ch_id}_plan.md 细纲缺失或无效，请先运行 outline 生成细纲。终止循环。")
                results.append(f"{ch_id}:缺细纲")
                break

            content = self.generate_chapter(no)
            if self.dry_run:
                # dry-run 只演示链路，不落盘（避免污染手稿导致真实运行时被跳过）
                print(f"  ✍ [dry-run] 已生成初稿，{word_count(content)} 字（未调用模型、未写入 manuscript）")
                print(f"    示例内容预览：{content[:60]}…")
                report = self.review_chapter(no, content)
                print(f"  ✅ [dry-run] 审稿模拟通过，将更新记忆 → {ch_id} 完成（不落盘）\n")
                results.append(f"{ch_id}:dry-run完成")
                continue

            self.db.set_chapter(ch_id, "写作中")
            save_text(out_path, content)
            self.db.set_chapter(ch_id, "审稿中", words=word_count(content))
            print(f"  ✍ 已生成初稿，{word_count(content)} 字")

            report = self.review_chapter(no, content)
            retried = 0
            while report.needs_manual or (report.verdict == ReviewReport.REVIEW_REWRITE and retried < max_retry):
                if report.needs_manual:
                    break
                retried += 1
                print(f"  ⚠ 审稿未通过（{report.problems[:80]}），第 {retried} 次重写…")
                content = self._rewrite(no, content, report.problems)
                save_text(out_path, content)
                report = self.review_chapter(no, content)

            if report.needs_manual:
                self.db.set_chapter(ch_id, "需人工复审", words=word_count(content),
                                    retries=retried, note=report.problems[:200])
                self.db.log(ch_id, "manual_review", report.problems[:500])
                print(f"  ❌ {ch_id} 需人工复审：{report.problems[:120]}\n    停止自动流水线（可从下一章或本章重跑）。")
                results.append(f"{ch_id}:需人工复审")
                break

            self.update_memory(no, content)
            self.db.set_chapter(ch_id, "完成", words=word_count(content),
                                retries=retried, note="审核通过")
            self.db.log(ch_id, "done", f"{word_count(content)}字")
            print(f"  ✅ {ch_id} 完成（{word_count(content)} 字，重写 {retried} 次），记忆已更新\n")

        self.db.log("", "pipeline", f"start={start} end={end} dry_run={self.dry_run}")
        return {"results": results}

    def _rewrite(self, chapter_no: int, old_content: str, problems: str) -> str:
        ctx = self.load_context(chapter_no)
        cfg = self.config["novel"]
        writer_prompt = self._read_prompt("agent_writer.md")
        user = (
            f"请根据审稿意见重写《{cfg['title']}》第 {ctx['chapter_no']} 章。\n\n"
            f"目标字数：{cfg['chapter_word_count']} 字左右。\n"
            f"文风：{cfg['tone']}\n\n"
            f"===== 本章细纲 =====\n{ctx['plan'].brief}\n\n"
            f"===== 人物档案 =====\n{ctx['characters'] or '（暂无）'}\n\n"
            f"===== 上一版正文 =====\n{old_content}\n\n"
            f"===== 审稿问题清单 =====\n{problems}\n\n"
            f"输出要求：只输出重写后的完整章节正文，修复以上全部问题，保留有效剧情。"
        )
        return self.call_llm(writer_prompt, user,
                             float(self.config["llm"]["temperature_write"])).strip()

    def close(self) -> None:
        self.db.close()


def _split_memory_output(text: str):
    """把记忆 Agent 输出拆成 (时间线块, 新增伏笔块, 已回收伏笔块) 三段。"""
    timeline, new_fs, resolved = [], [], []
    target = None
    for raw in text.splitlines():
        s = raw.strip().lstrip(">").strip()
        if not s:
            continue
        if re.match(r"^ch\d{3}$", s):
            continue  # 章节标记行由引擎重新生成，不重复携带
        if "时间线" in s and len(s) <= 12:
            target = timeline
            continue
        if ("伏笔-新增" in s or "新增伏笔" in s or s == "【伏笔】") and len(s) <= 12:
            target = new_fs
            continue
        if "伏笔-回收" in s and len(s) <= 12:
            target = resolved
            continue
        if s.startswith("回收"):
            target = resolved
        if target is not None:
            target.append(s)
    return "\n".join(timeline), "\n".join(new_fs), "\n".join(resolved)


def _mark_foreshadow_resolved(path: Path, resolved_block: str) -> int:
    """把 foreshadow.md 中与回收描述匹配的旧伏笔条目由【未回收】改为【已回收】。

    匹配策略：回收描述关键词与旧条目内容做双向子串匹配
    （模型可能复述原伏笔，也可能只给核心关键词）。返回标记条数。
    """
    pending: List[str] = []
    for ln in resolved_block.splitlines():
        s = ln.strip().lstrip(">").strip()
        if s.startswith("回收"):
            kw = re.split(r"[：:]", s, maxsplit=1)[-1].strip()
            if kw:
                pending.append(kw)
    if not pending:
        return 0
    text = read_text(path)
    if not text:
        return 0
    out_lines: List[str] = []
    marked = 0
    unmatched: List[str] = []
    for ln in text.splitlines():
        if "伏笔：" in ln and "【未回收】" in ln and pending:
            core = ln.split("伏笔：", 1)[1].replace("【未回收】", "").strip()
            hit = next((i for i, kw in enumerate(pending)
                        if kw in core or core[:12] in kw), None)
            if hit is not None:
                ln = ln.replace("【未回收】", "【已回收】")
                marked += 1
                pending.pop(hit)
            else:
                unmatched.append(ln.strip())
        out_lines.append(ln)
    if pending:
        unmatched.extend(pending)
    if marked:
        save_text(path, "\n".join(out_lines))
    if unmatched:
        print(f"  ⚠ 伏笔回收：{len(unmatched)} 条未在清单中匹配到旧条目，需人工核对："
              f"{'；'.join(u[:40] for u in unmatched[:5])}")
    return marked


def _recent_timeline(text: str, n: int) -> str:
    """把 timeline.md 裁剪为最近 n 个章节块（保留文件头部注释）。"""
    if not text:
        return ""
    marker = re.compile(r"(?m)^> ch\d{3}\s*$")
    matches = list(marker.finditer(text))
    if len(matches) <= n:
        return text
    head = text[: matches[0].start()].rstrip()
    return head + "\n" + text[matches[-n].start():].strip()


def _active_foreshadow(text: str) -> str:
    """只保留未回收伏笔条目（【已回收】条目不进上下文，仅留历史记录）。"""
    if not text:
        return ""
    lines = []
    for ln in text.splitlines():
        if "伏笔：" in ln and "【已回收】" in ln:
            continue
        lines.append(ln)
    return "\n".join(lines).strip()


def _indent_quote(block: str) -> str:
    return "\n".join(f"> {ln}" for ln in block.splitlines()) + "\n"
