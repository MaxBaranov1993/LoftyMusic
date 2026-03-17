"""Music generation engines package."""

from lofty.worker.engines.base import MusicEngine

__all__ = ["MusicEngine"]

# Lazy imports to avoid pulling in heavy dependencies at import time.
# Use get_engine_class("yue") or get_engine_class("ace-step") instead.


def get_engine_class(engine_type: str) -> type[MusicEngine]:
    """Return the engine class for the given type (lazy import)."""
    if engine_type == "yue":
        from lofty.worker.engines.yue_engine import YuEEngine

        return YuEEngine
    else:
        from lofty.worker.engines.ace_step_engine import AceStepEngine

        return AceStepEngine
