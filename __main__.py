from __future__ import annotations

from pathlib import Path

from gss_ai.core.runtime import Runtime
from gss_ai.plugins.tiny_recursive_model import TinyRecursiveModel
from gss_ai.plugins.neural_symbolic_ai import NeuralSymbolicAI
from gss_ai.plugins.agentic_systems import AgenticSystems
from gss_ai.plugins.algorithmic_reasoners import AlgorithmicReasoners
from gss_ai.plugins.advanced_hybrid_ai import AdvancedHybridAI
from gss_ai.information_core.ingest import ingest_path

def main() -> int:
    rt = Runtime.build()

    # Register plugins from your spec
    rt.registry.register(TinyRecursiveModel())
    rt.registry.register(NeuralSymbolicAI())
    rt.registry.register(AgenticSystems())
    rt.registry.register(AlgorithmicReasoners())
    rt.registry.register(AdvancedHybridAI())

    for p in rt.registry.all():
        p.plugin.start(rt)

    rt.log.info("Registered plugins: %s", [p.name for p in rt.registry.all()])

    # Demo: ingest a path if provided
    import sys
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        art = ingest_path(path)
        rt.log.info("Ingested: %s | mime=%s | sha256=%s", art.path, art.mime, art.sha256)
        if art.text:
            rt.log.info("Text preview (first 500 chars): %r", art.text[:500])

    rt.log.info("Done. (This scaffold is intentionally safe-by-default.)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
