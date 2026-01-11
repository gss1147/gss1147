from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from gss_ai.core.runtime import Runtime

@dataclass
class TinyRecursiveModel:
    """Tiny, efficient, recursive intelligence (reflection loop / self-critique scaffolding).

    This is a safe stub: it can observe events, ingest data, and *propose* changes,
    but it does not auto-apply patches or execute generated code.
    """
    name: str = "Automated_Tiny_Recursive_Model"
    _rt: Optional[Runtime] = None

    def start(self, runtime: Runtime) -> None:
        self._rt = runtime
        runtime.log.info("Plugin started: %s", self.name)

    def stop(self) -> None:
        if self._rt:
            self._rt.log.info("Plugin stopped: %s", self.name)
        self._rt = None
