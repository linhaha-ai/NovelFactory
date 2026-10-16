# -*- coding: utf-8 -*-
"""NovelFactory 一键入口。

用法（在 ai-book 根目录执行）：
    python -m NovelFactory.scripts.run init          # 初始化写作工作区（幂等）
    python -m NovelFactory.scripts.run outline "主角林辰，都市修仙，随身灵泉，爽文快节奏" 1 5
    python -m NovelFactory.scripts.run write --start 1 --end 5
    python -m NovelFactory.scripts.run write --dry-run
    python -m NovelFactory.scripts.run monitor
    python -m NovelFactory.scripts.run export
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.engine import NovelFactoryEngine
from . import export as export_mod
from . import init_project, monitor as monitor_mod, outline as outline_mod

DEFAULT_WS = Path(__file__).resolve().parent.parent.parent / "novel_factory"


def main() -> None:
    ap = argparse.ArgumentParser(description="NovelFactory 小说工厂")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="初始化写作工作区")
    p_init.add_argument("--workspace", default=str(DEFAULT_WS))

    p_outline = sub.add_parser("outline", help="生成大纲（总纲→卷纲→细纲）")
    p_outline.add_argument("--workspace", default=str(DEFAULT_WS))
    p_outline.add_argument("premise", help="作者补充设定，如：主角林辰，都市修仙，金手指随身灵泉")
    p_outline.add_argument("--start", type=int, default=1)
    p_outline.add_argument("--end", type=int, default=5)
    p_outline.add_argument("--volume", type=int, default=1)

    p_write = sub.add_parser("write", help="启动章节生产流水线")
    p_write.add_argument("--workspace", default=str(DEFAULT_WS))
    p_write.add_argument("--start", type=int, default=None)
    p_write.add_argument("--end", type=int, default=None)
    p_write.add_argument("--max-retry", type=int, default=None)
    p_write.add_argument("--dry-run", action="store_true")

    p_monitor = sub.add_parser("monitor", help="进度看板")
    p_monitor.add_argument("--workspace", default=str(DEFAULT_WS))

    p_export = sub.add_parser("export", help="导出合集")
    p_export.add_argument("--workspace", default=str(DEFAULT_WS))
    p_export.add_argument("--formats", default="txt,html")

    args = ap.parse_args()
    ws = Path(getattr(args, "workspace", DEFAULT_WS))

    if args.cmd == "init":
        init_project.init_workspace(ws)
        print(f"✅ 写作工作区就绪：{ws}")
    elif args.cmd == "outline":
        engine = NovelFactoryEngine(ws)
        try:
            outline_mod.outline_all(engine, args.premise, args.start, args.end, args.volume)
        finally:
            engine.close()
    elif args.cmd == "write":
        engine = NovelFactoryEngine(ws, dry_run=args.dry_run)
        try:
            engine.run_pipeline(start=args.start, end=args.end, max_retry=args.max_retry)
        finally:
            engine.close()
    elif args.cmd == "monitor":
        monitor_mod.monitor(ws)
    elif args.cmd == "export":
        export_mod.export_all(ws, getattr(args, "formats", "txt,html"))
    else:
        ap.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
