from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

@dataclass(frozen=True)
class MemoryItem:
    key: str
    value: str
    ts: float

class MemoryStore:
    """Simple SQLite key/value store with timestamps."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _init(self) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """CREATE TABLE IF NOT EXISTS memory (
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    ts REAL NOT NULL
                )"""
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_memory_key_ts ON memory(key, ts)")
            con.commit()

    def put(self, key: str, value: str, ts: float) -> None:
        with sqlite3.connect(self.db_path) as con:
            con.execute("INSERT INTO memory(key, value, ts) VALUES (?, ?, ?)", (key, value, ts))
            con.commit()

    def get_latest(self, key: str) -> Optional[MemoryItem]:
        with sqlite3.connect(self.db_path) as con:
            row = con.execute(
                "SELECT key, value, ts FROM memory WHERE key=? ORDER BY ts DESC LIMIT 1", (key,)
            ).fetchone()
        if not row:
            return None
        return MemoryItem(*row)

    def search_prefix(self, prefix: str, limit: int = 50) -> Iterable[MemoryItem]:
        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT key, value, ts FROM memory WHERE key LIKE ? ORDER BY ts DESC LIMIT ?",
                (f"{prefix}%", limit),
            ).fetchall()
        return [MemoryItem(*r) for r in rows]
