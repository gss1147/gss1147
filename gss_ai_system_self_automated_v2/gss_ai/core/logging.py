from __future__ import annotations
import logging
from pathlib import Path

def setup_logging(state_dir: Path, level: int = logging.INFO) -> logging.Logger:
    state_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("gss_ai")
    logger.setLevel(level)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = logging.FileHandler(state_dir / "gss_ai.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    logger.propagate = False
    return logger
