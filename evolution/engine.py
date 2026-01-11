"""
Autonomous evolution engine.

This module implements a closed-loop "observe → evaluate → mutate → validate → keep/rollback"
workflow. It is designed to be:
- Fully automated (no human gate required)
- Deterministic in scope (only edits within the project directory)
- Self-stabilizing (checkpoint + rollback on failed validation)

Note: This is engineering guardrail logic (integrity/rollback), not content filtering.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import os
import sys
import json
import time
import threading
import subprocess

from .evaluator import Evaluator, HealthReport
from .operators import MutationOperator, MissingImportFixer, RequirementsAppender
from .checkpoints import CheckpointManager


@dataclass
class EvolutionConfig:
    enabled: bool = True
    interval_seconds: int = 30
    max_mutations_per_cycle: int = 3
    run_pytest: bool = False
    run_compileall: bool = True
    run_import_smoke: bool = True
    autopatch: bool = True
    writable_roots: Optional[List[str]] = None  # defaults to [project_root]
    checkpoint_dir: str = ".evolution/checkpoints"
    logs_dir: str = ".evolution/logs"

    @staticmethod
    def load(project_root: Path) -> "EvolutionConfig":
        cfg = EvolutionConfig()

        # env overrides
        if os.getenv("GSS_EVOLVE", "").strip() in {"0", "false", "False", "no"}:
            cfg.enabled = False
        if os.getenv("GSS_EVOLVE_INTERVAL"):
            try:
                cfg.interval_seconds = max(3, int(os.getenv("GSS_EVOLVE_INTERVAL", "30")))
            except Exception:
                pass
        if os.getenv("GSS_EVOLVE_RUN_PYTEST", "").strip() in {"1", "true", "True", "yes"}:
            cfg.run_pytest = True
        if os.getenv("GSS_EVOLVE_AUTOPATCH", "").strip() in {"0", "false", "False", "no"}:
            cfg.autopatch = False

        # file override
        cfg_path = project_root / "evolution_config.json"
        if cfg_path.exists():
            try:
                loaded = json.loads(cfg_path.read_text(encoding="utf-8"))
                for k, v in loaded.items():
                    if hasattr(cfg, k):
                        setattr(cfg, k, v)
            except Exception:
                # best-effort; keep defaults
                pass

        if not cfg.writable_roots:
            cfg.writable_roots = [str(project_root)]

        return cfg

    def save(self, project_root: Path) -> None:
        (project_root / "evolution_config.json").write_text(
            json.dumps(asdict(self), indent=2), encoding="utf-8"
        )


class EvolutionEngine:
    """
    Autonomous self-improvement loop.

    You can start it in background via:
        engine.start(modules=modules)
    """
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.cfg = EvolutionConfig.load(self.project_root)

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._evaluator = Evaluator(self.project_root, self.cfg)
        self._checkpoints = CheckpointManager(self.project_root, Path(self.cfg.checkpoint_dir))

        self._operators: List[MutationOperator] = [
            MissingImportFixer(self.project_root, writable_roots=[Path(p) for p in self.cfg.writable_roots or []]),
            RequirementsAppender(self.project_root, writable_roots=[Path(p) for p in self.cfg.writable_roots or []]),
        ]

        self.last_report: Optional[HealthReport] = None
        self.last_action: Dict[str, Any] = {}

        # ensure dirs
        (self.project_root / self.cfg.logs_dir).mkdir(parents=True, exist_ok=True)

    def start(self, modules: Optional[Dict[str, Any]] = None, background: bool = True) -> None:
        if not self.cfg.enabled:
            return

        if background:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self.run_forever, args=(modules,), daemon=True)
            self._thread.start()
        else:
            self.run_forever(modules)

    def stop(self) -> None:
        self._stop.set()

    def trigger_once(self, modules: Optional[Dict[str, Any]] = None, reason: str = "manual") -> HealthReport:
        report = self._evaluator.evaluate(modules=modules)
        self.last_report = report

        if not self.cfg.autopatch:
            self.last_action = {"reason": reason, "autopatch": False, "mutations_applied": 0}
            return report

        if report.ok:
            # Nothing to fix; optional future: exploration/tuning.
            self.last_action = {"reason": reason, "mutations_applied": 0, "note": "healthy"}
            return report

        mutations_applied = 0
        applied_ops: List[Dict[str, Any]] = []

        # checkpoint before mutating
        cp_id = self._checkpoints.create_checkpoint(label=f"{reason}")
        for op in self._operators:
            if mutations_applied >= self.cfg.max_mutations_per_cycle:
                break
            if not op.can_handle(report):
                continue

            result = op.apply(report)
            if result.get("changed_files"):
                mutations_applied += 1
            applied_ops.append(result)

            # validate after each operator; rollback on failure
            validate = self._evaluator.evaluate(modules=modules)
            if not validate.ok:
                self._checkpoints.rollback(cp_id)
                self.last_action = {
                    "reason": reason,
                    "mutations_applied": mutations_applied,
                    "rollback": True,
                    "checkpoint": cp_id,
                    "operators": applied_ops,
                    "post_validate": validate.to_dict(),
                }
                return validate

        # final validate
        final_report = self._evaluator.evaluate(modules=modules)
        if not final_report.ok:
            self._checkpoints.rollback(cp_id)
            self.last_action = {
                "reason": reason,
                "mutations_applied": mutations_applied,
                "rollback": True,
                "checkpoint": cp_id,
                "operators": applied_ops,
                "post_validate": final_report.to_dict(),
            }
            return final_report

        self.last_action = {
            "reason": reason,
            "mutations_applied": mutations_applied,
            "rollback": False,
            "checkpoint": cp_id,
            "operators": applied_ops,
            "post_validate": final_report.to_dict(),
        }
        return final_report

    def run_forever(self, modules: Optional[Dict[str, Any]] = None) -> None:
        while not self._stop.is_set():
            try:
                self.trigger_once(modules=modules, reason="cycle")
            except Exception:
                # keep engine alive no matter what
                pass
            self._stop.wait(self.cfg.interval_seconds)

    def status(self) -> Dict[str, Any]:
        return {
            "enabled": self.cfg.enabled,
            "interval_seconds": self.cfg.interval_seconds,
            "autopatch": self.cfg.autopatch,
            "last_report": None if not self.last_report else self.last_report.to_dict(),
            "last_action": self.last_action,
        }
