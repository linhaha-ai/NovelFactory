# -*- coding: utf-8 -*-
"""Agent 提示词加载器：统一从 resources/prompts 读取 5 个角色的系统提示词。"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "resources" / "prompts"


def load_prompt(name: str) -> str:
    p = PROMPTS_DIR / name
    if not p.exists():
        raise FileNotFoundError(f"缺少提示词文件: {p}")
    return p.read_text(encoding="utf-8").strip()


def system_orchestrator() -> str:
    return load_prompt("system_orchestrator.md")


def agent_outline() -> str:
    return load_prompt("agent_outline.md")


def agent_writer() -> str:
    return load_prompt("agent_writer.md")


def agent_reviewer() -> str:
    return load_prompt("agent_reviewer.md")


def agent_memory() -> str:
    return load_prompt("agent_memory.md")
