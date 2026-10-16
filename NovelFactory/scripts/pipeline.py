# -*- coding: utf-8 -*-
"""章节生产流水线入口：写作→审稿→重写→记忆→落盘，支持断点续跑。

用法（在 ai-book 根目录）：
    python -m NovelFactory.scripts.pipeline --start 1 --end 5
    python -m NovelFactory.scripts.pipeline --dry-run      # 不调用模型，演示链路
"""
from __future__ import annotations

import argparse
from pathlib import Path

from ..core.engine import NovelFactoryEngine

DEFAULT_WS = Path(__file__).resolve().parent.parent.parent / "novel_factory"


def main() -> None:
    ap = argparse.ArgumentParser(description="NovelFactory 章节生产流水线")
    ap.add_argument("--workspace", default=str(DEFAULT_WS), help="写作工作区目录")
    ap.add_argument("--start", type=int, default=None)
    ap.add_argument("--end", type=int, default=None)
    ap.add_argument("--max-retry", type=int, default=None, help="审稿未通过最大重写次数")
    ap.add_argument("--dry-run", action="store_true", help="不调用真实模型，演示流程")
    args = ap.parse_args()

    engine = NovelFactoryEngine(args.workspace, dry_run=args.dry_run)
    try:
        engine.run_pipeline(start=args.start, end=args.end, max_retry=args.max_retry)
    finally:
        engine.close()


if __name__ == "__main__":
    main()
