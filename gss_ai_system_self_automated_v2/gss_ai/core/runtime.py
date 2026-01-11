from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
import time

from .config import Settings
from .events import EventBus, Event
from .logging import setup_logging
from .registry import Registry
from .memory import MemoryStore

@dataclass
class Runtime:
    settings: Settings
    registry: Registry
    bus: EventBus
    memory: MemoryStore
    log: Any

    @classmethod
    def build(cls, settings: Optional[Settings] = None) -> "Runtime":
        settings = settings or Settings()
        settings.state_dir.mkdir(parents=True, exist_ok=True)
        log = setup_logging(settings.state_dir)
        registry = Registry()
        bus = EventBus()
        memory = MemoryStore(settings.memory_db)
        rt = cls(settings=settings, registry=registry, bus=bus, memory=memory, log=log)
        rt.log.info("Runtime initialized | project_root=%s | state_dir=%s", settings.project_root, settings.state_dir)
        return rt

    def emit(self, type: str, **payload: Any) -> None:
        self.bus.publish(Event(type=type, payload=payload))

    def now(self) -> float:
        return time.time()
