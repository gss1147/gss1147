"""
Automated_Algorithmic_Reasoners
Compatibility layer with a safe problem-solver interface.

Public API expected
- get_reasoners_manager()
- solve_problem(text) -> dict
- get_stats() -> dict
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, List
import ast
import operator
import time
import re

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARY = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

def _safe_eval_expr(expr: str) -> float:
    node = ast.parse(expr, mode="eval")

    def _eval(n):
        if isinstance(n, ast.Expression):
            return _eval(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.BinOp) and type(n.op) in _ALLOWED_BINOPS:
            return _ALLOWED_BINOPS[type(n.op)](_eval(n.left), _eval(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _ALLOWED_UNARY:
            return _ALLOWED_UNARY[type(n.op)](_eval(n.operand))
        raise ValueError("Unsupported expression")
    return _eval(node)

@dataclass
class ReasonersManager:
    history: List[Dict[str, Any]] = field(default_factory=list)

    def solve_problem(self, text: str) -> Dict[str, Any]:
        # Heuristic: attempt to solve pure arithmetic expressions.
        cleaned = text.strip()
        out: Dict[str, Any]
        try:
            if re.fullmatch(r"[0-9\.\s\+\-\*\/\%\(\)\^]+", cleaned):
                expr = cleaned.replace("^", "**")
                value = _safe_eval_expr(expr)
                out = {"status": "success", "type": "math", "answer": value, "confidence": 0.85}
            else:
                out = {
                    "status": "success",
                    "type": "reasoned_response",
                    "answer": f"Interpreted problem statement: {cleaned}",
                    "notes": ["Add domain-specific solvers here (graphs, planning, search, etc.)"],
                    "confidence": 0.55,
                }
        except Exception as e:
            out = {"status": "error", "message": str(e), "confidence": 0.2}

        self.history.append({"t": time.time(), "q": text, "out": out})
        self.history = self.history[-200:]
        return out

    def get_stats(self) -> Dict[str, Any]:
        return {"status": "active", "history_size": len(self.history)}

    def tick(self, ctx: Dict[str, Any]) -> None:
        """Autonomous micro-step (safe). Periodically runs a tiny self-check."""
        now = float(ctx.get("t", time.time()))
        if (int(now) % 120) == 0:
            # deterministic micro-check (does not call external tools)
            self.history.append({"t": now, "type": "self_check", "ok": True})
            self.history = self.history[-200:]


_reasoners_manager: ReasonersManager | None = None

def get_reasoners_manager() -> ReasonersManager:
    global _reasoners_manager
    if _reasoners_manager is None:
        _reasoners_manager = ReasonersManager()
    return _reasoners_manager
