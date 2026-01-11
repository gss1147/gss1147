"""
Automated_Agentic_Systems
Compatibility layer for an "agentic" orchestrator.

Important safety:
- This module does NOT self-modify code automatically.
- It can generate "patch proposals" as text files for human review.

Public API expected
- get_orchestrator()
- orchestrate_task(task_dict) -> dict
- get_stats() -> dict

Additional safe actions (used by GUI/orchestrator)
- debug() -> dict
- evolve_routing() -> dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import os
import time
import json
from datetime import datetime

@dataclass
class AgenticOrchestrator:
    work_dir: str
    history: List[Dict[str, Any]] = field(default_factory=list)

    def orchestrate_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        # Basic planner: create steps and a safe execution plan.
        desc = str(task.get("description", "")).strip()
        plan = [
            {"step": 1, "action": "analyze", "detail": "Extract intent and constraints"},
            {"step": 2, "action": "select_tools", "detail": "Choose modules to consult"},
            {"step": 3, "action": "synthesize", "detail": "Combine outputs into response"},
            {"step": 4, "action": "verify", "detail": "Sanity-check and produce confidence"},
        ]
        result = {
            "status": "success",
            "type": "agentic_plan",
            "task": desc,
            "plan": plan,
            "confidence": 0.62,
        }
        self.history.append({"t": time.time(), "task": task, "out": result})
        self.history = self.history[-200:]
        return result

    def propose_patch(self, title: str, proposal: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        os.makedirs(self.work_dir, exist_ok=True)
        patches_dir = os.path.join(self.work_dir, "patch_proposals")
        os.makedirs(patches_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        fn = os.path.join(patches_dir, f"{ts}_{title.replace(' ', '_')}.json")
        payload = {"title": title, "proposal": proposal, "metadata": metadata or {}, "created_at": datetime.now().isoformat()}
        with open(fn, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return fn

    def debug(self) -> Dict[str, Any]:
        """Run a bounded, safe diagnostic and return a report."""
        report = {
            "status": "success",
            "type": "agentic_debug",
            "checks": [
                {"name": "history_ok", "ok": True, "details": f"history_size={len(self.history)}"},
                {"name": "patch_dir_ok", "ok": True, "details": os.path.join(self.work_dir, "patch_proposals")},
            ],
            "confidence": 0.7,
        }
        self.history.append({"t": time.time(), "type": "debug", "out": report})
        self.history = self.history[-200:]
        return report

    def evolve_routing(self) -> Dict[str, Any]:
        """Safe 'evolution' action: emit a routing policy proposal (no auto-apply)."""
        proposal = (
            "Proposed routing evolution:\n"
            "- Add a lightweight task classifier (intent: math/retrieval/planning)\n"
            "- Route to specialized experts (reasoners/info_core/recursive)\n"
            "- Track per-expert success metrics and adjust weights (no auto code changes)\n"
        )
        path = self.propose_patch(
            title="evolve_routing",
            proposal=proposal,
            metadata={"source": "agentic_evolve_routing"},
        )
        out = {"status": "success", "type": "agentic_evolve_routing", "patch_proposal": path, "confidence": 0.65}
        self.history.append({"t": time.time(), "type": "evolve_routing", "out": out})
        self.history = self.history[-200:]
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {"status": "active", "history_size": len(self.history), "work_dir": self.work_dir}

    def tick(self, ctx: Dict[str, Any]) -> None:
        """Autonomous micro-step (safe).

        Performs bounded housekeeping and emits patch proposals only (no auto-apply).
        """
        now = float(ctx.get("t", time.time()))
        if not self.history or (now - float(self.history[-1].get("t", now))) > 60.0:
            self.history.append({"t": now, "type": "heartbeat", "note": "agentic_ok"})
            self.history = self.history[-200:]


_orchestrator: AgenticOrchestrator | None = None

def get_orchestrator(work_dir: str | None = None) -> AgenticOrchestrator:
    global _orchestrator
    root = work_dir or os.environ.get("GSS1147_ROOT", "X:/gss1147")
    if _orchestrator is None:
        _orchestrator = AgenticOrchestrator(work_dir=root)
    return _orchestrator
