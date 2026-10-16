# -*- coding: utf-8 -*-
"""监控看板：章节字数与状态统计、记忆库统计。"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..core.database import NovelDB
from ..core.models import list_chapter_ids
from ..core.utils import read_text, word_count

DEFAULT_WS = Path(__file__).resolve().parent.parent.parent / "novel_factory"


def monitor(workspace: Path) -> None:
    ws = Path(workspace)
    db = NovelDB(ws)
    try:
        planned = list_chapter_ids(ws)
        print(f"已规划细纲章节数：{len(planned)}")
        print(f"{'章节':<10}{'状态':<10}{'字数':>6}  备注")
        for ch in db.all_chapters():
            print(f"{ch['chapter_id']:<10}{ch['status']:<10}{ch['words']:>6}  {ch['note'][:30]}")
        ms = ws / "manuscript"
        if ms.exists():
            files = sorted(ms.glob("ch*.md"))
            total = sum(word_count(read_text(p)) for p in files)
            print(f"\n已产出手稿：{len(files)} 章，累计 {total} 字")
        mem = ws / "memory"
        tl = read_text(mem / "timeline.md")
        fs = read_text(mem / "foreshadow.md")
        print(f"记忆库：timeline {len(tl.splitlines())} 行，foreshadow {len(fs.splitlines())} 行")
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="小说工厂进度看板")
    ap.add_argument("--workspace", default=str(DEFAULT_WS))
    args = ap.parse_args()
    monitor(Path(args.workspace))


if __name__ == "__main__":
    main()
