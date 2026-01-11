"""
Checkpoint/rollback for self-modifying code.

Implementation: zip snapshot of the project tree (excluding checkpoint dir itself).
Rollback extracts snapshot over working tree.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
import zipfile
import time
import os


class CheckpointManager:
    def __init__(self, project_root: Path, checkpoint_dir: Path):
        self.project_root = project_root.resolve()
        self.checkpoint_dir = (self.project_root / checkpoint_dir).resolve()
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def create_checkpoint(self, label: str = "") -> str:
        ts = time.strftime("%Y%m%d-%H%M%S")
        safe_label = "".join(c for c in label if c.isalnum() or c in ("-", "_"))[:32]
        cp_id = f"{ts}-{safe_label}" if safe_label else ts
        out = self.checkpoint_dir / f"{cp_id}.zip"

        exclude_prefix = str(self.checkpoint_dir)

        with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for p in self.project_root.rglob("*"):
                if not p.is_file():
                    continue
                ps = str(p.resolve())
                if ps.startswith(exclude_prefix):
                    continue
                # skip venvs / caches
                if any(part in {".venv", "venv", "__pycache__", ".git"} for part in p.parts):
                    continue
                rel = p.relative_to(self.project_root)
                z.write(p, arcname=str(rel))
        return cp_id

    def rollback(self, checkpoint_id: str) -> None:
        cp = self.checkpoint_dir / f"{checkpoint_id}.zip"
        if not cp.exists():
            return
        with zipfile.ZipFile(cp, "r") as z:
            z.extractall(self.project_root)
