"""Music generation engine factory.

Routes generation requests to the appropriate engine based on model name.
Supports ACE-Step 1.5 and YuE.
"""

import logging

from lofty.config import settings
from lofty.worker.engines.base import MusicEngine

logger = logging.getLogger(__name__)

# Engine cache keyed by engine type
_engines: dict[str, MusicEngine] = {}


def detect_engine_type(model_name: str | None = None) -> str:
    """Detect engine type from model name."""
    if model_name and model_name.startswith("yue"):
        return "yue"
    return "ace-step"


def get_engine(model_name: str | None = None) -> MusicEngine:
    """Get or create an engine for the given model name."""
    global _engines

    engine_type = detect_engine_type(model_name)

    if engine_type not in _engines:
        from lofty.worker.engines import get_engine_class

        if engine_type == "yue":
            engine_cls = get_engine_class("yue")
            engine = engine_cls(
                device=settings.model_device,
                cache_dir=settings.yue_cache_dir,
                use_4bit=settings.yue_use_4bit,
            )
        else:
            engine_cls = get_engine_class("ace-step")
            engine = engine_cls(
                model_path=settings.ace_step_model_path,
                device=settings.model_device,
                cache_dir=settings.ace_step_cache_dir,
            )

        engine.load()
        _engines[engine_type] = engine
        logger.info("%s engine loaded", engine_type)

    return _engines[engine_type]


# Backward-compatible alias
def get_generator() -> MusicEngine:
    return get_engine()


def preload_engines() -> None:
    """Pre-load the default engine on worker startup."""
    get_engine()
