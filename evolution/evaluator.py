"""
Health evaluator for the evolution engine.

Evaluation steps are best-effort and dependency-aware:
- import smoke test of core modules (subprocess)
- compileall (subprocess)
- optional pytest (subprocess)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, List
import sys
import os
import subprocess
import json
import time
import re


@dataclass
class HealthReport:
    ok: bool
    checks: Dict[str, Any]
    issues: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": self.ok, "checks": self.checks, "issues": self.issues}


class Evaluator:
    def __init__(self, project_root: Path, cfg: Any):
        self.project_root = project_root
        self.cfg = cfg

    def evaluate(self, modules: Optional[Dict[str, Any]] = None) -> HealthReport:
        checks: Dict[str, Any] = {}
        issues: List[Dict[str, Any]] = []

        if getattr(self.cfg, "run_import_smoke", True):
            ok, detail = self._import_smoke()
            checks["import_smoke"] = detail
            if not ok:
                issues.extend(detail.get("issues", []))

        if getattr(self.cfg, "run_compileall", True):
            ok, detail = self._compileall()
            checks["compileall"] = detail
            if not ok:
                issues.extend(detail.get("issues", []))

        if getattr(self.cfg, "run_pytest", False):
            ok, detail = self._pytest()
            checks["pytest"] = detail
            if not ok:
                issues.extend(detail.get("issues", []))

        ok = len(issues) == 0
        return HealthReport(ok=ok, checks=checks, issues=issues)

    def _import_smoke(self):
        """
        Import the core entry modules and call their factory functions.
        Run in subprocess so a crash doesn't take down the orchestrator.
        """
        script = r"""
import json, sys, traceback
issues=[]
def _try(label, code):
    try:
        exec(code, globals(), globals())
    except Exception as e:
        issues.append({"type":"import_smoke", "label":label, "error":repr(e), "traceback":traceback.format_exc()})

# import modules
_try("Automated_Tiny_Recursive_Model", "import Automated_Tiny_Recursive_Model as m; m.get_model_manager().get_stats()")
_try("Automated_Neural_Symbolic_AI", "import Automated_Neural_Symbolic_AI as m; m.get_neural_symbolic_manager().get_stats()")
_try("Automated_Agentic_Systems", "import Automated_Agentic_Systems as m; m.get_orchestrator().get_stats()")
_try("Automated_Algorithmic_Reasoners", "import Automated_Algorithmic_Reasoners as m; m.get_reasoners_manager().get_stats()")
_try("Automated_Advanced_Hybird_AI", "import Automated_Advanced_Hybird_AI as m; m.get_hybrid_manager().get_stats()")
_try("Automated_Infomation_Core", "import Automated_Infomation_Core as m; m.get_info_core_manager().get_stats()")

print(json.dumps({"issues":issues}))
sys.exit(0 if not issues else 2)
"""
        p = subprocess.run(
            [sys.executable, "-c", script],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        detail = {"returncode": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-8000:], "issues": []}
        parsed = None
        try:
            parsed = json.loads(p.stdout.strip().splitlines()[-1])
        except Exception:
            parsed = None

        if parsed and isinstance(parsed.get("issues"), list):
            detail["issues"] = parsed["issues"]
            ok = len(detail["issues"]) == 0
        else:
            ok = p.returncode == 0
            if not ok:
                detail["issues"].append({"type":"import_smoke", "error":"unparseable_smoke_output", "stderr":detail["stderr"]})

        return ok, detail

    def _compileall(self):
        p = subprocess.run(
            [sys.executable, "-m", "compileall", "-q", "."],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        ok = p.returncode == 0
        detail = {"returncode": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-8000:], "issues": []}
        if not ok:
            detail["issues"].append({"type": "compileall", "stderr": detail["stderr"]})
        return ok, detail

    def _pytest(self):
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        ok = p.returncode == 0
        detail = {"returncode": p.returncode, "stdout": p.stdout[-8000:], "stderr": p.stderr[-8000:], "issues": []}
        if not ok:
            detail["issues"].append({"type": "pytest", "stderr": detail["stderr"], "stdout": detail["stdout"]})
        return ok, detail
