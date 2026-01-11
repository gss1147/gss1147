from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import mimetypes
import hashlib

@dataclass(frozen=True)
class IngestedArtifact:
    path: Path
    sha256: str
    mime: str
    text: Optional[str]
    meta: Dict[str, Any]

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def ingest_path(path: Path, *, max_text_bytes: int = 2_000_000) -> IngestedArtifact:
    """Best-effort ingestion.

    - Always returns file hash + mime.
    - Extracts text for plain-text-like files.
    - For PDFs/images/audio/video/etc. you can add optional extractors later.
    """
    path = path.expanduser().resolve()
    mime, _ = mimetypes.guess_type(str(path))
    mime = mime or "application/octet-stream"

    sha = _sha256(path)

    text: Optional[str] = None
    meta: Dict[str, Any] = {"size_bytes": path.stat().st_size}

    # lightweight: try decoding small text files
    if mime.startswith("text/") or path.suffix.lower() in {".md", ".markdown", ".txt", ".log", ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".tsv"}:
        if path.stat().st_size <= max_text_bytes:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                text = path.read_text(errors="replace")

    return IngestedArtifact(path=path, sha256=sha, mime=mime, text=text, meta=meta)
