"""Automated_Memory_Core

A lightweight, offline, self-contained memory subsystem.

Design goals
- Works on Windows with no extra dependencies (sqlite3 only).
- Provides short-term memory (STM) and long-term memory (LTM).
- Safe-by-default: no code execution, no external calls.

Public API expected by orchestrator/GUI
- get_memory_manager(work_dir: str|None=None) -> MemoryManager
- add_stm(text, meta=None) -> dict
- add_ltm(text, meta=None) -> dict
- consolidate(limit=50) -> dict
- query_stm(limit=20) -> dict
- query_ltm(limit=20) -> dict
- clear(stm=True, ltm=False) -> dict
- get_stats() -> dict
"""

from __future__ import annotations

import os
import json
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


@dataclass
class MemoryManager:
    work_dir: str
    db_path: str

    def __post_init__(self) -> None:
        _ensure_dir(os.path.dirname(self.db_path))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    text TEXT NOT NULL,
                    meta_json TEXT
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ltm (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    text TEXT NOT NULL,
                    meta_json TEXT
                );
                """
            )

    def _insert(self, table: str, text: str, meta: Optional[Dict[str, Any]]) -> int:
        payload = json.dumps(meta or {}, ensure_ascii=False)
        ts = time.time()
        with self._connect() as conn:
            cur = conn.execute(f"INSERT INTO {table} (ts, text, meta_json) VALUES (?, ?, ?)", (ts, text, payload))
            return int(cur.lastrowid)

    def add_stm(self, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rid = self._insert("stm", text, meta)
        return {"status": "success", "type": "stm_add", "id": rid}

    def add_ltm(self, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rid = self._insert("ltm", text, meta)
        return {"status": "success", "type": "ltm_add", "id": rid}

    def query_stm(self, limit: int = 20) -> Dict[str, Any]:
        limit = int(max(1, min(200, limit)))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, text, meta_json FROM stm ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"status": "success", "type": "stm", "items": [self._row_to_item(r) for r in rows]}

    def query_ltm(self, limit: int = 20) -> Dict[str, Any]:
        limit = int(max(1, min(200, limit)))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, text, meta_json FROM ltm ORDER BY ts DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"status": "success", "type": "ltm", "items": [self._row_to_item(r) for r in rows]}

    def consolidate(self, limit: int = 50) -> Dict[str, Any]:
        """Promote the oldest STM entries into LTM (bounded)."""
        limit = int(max(1, min(500, limit)))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, ts, text, meta_json FROM stm ORDER BY ts ASC LIMIT ?",
                (limit,),
            ).fetchall()
            if not rows:
                return {"status": "success", "type": "consolidate", "moved": 0}

            for _id, ts, text, meta_json in rows:
                conn.execute("INSERT INTO ltm (ts, text, meta_json) VALUES (?, ?, ?)", (ts, text, meta_json))
                conn.execute("DELETE FROM stm WHERE id=?", (_id,))
        return {"status": "success", "type": "consolidate", "moved": len(rows)}

    def clear(self, stm: bool = True, ltm: bool = False) -> Dict[str, Any]:
        with self._connect() as conn:
            if stm:
                conn.execute("DELETE FROM stm")
            if ltm:
                conn.execute("DELETE FROM ltm")
        return {"status": "success", "type": "clear", "stm": stm, "ltm": ltm}

    def get_stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            stm_count = int(conn.execute("SELECT COUNT(*) FROM stm").fetchone()[0])
            ltm_count = int(conn.execute("SELECT COUNT(*) FROM ltm").fetchone()[0])
        return {
            "status": "active",
            "db_path": self.db_path,
            "stm_count": stm_count,
            "ltm_count": ltm_count,
            "updated_at": datetime.now().isoformat(),
        }

    def tick(self, ctx: Dict[str, Any]) -> None:
        """Autonomous micro-step: periodically consolidate."""
        now = float(ctx.get("t", time.time()))
        # consolidate every ~120 seconds (safe, bounded)
        if int(now) % 120 == 0:
            try:
                self.consolidate(limit=10)
            except Exception:
                pass

    @staticmethod
    def _row_to_item(row: Any) -> Dict[str, Any]:
        _id, ts, text, meta_json = row
        try:
            meta = json.loads(meta_json) if meta_json else {}
        except Exception:
            meta = {}
        return {"id": int(_id), "ts": float(ts), "text": str(text), "meta": meta}


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(work_dir: str | None = None) -> MemoryManager:
    global _memory_manager
    root = work_dir or os.environ.get("GSS1147_ROOT", "X:/gss1147")
    db_path = os.path.join(root, "state", "memory.sqlite3")
    if _memory_manager is None:
        _memory_manager = MemoryManager(work_dir=root, db_path=db_path)
    return _memory_manager
