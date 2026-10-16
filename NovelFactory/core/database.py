# -*- coding: utf-8 -*-
"""轻量 SQLite 记录层：章节状态与运行日志（记忆正文仍以 md 文件为主记忆）。"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class NovelDB:
    def __init__(self, workspace: Path):
        self.conn = sqlite3.connect(str(workspace / "memory" / "novel.db"))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS chapter_status(
                chapter_id TEXT PRIMARY KEY,
                status TEXT,
                words INTEGER DEFAULT 0,
                retries INTEGER DEFAULT 0,
                note TEXT,
                updated_at TEXT)"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS run_log(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT, chapter_id TEXT, action TEXT, detail TEXT)"""
        )
        self.conn.commit()

    def set_chapter(self, chapter_id: str, status: str, words: int = 0,
                    retries: int = 0, note: str = "") -> None:
        self.conn.execute(
            """INSERT INTO chapter_status(chapter_id, status, words, retries, note, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(chapter_id) DO UPDATE SET
                 status=excluded.status, words=excluded.words,
                 retries=excluded.retries, note=excluded.note,
                 updated_at=excluded.updated_at""",
            (chapter_id, status, words, retries, note,
             datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def get_chapter(self, chapter_id: str) -> Dict[str, Any] | None:
        cur = self.conn.execute(
            "SELECT chapter_id,status,words,retries,note,updated_at FROM chapter_status WHERE chapter_id=?",
            (chapter_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = ["chapter_id", "status", "words", "retries", "note", "updated_at"]
        return dict(zip(keys, row))

    def all_chapters(self) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT chapter_id,status,words,retries,note,updated_at FROM chapter_status ORDER BY chapter_id"
        )
        keys = ["chapter_id", "status", "words", "retries", "note", "updated_at"]
        return [dict(zip(keys, r)) for r in cur.fetchall()]

    def log(self, chapter_id: str, action: str, detail: str = "") -> None:
        self.conn.execute(
            "INSERT INTO run_log(ts, chapter_id, action, detail) VALUES(?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), chapter_id, action, detail[:500]),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
