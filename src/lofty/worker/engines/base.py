"""Abstract base class for music generation engines."""

import io
import wave
from abc import ABC, abstractmethod
from typing import Callable

import numpy as np


class MusicEngine(ABC):
    """Base interface for any music generation engine.

    All engines must implement load(), generate(), and unload().
    The generate() method returns (wav_bytes, sample_rate, actual_duration).
    """

    @abstractmethod
    def load(self) -> None:
        """Load model weights into memory (GPU or CPU)."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        duration_seconds: float = 10.0,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        """Generate audio from a text prompt.

        Returns:
            tuple of (wav_bytes, sample_rate, actual_duration_seconds)
        """

    def unload(self) -> None:
        """Release model from memory. Override if cleanup is needed."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Short identifier for this engine, e.g. 'musicgen' or 'ace-step'."""

    @property
    def is_loaded(self) -> bool:
        """Whether the model is ready for inference."""
        return False

    @staticmethod
    def numpy_to_wav(audio: np.ndarray, sample_rate: int, n_channels: int = 1) -> bytes:
        """Convert numpy array (channels, samples) to WAV bytes."""
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]

        peak = max(abs(audio.max()), abs(audio.min()))
        if peak > 0:
            audio = audio / peak

        audio_int16 = (audio * 32767).astype(np.int16)

        if n_channels == 2 and audio_int16.shape[0] == 2:
            interleaved = np.empty(audio_int16.shape[1] * 2, dtype=np.int16)
            interleaved[0::2] = audio_int16[0]
            interleaved[1::2] = audio_int16[1]
        else:
            interleaved = audio_int16[0]

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(interleaved.tobytes())

        return buffer.getvalue()
