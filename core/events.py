from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import uuid

@dataclass
class Event:
    type: str
    payload: Dict[str, Any]
    ts: float = time.time()
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = uuid.uuid4().hex

class EventBus:
    """Minimal pub/sub bus (in-process)."""
    def __init__(self) -> None:
        self._subs: Dict[str, list] = {}

    def subscribe(self, event_type: str, fn) -> None:
        self._subs.setdefault(event_type, []).append(fn)

    def publish(self, event: Event) -> None:
        for fn in self._subs.get(event.type, []):
            fn(event)
