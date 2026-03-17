"""Audio format conversion utilities using ffmpeg."""

import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def wav_to_mp3(wav_bytes: bytes, bitrate: str = "320k") -> bytes | None:
    """Convert WAV audio bytes to MP3 using ffmpeg.

    Returns MP3 bytes on success, None if ffmpeg is not available.
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as wav_file:
            wav_file.write(wav_bytes)
            wav_path = Path(wav_file.name)

        mp3_path = wav_path.with_suffix(".mp3")

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                bitrate,
                "-q:a",
                "2",
                str(mp3_path),
            ],
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            logger.warning("ffmpeg conversion failed: %s", result.stderr.decode()[:500])
            return None

        mp3_bytes = mp3_path.read_bytes()

        # Cleanup temp files
        wav_path.unlink(missing_ok=True)
        mp3_path.unlink(missing_ok=True)

        logger.info(
            "Converted WAV to MP3: %d KB -> %d KB (%.0f%% reduction)",
            len(wav_bytes) // 1024,
            len(mp3_bytes) // 1024,
            (1 - len(mp3_bytes) / len(wav_bytes)) * 100,
        )
        return mp3_bytes

    except FileNotFoundError:
        logger.warning("ffmpeg not found — skipping MP3 conversion")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("ffmpeg conversion timed out")
        return None
    except Exception:
        logger.exception("Unexpected error during MP3 conversion")
        return None
