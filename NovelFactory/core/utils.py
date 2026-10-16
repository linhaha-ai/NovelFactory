# -*- coding: utf-8 -*-
"""通用工具：文件读写、字数统计、轻量 TOML 解析、断点记录。零第三方依赖。"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def save_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def append_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(content)


def word_count(text: str) -> int:
    """中文字符数 + 英文单词数，作为章节字数口径。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z]+", text))
    return cjk + en


def parse_toml_simple(text: str) -> Dict[str, Any]:
    """解析本项目 config.toml 用到的 TOML 子集：section、key=value、字符串/数字/布尔。"""
    cfg: Dict[str, Any] = {}
    section: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            section = m.group(1).strip()
            cfg.setdefault(section, {})
            continue
        m = re.match(r'^([\w.-]+)\s*=\s*(.+)$', line)
        if m and section is not None:
            key, val = m.group(1).strip(), m.group(2).strip()
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                cfg[section][key] = val[1:-1]
            elif val.lower() == "true":
                cfg[section][key] = True
            elif val.lower() == "false":
                cfg[section][key] = False
            else:
                try:
                    cfg[section][key] = int(val)
                except ValueError:
                    try:
                        cfg[section][key] = float(val)
                    except ValueError:
                        cfg[section][key] = val
    return cfg


def load_config(workspace: Path) -> Dict[str, Any]:
    """读取写作工作区 config.toml，缺省值兜底。"""
    defaults: Dict[str, Any] = {
        "novel": {"title": "未命名", "genre": "待定", "chapter_word_count": 2000,
                  "word_tolerance": 0.1, "tone": "网文通俗叙事，少AI腔"},
        "llm": {"provider": "ollama", "base_url": "http://localhost:11434",
                "model": "qwen3.5:9b", "temperature_write": 0.7,
                "temperature_review": 0.2, "timeout": 300},
        "pipeline": {"start": 1, "end": 5, "max_retry": 1},
    }
    cfg_path = workspace / "config.toml"
    if cfg_path.exists():
        parsed = parse_toml_simple(cfg_path.read_text(encoding="utf-8"))
        for sec, kv in parsed.items():
            defaults.setdefault(sec, {})
            for k, v in kv.items():
                defaults[sec][k] = v
    return defaults


def tail(text: str, n: int = 500) -> str:
    """取文本末尾 n 字符，用于给主笔提供上一章结尾。"""
    return text[-n:] if len(text) > n else text


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", name).strip()
