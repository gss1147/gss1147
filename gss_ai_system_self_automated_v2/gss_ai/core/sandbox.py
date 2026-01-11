from __future__ import annotations

from pathlib import Path

class SandboxViolation(RuntimeError):
    pass

def within_root(root: Path, path: Path) -> bool:
    try:
        root = root.resolve()
        path = path.resolve()
        return root == path or root in path.parents
    except Exception:
        return False

def require_within(root: Path, path: Path) -> Path:
    if not within_root(root, path):
        raise SandboxViolation(f"Path is outside sandbox root: {path}")
    return path.resolve()
