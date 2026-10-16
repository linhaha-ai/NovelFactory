# -*- coding: utf-8 -*-
"""数据模型：章节细纲解析、审稿报告、章节状态。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .utils import read_text

REVIEW_PASS = "通过"
REVIEW_REWRITE = "重写"
REVIEW_MANUAL = "人工"


@dataclass
class ChapterPlan:
    """一章细纲：目标/冲突/爽点/结尾钩子。"""

    chapter_no: int
    chapter_id: str
    goal: str = ""
    conflict: str = ""
    payoff: str = ""
    hook: str = ""
    raw: str = ""

    @property
    def is_valid(self) -> bool:
        return bool(self.goal or self.conflict or self.hook)

    @property
    def brief(self) -> str:
        return (f"【本章目标】{self.goal}\n"
                f"【核心冲突】{self.conflict}\n"
                f"【爽点/情绪点】{self.payoff}\n"
                f"【结尾钩子】{self.hook}")

    @classmethod
    def load(cls, plan_path: Path) -> "ChapterPlan":
        text = read_text(plan_path)
        m = re.search(r"ch(\d+)_plan", plan_path.name)
        no = int(m.group(1)) if m else 0
        return cls(
            chapter_no=no,
            chapter_id=f"ch{no:03d}",
            goal=_extract_block(text, "本章目标"),
            conflict=_extract_block(text, "核心冲突"),
            payoff=_extract_block(text, "爽点"),
            hook=_extract_block(text, "结尾钩子"),
            raw=text,
        )


def _extract_block(text: str, keyword: str) -> str:
    """按标题块提取细纲内容。支持 # 标题、**加粗**、- 列表项等常见格式：
    - ## 本章目标 / 本章目标：xxx / **本章目标**：xxx / - **本章目标**：xxx（同行）
    - ## 本章目标 独占一行，内容在下一行
    """
    head = r"^[\s>#*\-]*[（(]?"
    for pattern in (
        head + keyword + r"[)）]?[^\n:：]{0,12}?[ \t]*[:：][ \t]*(.+)$",          # 同行（带冒号）
        head + keyword + r"[)）]?[^\n:：]{0,12}?[ \t]*[:：]?[ \t]*$\n\s*(.+)$",    # 独占行 → 下一行
    ):
        m = re.search(pattern, text, flags=re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""


@dataclass
class ReviewReport:
    """审稿结果。"""

    REVIEW_PASS = "通过"
    REVIEW_REWRITE = "重写"
    REVIEW_MANUAL = "人工"

    verdict: str = REVIEW_REWRITE  # 通过 / 重写 / 人工
    problems: str = ""
    report: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == REVIEW_PASS

    @property
    def needs_manual(self) -> bool:
        return self.verdict == REVIEW_MANUAL

    @classmethod
    def parse(cls, raw: str) -> "ReviewReport":
        """从审稿模型输出中解析判定。判定行格式：【判定】通过/重写/人工。
        重写/人工时，提取判定行之后的内容作为问题清单。"""
        m = re.search(r"【判定】\s*(通过|重写|人工)", raw)
        verdict = m.group(1) if m else REVIEW_REWRITE
        problems = ""
        if verdict in (REVIEW_REWRITE, REVIEW_MANUAL):
            rest = raw[m.end():] if m else raw
            problems = rest.strip()[:500]
        return cls(verdict=verdict, problems=problems, report=raw.strip())


@dataclass
class ChapterState:
    """单章生产状态，用于看板/断点。"""

    chapter_id: str
    status: str = "待生成"  # 待生成 / 已生成 / 审稿中 / 需人工复审 / 完成
    words: int = 0
    retries: int = 0
    note: str = ""


def list_chapter_ids(workspace: Path, volume: str = "volume1") -> List[str]:
    """扫描细纲目录，返回已规划章节 id 列表。"""
    plans_dir = workspace / "plot" / "chapter_plans"
    if not plans_dir.exists():
        return []
    ids = []
    for p in sorted(plans_dir.glob("ch*_plan.md")):
        m = re.search(r"ch(\d+)_plan", p.name)
        if m:
            ids.append(f"ch{int(m.group(1)):03d}")
    return ids
