"""Audio analyzer: auto-annotate uploaded tracks using ACE-Step understand_music."""

import io
import logging

from lofty.config import settings

logger = logging.getLogger(__name__)


def analyze_audio(audio_bytes: bytes, audio_format: str = "wav") -> dict:
    """Analyze audio and extract metadata (caption, lyrics, BPM, key, etc.).

    Uses ACE-Step's understand_music() if the LLM handler is available,
    otherwise falls back to basic analysis with soundfile.

    Returns dict with keys: caption, lyrics, bpm, key_scale, duration_seconds, language.
    """
    result = {
        "caption": "",
        "lyrics": "",
        "bpm": None,
        "key_scale": None,
        "duration_seconds": 0.0,
        "language": "en",
    }

    # Always get basic duration first
    try:
        basic = _analyze_basic(audio_bytes)
        result.update(basic)
    except Exception:
        pass

    # Try ACE-Step understand_music for full annotation
    if settings.ace_step_enabled:
        try:
            ace_result = _analyze_with_ace_step(audio_bytes, audio_format)
            if ace_result:
                result.update(ace_result)
        except Exception:
            logger.warning("ACE-Step analysis failed, using basic analysis only")

    return result


def _analyze_with_ace_step(audio_bytes: bytes, audio_format: str) -> dict | None:
    """Use ACE-Step's understand_music() for comprehensive analysis.

    Note: understand_music() requires the LLM handler and audio_codes (encoded audio).
    This is a heavyweight operation that needs the ACE-Step engine loaded.
    """
    try:
        from acestep.handler import AceStepHandler
        from acestep.inference import understand_music
        from acestep.llm_inference import LLMHandler
    except ImportError:
        logger.debug("ACE-Step not installed, skipping ACE analysis")
        return None

    # Get the handlers from the loaded engine (avoid loading a second copy)
    from lofty.worker.generator import get_engine, detect_engine_type

    try:
        engine = get_engine("ace-step-1.5")
    except Exception:
        return None

    if engine._mock_mode or engine._llm_handler is None or engine._dit_handler is None:
        return None

    # ACE-Step understand_music needs audio_codes — we need to encode the audio first
    # Write to temp file, encode, then analyze
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=f".{audio_format}", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Encode audio to codes using the DiT handler
        if hasattr(engine._dit_handler, "encode_audio"):
            audio_codes = engine._dit_handler.encode_audio(tmp_path)
        else:
            logger.debug("DiT handler has no encode_audio method")
            return None

        analysis = understand_music(
            llm_handler=engine._llm_handler,
            audio_codes=audio_codes,
        )

        if not analysis.success:
            logger.warning("understand_music failed: %s", analysis.error)
            return None

        result = {}
        if analysis.caption:
            result["caption"] = analysis.caption
        if analysis.lyrics:
            result["lyrics"] = analysis.lyrics
        if analysis.language:
            result["language"] = analysis.language
        if analysis.bpm is not None:
            result["bpm"] = analysis.bpm
        if analysis.keyscale:
            result["key_scale"] = analysis.keyscale
        if analysis.duration is not None:
            result["duration_seconds"] = analysis.duration

        return result

    except Exception:
        logger.exception("ACE-Step understand_music failed")
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _analyze_basic(audio_bytes: bytes) -> dict:
    """Basic audio analysis using soundfile for duration."""
    result = {}

    try:
        import soundfile as sf
        info = sf.info(io.BytesIO(audio_bytes))
        result["duration_seconds"] = info.duration
    except Exception:
        pass

    return result
