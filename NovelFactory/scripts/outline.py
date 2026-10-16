# -*- coding: utf-8 -*-
"""大纲 Agent：全书总纲 → 卷大纲 → 单章细纲。输出到 plot/ 目录并等待人工确认。"""
from __future__ import annotations

from pathlib import Path
from typing import List

from ..agents.prompts import agent_outline
from ..core.engine import NovelFactoryEngine
from ..core.utils import save_text


def generate_full_outline(engine: NovelFactoryEngine, premise: str) -> str:
    cfg = engine.config["novel"]
    user = (
        f"小说基础设定：\n书名：{cfg['title']}\n题材：{cfg['genre']}\n"
        f"文风：{cfg['tone']}\n目标单章字数：{cfg['chapter_word_count']}\n\n"
        f"作者补充：{premise}\n\n"
        f"请先生成《全书总大纲》并写入 markdown。"
    )
    out = engine.call_llm(agent_outline(), user, 0.6)
    save_text(engine.workspace / "plot" / "full_outline.md", out.strip())
    return out.strip()


def generate_volume(engine: NovelFactoryEngine, volume_no: int = 1) -> str:
    cfg = engine.config["novel"]
    outline = (engine.workspace / "plot" / "full_outline.md")
    outline_text = outline.read_text(encoding="utf-8") if outline.exists() else "（总纲未生成）"
    user = (
        f"《{cfg['title']}》全书总纲如下：\n{outline_text}\n\n"
        f"请基于总纲生成第 {volume_no} 卷大纲（本卷目标/主要冲突/登场新人物/本卷高潮/卷收尾钩子），"
        f"写入 markdown。只规划 1~2 卷，不写太远细节。"
    )
    out = engine.call_llm(agent_outline(), user, 0.6)
    save_text(engine.workspace / "plot" / f"volume{volume_no}.md", out.strip())
    return out.strip()


def generate_chapter_plans(engine: NovelFactoryEngine, start: int, end: int,
                           volume_no: int = 1) -> List[str]:
    """批量生成单章细纲。每章 4 块：本章目标/核心冲突/爽点/结尾钩子。"""
    cfg = engine.config["novel"]
    vol_text = (engine.workspace / "plot" / f"volume{volume_no}.md")
    vol = vol_text.read_text(encoding="utf-8") if vol_text.exists() else "（卷大纲未生成）"
    created: List[str] = []

    for no in range(start, end + 1):
        ch_id = f"ch{no:03d}"
        out_path = engine.workspace / "plot" / "chapter_plans" / f"{ch_id}_plan.md"
        if out_path.exists():
            created.append(out_path.name)
            continue
        user = (
            f"《{cfg['title']}》第 {volume_no} 卷大纲：\n{vol}\n\n"
            f"请生成第 {no} 章单章细纲，严格包含四块：本章目标 / 核心冲突 / 爽点或情绪点 / 结尾钩子，"
            f"200~400 字，必须有明确冲突，禁止流水账，并输出【大纲校验报告】检查与前面章节的逻辑矛盾。"
        )
        out = engine.call_llm(agent_outline(), user, 0.5)
        save_text(out_path, out.strip())
        created.append(out_path.name)
        print(f"  ✅ {out_path.name} 已生成")
    return created


def outline_all(engine: NovelFactoryEngine, premise: str, start: int = 1,
                end: int = 5, volume_no: int = 1) -> None:
    print("① 生成全书总纲…")
    generate_full_outline(engine, premise)
    print("② 生成卷大纲…")
    generate_volume(engine, volume_no)
    print("③ 批量生成单章细纲…")
    generate_chapter_plans(engine, start, end, volume_no)
    print(f"\n✅ 大纲生成完毕（第 {start}~{end} 章细纲）。请人工审阅 plot/ 下大纲，确认后再启动流水线。")
