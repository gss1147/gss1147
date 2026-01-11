from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Protocol, Any

class Plugin(Protocol):
    name: str
    def start(self, runtime: "Runtime") -> None: ...
    def stop(self) -> None: ...

@dataclass
class PluginInfo:
    name: str
    plugin: Plugin

class Registry:
    def __init__(self) -> None:
        self._plugins: Dict[str, PluginInfo] = {}

    def register(self, plugin: Plugin) -> None:
        if plugin.name in self._plugins:
            raise ValueError(f"Plugin already registered: {plugin.name}")
        self._plugins[plugin.name] = PluginInfo(name=plugin.name, plugin=plugin)

    def get(self, name: str) -> Plugin:
        return self._plugins[name].plugin

    def all(self) -> Iterable[PluginInfo]:
        return list(self._plugins.values())
