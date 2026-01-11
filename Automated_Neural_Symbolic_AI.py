"""
Automated_Neural_Symbolic_AI
Compatibility layer providing a minimal neural-symbolic reasoning interface.

Public API expected
- get_neural_symbolic_manager()
- process_logical_query(text) -> dict
- get_stats() -> dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List
import re
import time

_RULE_RE = re.compile(r"^\s*if\s+(?P<a>.+?)\s+then\s+(?P<b>.+?)\s*$", re.IGNORECASE)

@dataclass
class NeuralSymbolicManager:
    rules: List[Dict[str, str]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

    def add_rule(self, rule_text: str) -> Dict[str, Any]:
        m = _RULE_RE.match(rule_text)
        if not m:
            return {"status": "error", "message": "Rule format must be: IF <A> THEN <B>"}
        rule = {"if": m.group("a").strip(), "then": m.group("b").strip()}
        self.rules.append(rule)
        return {"status": "success", "rule": rule, "rule_count": len(self.rules)}

    def process_logical_query(self, text: str) -> Dict[str, Any]:
        # Very small symbolic engine: match rules whose antecedent appears in text.
        fired = []
        lower = text.lower()
        for r in self.rules:
            if r["if"].lower() in lower:
                fired.append(r)

        conclusion = [r["then"] for r in fired]
        out = {
            "status": "success",
            "type": "neural_symbolic_stub",
            "rules_total": len(self.rules),
            "rules_fired": len(fired),
            "conclusions": conclusion,
            "confidence": 0.68 if conclusion else 0.45,
        }
        self.history.append({"t": time.time(), "q": text, "out": out})
        self.history = self.history[-200:]
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {"status": "active", "rule_count": len(self.rules), "history_size": len(self.history)}

    def tick(self, ctx: Dict[str, Any]) -> None:
        """Autonomous micro-step (safe). Updates a heartbeat counter."""
        now = float(ctx.get("t", time.time()))
        if not self.history or (now - float(self.history[-1].get("t", now))) > 45.0:
            self.history.append({"t": now, "type": "heartbeat", "note": "neural_symbolic_ok"})
            self.history = self.history[-200:]


_neural_symbolic_manager: NeuralSymbolicManager | None = None

def get_neural_symbolic_manager() -> NeuralSymbolicManager:
    global _neural_symbolic_manager
    if _neural_symbolic_manager is None:
        _neural_symbolic_manager = NeuralSymbolicManager()
    return _neural_symbolic_manager
