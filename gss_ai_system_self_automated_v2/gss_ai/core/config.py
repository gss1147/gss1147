from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    """Central configuration (safe defaults for local/offline operation)."""

    # Project root (restricts file access)
    project_root: Path = field(default_factory=lambda: Path(os.environ.get("GSS_PROJECT_ROOT", Path.cwd())).resolve())

    # Where the system stores its local state (logs, sqlite, cache)
    state_dir: Path = field(default_factory=lambda: (Path(os.environ.get("GSS_STATE_DIR", Path.cwd() / ".gss_state")).resolve()))

    # Safety: never auto-execute newly written code
    allow_auto_execute: bool = False

    # Safety: restrict tools to this directory by default
    tools_root: Path = field(default_factory=lambda: Path(os.environ.get("GSS_TOOLS_ROOT", Path.cwd())).resolve())

    # Memory DB file
    memory_db: Path = field(default_factory=lambda: (Path(os.environ.get("GSS_MEMORY_DB", Path.cwd() / ".gss_state" / "memory.sqlite3")).resolve()))

    # Basic runtime knobs
    max_reflection_steps: int = int(os.environ.get("GSS_MAX_REFLECTION_STEPS", "3"))
    max_patch_bytes: int = int(os.environ.get("GSS_MAX_PATCH_BYTES", "200000"))
