"""Music generation engine wrapping MusicGen model.

Supports two modes:
- GPU mode: loads facebook/musicgen-stereo-medium (or other variants) via transformers
- Mock mode: generates procedural music for CPU-only development/testing
"""

import io
import logging
import time
import wave
from typing import Callable

import numpy as np

from lofty.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt enrichment — MusicGen responds much better to detailed prompts
# ---------------------------------------------------------------------------

_GENRE_ENRICHMENTS = {
    "pop": "catchy pop song, polished production, clear vocals melody, bright mixing, radio-ready",
    "rock": "energetic rock track, electric guitars, driving drums, powerful bass line, stadium sound",
    "jazz": "smooth jazz piece, warm saxophone, piano chords, walking bass, brushed drums, intimate club atmosphere",
    "blues": "soulful blues track, expressive electric guitar, Hammond organ, steady groove, warm analog tone",
    "electronic": "electronic dance music, synthesizers, deep bass, crisp hi-hats, build-ups and drops, club-ready production",
    "edm": "high-energy EDM, massive synth leads, punchy kick drums, sidechain compression, festival anthem",
    "techno": "driving techno, hypnotic bassline, industrial textures, modular synth, dark warehouse atmosphere",
    "classical": "orchestral classical piece, strings ensemble, dynamic crescendos, concert hall reverb, expressive performance",
    "ambient": "atmospheric ambient soundscape, evolving pads, gentle textures, spacious reverb, meditative mood",
    "hip-hop": "hip-hop beat, boom bap drums, deep 808 bass, vinyl crackle, sampled chords, head-nodding groove",
    "lofi": "lo-fi hip-hop, dusty vinyl samples, mellow piano, tape saturation, relaxing chill beats",
    "metal": "heavy metal, distorted guitars, double bass drums, aggressive riffs, powerful and intense",
    "funk": "funky groove, slap bass, wah-wah guitar, tight drums, horn section, danceable rhythm",
    "r&b": "smooth R&B, silky vocals melody, lush pads, 808 bass, modern production, emotional",
    "country": "country music, acoustic guitar, steel guitar, fiddle, warm vocals melody, Nashville sound",
    "reggae": "reggae rhythm, offbeat guitar skank, deep bass, one-drop drums, warm tropical feel",
    "latin": "latin music, congas and timbales, brass section, piano montuno, energetic dancing rhythm",
    "cinematic": "cinematic orchestral score, epic brass, sweeping strings, timpani, dramatic and emotional, film soundtrack quality",
}

_MOOD_KEYWORDS = {
    "happy": "uplifting, bright, major key, feel-good energy",
    "sad": "melancholic, emotional, minor key, heartfelt",
    "energetic": "high energy, driving tempo, powerful, dynamic",
    "calm": "peaceful, gentle, soothing, relaxed tempo",
    "dark": "dark atmosphere, ominous, deep tones, tension",
    "upbeat": "upbeat tempo, cheerful, bouncy rhythm, positive vibes",
    "aggressive": "intense, powerful, heavy, hard-hitting",
    "dreamy": "ethereal, floating, reverb-soaked, atmospheric, soft",
    "epic": "grand, cinematic, building intensity, powerful climax",
    "romantic": "warm, intimate, gentle, tender melody, emotional depth",
}


def _enrich_prompt(prompt: str) -> str:
    """Enrich a user prompt with production details for better MusicGen output.

    MusicGen produces significantly better results with detailed descriptions
    including instruments, production style, tempo, and mood descriptors.
    """
    lower = prompt.lower()
    additions = []

    # Add genre-specific enrichment
    for genre, enrichment in _GENRE_ENRICHMENTS.items():
        if genre in lower:
            additions.append(enrichment)
            break

    # Add mood enrichment
    for mood, enrichment in _MOOD_KEYWORDS.items():
        if mood in lower:
            additions.append(enrichment)
            break

    # Always append quality descriptors
    quality = "high quality, professional studio recording, well-mixed and mastered"
    additions.append(quality)

    if additions:
        enriched = f"{prompt}, {', '.join(additions)}"
    else:
        enriched = f"{prompt}, {quality}"

    # MusicGen tokenizer has a limit; keep prompt reasonable
    if len(enriched) > 500:
        enriched = enriched[:500]

    return enriched


class MusicGenerator:
    """Singleton-per-worker that holds the loaded model in GPU memory."""

    def __init__(
        self,
        model_name: str = settings.model_name,
        device: str = settings.model_device,
        cache_dir: str = settings.model_cache_dir,
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.cache_dir = cache_dir
        self.processor = None
        self.model = None
        self._loaded = False
        self._is_stereo = "stereo" in model_name

    def load(self) -> None:
        """Load model and processor. Falls back to mock mode if torch unavailable."""
        if self._loaded:
            return

        try:
            import torch
            from transformers import AutoProcessor, MusicgenForConditionalGeneration

            logger.info(f"Loading model {self.model_name} on {self.device}...")

            self.processor = AutoProcessor.from_pretrained(
                self.model_name, cache_dir=self.cache_dir
            )
            use_cuda = self.device == "cuda" and torch.cuda.is_available()
            if use_cuda:
                self.model = MusicgenForConditionalGeneration.from_pretrained(
                    self.model_name, cache_dir=self.cache_dir,
                    torch_dtype=torch.float16,
                ).to(self.device)
                logger.info(
                    f"Model loaded on CUDA (float16). "
                    f"VRAM: {torch.cuda.memory_allocated() / 1024**2:.0f}MB"
                )
            else:
                self.model = MusicgenForConditionalGeneration.from_pretrained(
                    self.model_name, cache_dir=self.cache_dir,
                )
                self.device = "cpu"
                logger.info("Model loaded on CPU (generation will be slow, ~20x real-time)")

            # Detect stereo from model config
            audio_channels = getattr(self.model.config.audio_encoder, "num_channels", 1)
            self._is_stereo = audio_channels > 1 or "stereo" in self.model_name

            self._loaded = True
            logger.info(
                f"MusicGenerator ready in REAL mode on {self.device} "
                f"({'stereo' if self._is_stereo else 'mono'})"
            )

        except ImportError as e:
            logger.warning(
                f"Cannot load ML model: missing package ({e}). "
                "Install with: pip install -e \".[worker]\""
            )
            self._loaded = True
            logger.warning("MusicGenerator running in MOCK mode — audio will be procedural tones, not AI-generated")

        except OSError as e:
            logger.warning(
                f"Cannot load ML model: OS error ({e}). "
                "Check model_cache_dir and network access for downloading model weights."
            )
            self._loaded = True
            logger.warning("MusicGenerator running in MOCK mode — audio will be procedural tones, not AI-generated")

    def generate(
        self,
        prompt: str,
        duration_seconds: float = 10.0,
        temperature: float = 0.8,
        top_k: int = 250,
        top_p: float = 0.95,
        guidance_scale: float = 4.0,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[bytes, int, float]:
        """Generate audio from a text prompt.

        Args:
            on_progress: Optional callback called with progress percentage (0-100).

        Returns:
            tuple of (wav_bytes, sample_rate, actual_duration_seconds)
        """
        if self.model is not None and self.processor is not None:
            return self._generate_real(
                prompt, duration_seconds, temperature, top_k, top_p,
                guidance_scale, on_progress,
            )
        return self._generate_mock(prompt, duration_seconds, on_progress)

    def _generate_real(
        self,
        prompt: str,
        duration_seconds: float,
        temperature: float,
        top_k: int,
        top_p: float,
        guidance_scale: float,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[bytes, int, float]:
        """Generate audio using the actual MusicGen model."""
        import torch
        from transformers import LogitsProcessor, LogitsProcessorList

        if self.device == "cpu":
            est = duration_seconds * 20
            logger.info(f"Generating {duration_seconds}s audio on CPU — estimated ~{est:.0f}s wall time")

        # Enrich the user prompt for better quality
        enriched_prompt = _enrich_prompt(prompt)
        logger.info(f"Enriched prompt: '{enriched_prompt[:120]}...'")

        inputs = self.processor(
            text=[enriched_prompt], padding=True, return_tensors="pt"
        ).to(self.device)

        # MusicGen generates ~50 tokens per second of audio at 32kHz
        max_new_tokens = int(duration_seconds * 50)

        # Track progress via a custom logits processor that counts generated tokens
        class ProgressTracker(LogitsProcessor):
            def __init__(self, total_tokens: int, callback: Callable[[int], None] | None):
                self.total_tokens = total_tokens
                self.callback = callback
                self.step = 0

            def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor) -> torch.FloatTensor:
                self.step += 1
                if self.callback and self.total_tokens > 0:
                    pct = min(95, int(self.step / self.total_tokens * 95))
                    self.callback(pct)
                return scores

        logits_processor = LogitsProcessorList()
        if on_progress:
            logits_processor.append(ProgressTracker(max_new_tokens, on_progress))

        with torch.no_grad():
            audio_values = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                guidance_scale=guidance_scale,
                do_sample=True,
                logits_processor=logits_processor,
            )

        # Extract audio: shape is (batch, channels, samples)
        # Stereo models output 2 channels, mono outputs 1
        audio_tensor = audio_values[0].cpu().numpy()  # (channels, samples)
        sample_rate = self.model.config.audio_encoder.sampling_rate

        # Clear GPU cache
        if self.device == "cuda":
            torch.cuda.empty_cache()

        # Post-processing per channel
        if audio_tensor.ndim == 1:
            audio_tensor = audio_tensor[np.newaxis, :]  # (1, samples)

        processed_channels = []
        for ch in range(audio_tensor.shape[0]):
            processed_channels.append(self._post_process(audio_tensor[ch], sample_rate))
        audio_tensor = np.stack(processed_channels, axis=0)

        n_channels = audio_tensor.shape[0]
        wav_bytes = self._numpy_to_wav(audio_tensor, sample_rate, n_channels)
        actual_duration = audio_tensor.shape[1] / sample_rate

        if on_progress:
            on_progress(100)

        logger.info(f"Generated {actual_duration:.1f}s {'stereo' if n_channels == 2 else 'mono'} audio at {sample_rate}Hz")

        return wav_bytes, sample_rate, actual_duration

    def _generate_mock(
        self, prompt: str, duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[bytes, int, float]:
        """Generate procedural music for testing without GPU.

        Uses multi-layered synthesis with melody, chords, and bass
        instead of a simple sine tone.
        """
        from lofty.worker.mock_generator import generate_procedural_music

        sample_rate = 32000

        # Simulate generation time (~1s per 5s of audio) with progress updates
        total_steps = 20
        step_delay = max(0.05, duration_seconds / 50)
        for step in range(total_steps):
            time.sleep(step_delay)
            if on_progress:
                pct = min(95, int((step + 1) / total_steps * 95))
                on_progress(pct)

        logger.info(f"Mock mode: generating procedural music for prompt: '{prompt[:80]}'")
        audio = generate_procedural_music(prompt, duration_seconds, sample_rate)

        # Mock outputs mono: shape (samples,) -> (1, samples)
        audio_2d = audio[np.newaxis, :]
        wav_bytes = self._numpy_to_wav(audio_2d, sample_rate, n_channels=1)

        if on_progress:
            on_progress(100)

        return wav_bytes, sample_rate, duration_seconds

    @staticmethod
    def _post_process(audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Apply fade, compression, soft clipping, and normalization."""
        audio = audio.astype(np.float64)

        # Fade in/out (50ms) to avoid clicks
        fade_samples = int(sample_rate * 0.05)
        if len(audio) > 2 * fade_samples:
            audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
            audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

        # Light dynamic compression — reduces dynamic range for more "polished" sound
        # RMS-based gain with attack/release
        block_size = int(sample_rate * 0.05)  # 50ms blocks
        threshold_rms = 0.15
        ratio = 3.0  # 3:1 compression above threshold
        for i in range(0, len(audio) - block_size, block_size):
            block = audio[i:i + block_size]
            rms = np.sqrt(np.mean(block ** 2))
            if rms > threshold_rms:
                gain_reduction = threshold_rms + (rms - threshold_rms) / ratio
                gain = gain_reduction / rms
                # Smooth gain application
                audio[i:i + block_size] *= gain

        # Soft clipping via tanh to tame harsh peaks
        threshold = 0.85
        mask = np.abs(audio) > threshold
        if np.any(mask):
            audio[mask] = threshold * np.tanh(audio[mask] / threshold)

        # Normalize to -0.5 dBFS (0.94 peak) for loudness
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.94

        return audio

    @staticmethod
    def _numpy_to_wav(audio: np.ndarray, sample_rate: int, n_channels: int = 1) -> bytes:
        """Convert numpy array to WAV bytes.

        Args:
            audio: Shape (channels, samples) or (samples,) for mono.
            sample_rate: Audio sample rate.
            n_channels: Number of output channels.
        """
        if audio.ndim == 1:
            audio = audio[np.newaxis, :]

        # Normalize to [-1, 1] range
        peak = max(abs(audio.max()), abs(audio.min()))
        if peak > 0:
            audio = audio / peak

        # Convert to 16-bit PCM
        audio_int16 = (audio * 32767).astype(np.int16)

        # Interleave channels for WAV format: [L0, R0, L1, R1, ...]
        if n_channels == 2 and audio_int16.shape[0] == 2:
            interleaved = np.empty(audio_int16.shape[1] * 2, dtype=np.int16)
            interleaved[0::2] = audio_int16[0]
            interleaved[1::2] = audio_int16[1]
        else:
            interleaved = audio_int16[0]

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(n_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(interleaved.tobytes())

        return buffer.getvalue()


# Module-level singleton
_generator: MusicGenerator | None = None


def get_generator() -> MusicGenerator:
    """Get or create the generator singleton."""
    global _generator
    if _generator is None:
        _generator = MusicGenerator()
    return _generator
