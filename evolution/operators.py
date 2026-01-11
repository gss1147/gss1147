"""
Mutation operators for the evolution engine.

Operators are conservative and mechanical:
- Fix missing imports for common symbols (random/np/pd/torch/defaultdict).
- Append missing optional dependencies to requirements-optional.txt.

You can add more operators over time (API adapters, refactors, tuning, etc.).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Optional
import re


class MutationOperator:
    name: str = "base"

    def __init__(self, project_root: Path, writable_roots: Optional[List[Path]] = None):
        self.project_root = project_root.resolve()
        self.writable_roots = [p.resolve() for p in (writable_roots or [self.project_root])]

    def can_handle(self, report: Any) -> bool:
        raise NotImplementedError

    def apply(self, report: Any) -> Dict[str, Any]:
        raise NotImplementedError

    def _is_writable(self, path: Path) -> bool:
        rp = path.resolve()
        return any(str(rp).startswith(str(root)) for root in self.writable_roots)


class MissingImportFixer(MutationOperator):
    name = "missing_import_fixer"

    _SYMBOL_TO_IMPORT = {
        "random": "import random",
        "np": "import numpy as np",
        "pd": "import pandas as pd",
        "torch": "import torch",
        "defaultdict": "from collections import defaultdict",
        "Path": "from pathlib import Path",
    }

    def can_handle(self, report: Any) -> bool:
        for iss in getattr(report, "issues", []):
            tb = iss.get("traceback", "") or ""
            err = iss.get("error", "") or ""
            if "NameError" in err and "is not defined" in err:
                return True
            if "NameError" in tb and "is not defined" in tb:
                return True
        return False

    def apply(self, report: Any) -> Dict[str, Any]:
        changed: List[str] = []
        notes: List[str] = []

        for iss in getattr(report, "issues", []):
            tb = iss.get("traceback", "") or ""
            # NameError: name 'X' is not defined
            m = re.search(r"NameError:\s+name\s+'([^']+)'\s+is\s+not\s+defined", tb)
            if not m:
                m = re.search(r"NameError\(\"name\s+'([^']+)'\s+is\s+not\s+defined\"\)", iss.get("error", "") or "")
            if not m:
                continue

            symbol = m.group(1)
            import_stmt = self._SYMBOL_TO_IMPORT.get(symbol)
            if not import_stmt:
                notes.append(f"Unmapped missing symbol: {symbol}")
                continue

            src_file = self._extract_project_file(tb)
            if not src_file:
                notes.append(f"Could not locate source file for missing symbol: {symbol}")
                continue

            if not self._is_writable(src_file):
                notes.append(f"Not writable: {src_file}")
                continue

            try:
                if self._ensure_import(src_file, import_stmt):
                    changed.append(str(src_file.relative_to(self.project_root)))
                    notes.append(f"Inserted `{import_stmt}` into {src_file.name}")
            except Exception as e:
                notes.append(f"Failed to patch {src_file}: {e}")

        return {"operator": self.name, "changed_files": changed, "notes": notes}

    def _extract_project_file(self, traceback_str: str) -> Optional[Path]:
        # Choose the last file path in the traceback that lives under project_root
        candidates = []
        for m in re.finditer(r'File "([^"]+)"', traceback_str):
            p = Path(m.group(1))
            try:
                rp = p.resolve()
            except Exception:
                rp = p
            if str(rp).startswith(str(self.project_root)):
                candidates.append(rp)
        if not candidates:
            return None
        return candidates[-1]

    def _ensure_import(self, file_path: Path, import_stmt: str) -> bool:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^\s*" + re.escape(import_stmt) + r"\s*$", content, flags=re.M):
            return False

        lines = content.splitlines(True)
        i = 0

        # Shebang / coding
        if i < len(lines) and lines[i].startswith("#!"):
            i += 1
        if i < len(lines) and "coding" in lines[i]:
            i += 1

        # Module docstring
        if i < len(lines) and (lines[i].lstrip().startswith('"""') or lines[i].lstrip().startswith("'''")):
            quote = '"""' if '"""' in lines[i] else "'''"
            i += 1
            while i < len(lines) and quote not in lines[i]:
                i += 1
            if i < len(lines):
                i += 1  # include closing line

        # __future__ imports
        while i < len(lines) and lines[i].startswith("from __future__"):
            i += 1

        # Insert a blank line if needed
        insert = import_stmt + "\n"
        if i < len(lines) and lines[i].strip() != "":
            insert = insert + "\n"

        lines.insert(i, insert)
        file_path.write_text("".join(lines), encoding="utf-8")
        return True


class RequirementsAppender(MutationOperator):
    name = "requirements_appender"

    _MODULE_TO_PIP = {
        "cv2": "opencv-python",
        "yaml": "PyYAML",
        "PyPDF2": "PyPDF2",
        "toml": "toml",
        "bs4": "beautifulsoup4",
        "docx": "python-docx",
        "soundfile": "soundfile",
        "librosa": "librosa",
        "feedparser": "feedparser",
        "xmltodict": "xmltodict",
        "onnx": "onnx",
        "pyreadstat": "pyreadstat",
        "geopandas": "geopandas",
        "py7zr": "py7zr",
        "rarfile": "rarfile",
        "h5py": "h5py",
        "pyarrow": "pyarrow",
    }

    def can_handle(self, report: Any) -> bool:
        for iss in getattr(report, "issues", []):
            err = (iss.get("error", "") or "") + "\n" + (iss.get("traceback", "") or "")
            if "ModuleNotFoundError" in err and "No module named" in err:
                return True
        return False

    def apply(self, report: Any) -> Dict[str, Any]:
        req_file = self.project_root / "requirements-optional.txt"
        if not req_file.exists():
            req_file = self.project_root / "requirements.txt"

        if not self._is_writable(req_file):
            return {"operator": self.name, "changed_files": [], "notes": ["requirements file not writable"]}

        existing = set()
        try:
            existing = {line.strip() for line in req_file.read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.strip().startswith("#")}
        except Exception:
            existing = set()

        to_add = []
        notes = []
        for iss in getattr(report, "issues", []):
            err = (iss.get("error", "") or "") + "\n" + (iss.get("traceback", "") or "")
            m = re.search(r"No module named '([^']+)'", err)
            if not m:
                continue
            mod = m.group(1)
            pkg = self._MODULE_TO_PIP.get(mod, mod)
            if pkg not in existing and pkg not in to_add:
                to_add.append(pkg)
                notes.append(f"Added optional dependency: {pkg} (from missing module {mod})")

        if not to_add:
            return {"operator": self.name, "changed_files": [], "notes": ["no dependencies to add"]}

        blob = req_file.read_text(encoding="utf-8") if req_file.exists() else ""
        if blob and not blob.endswith("\n"):
            blob += "\n"
        blob += "\n# Added by evolution engine\n" + "\n".join(to_add) + "\n"
        req_file.write_text(blob, encoding="utf-8")
        return {"operator": self.name, "changed_files": [str(req_file.relative_to(self.project_root))], "notes": notes}
