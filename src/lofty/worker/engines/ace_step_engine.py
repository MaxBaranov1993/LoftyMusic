"""ACE-Step 1.5 music generation engine.

ACE-Step is a hybrid LM + DiT model that generates full songs with vocals,
lyrics, and instrument control. It requires < 4 GB VRAM for inference.

Real API uses two handlers:
  - AceStepHandler (DiT model for audio synthesis)
  - LLMHandler (Language model for planning/reasoning)

And free functions:
  - generate_music(dit_handler, llm_handler, params, config) → GenerationResult
"""

import logging
import os
import random
import tempfile
from typing import Callable

import numpy as np

from lofty.config import settings
from lofty.worker.engines.base import MusicEngine

logger = logging.getLogger(__name__)

# ACE-Step project root — needed for handler initialization
_ACE_STEP_PROJECT_ROOT = os.environ.get(
    "ACE_STEP_PROJECT_ROOT",
    os.path.join(settings.ace_step_cache_dir, "ACE-Step-1.5"),
)

# Max retries on NaN / generation failure
_MAX_NAN_RETRIES = 3


class AceStepEngine(MusicEngine):
    """ACE-Step 1.5 engine for full-song generation with vocals and lyrics."""

    def __init__(
        self,
        model_path: str = "",
        device: str = settings.model_device,
        cache_dir: str = "",
    ) -> None:
        self.model_path = model_path or settings.ace_step_model_path
        self.device = device
        self.cache_dir = cache_dir or settings.ace_step_cache_dir
        self._dit_handler = None
        self._llm_handler = None
        self._loaded = False
        self._mock_mode = False

    @property
    def engine_name(self) -> str:
        return "ace-step"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        if self._loaded:
            return

        # Respect explicit mock mode setting
        if settings.mock_gpu:
            logger.info("MOCK_GPU=true — ACE-Step running in mock mode")
            self._loaded = True
            self._mock_mode = True
            return

        try:
            from acestep.handler import AceStepHandler
            from acestep.llm_inference import LLMHandler

            logger.info("Loading ACE-Step 1.5 handlers on %s...", self.device)

            # Detect GPU capabilities for optimizations
            use_flash = False
            use_compile = False
            try:
                import torch
                if torch.cuda.is_available():
                    cap = torch.cuda.get_device_capability()
                    use_flash = cap[0] >= 7  # sm_75+ (T4, A100, etc.)
                    use_compile = hasattr(torch, "compile")
            except Exception:
                pass

            # Initialize DiT handler with optimizations
            self._dit_handler = AceStepHandler()
            self._dit_handler.initialize_service(
                project_root=_ACE_STEP_PROJECT_ROOT,
                config_path="acestep-v15-turbo",
                device=self.device,
                offload_to_cpu=settings.ace_step_cpu_offload,
                compile_model=use_compile,
                use_flash_attention=use_flash,
            )

            # Initialize LLM handler
            self._llm_handler = LLMHandler()
            self._llm_handler.initialize(
                checkpoint_dir=self.cache_dir,
                lm_model_path="acestep-5Hz-lm-1.7B",
                backend="vllm",
                device=self.device,
            )

            self._loaded = True
            self._mock_mode = False
            logger.info("AceStepEngine ready on %s", self.device)

        except ImportError as e:
            logger.warning(
                "Cannot load ACE-Step: %s. "
                "Install from: https://github.com/ace-step/ACE-Step-1.5 "
                "Running in MOCK mode.",
                e,
            )
            self._loaded = True
            self._mock_mode = True

        except Exception as e:
            logger.warning("Cannot load ACE-Step model: %s. Running in MOCK mode.", e)
            self._loaded = True
            self._mock_mode = True

    def unload(self) -> None:
        self._dit_handler = None
        self._llm_handler = None
        self._loaded = False
        self._mock_mode = False
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass

    def generate(
        self,
        prompt: str,
        duration_seconds: float = 10.0,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        """Generate music using ACE-Step 1.5.

        ACE-Step specific params (passed via **params):
            lyrics: str — song lyrics text
            bpm: int | None — beats per minute
            key: str | None — musical key (e.g. "C Major", "A Minor")
            time_signature: str — e.g. "4/4", "3/4"
            language: str — lyrics language code (en, zh, ja, ko, etc.)
            inference_steps: int — diffusion steps (default 8 for turbo)
            guidance_scale: float — prompt adherence (3.0-7.0)
            task_type: str — "text2music", "cover", "repaint", etc.
            seed: int — random seed (-1 for random)
            lora_adapter_path: str | None — path to LoRA adapter
        """
        if self._mock_mode or self._dit_handler is None:
            return self._generate_mock(prompt, duration_seconds, on_progress)

        # Load LoRA adapter if provided
        lora_path = params.pop("lora_adapter_path", None)
        if lora_path:
            self._load_lora(lora_path)

        return self._generate_with_retry(prompt, duration_seconds, on_progress, **params)

    def _generate_with_retry(
        self,
        prompt: str,
        duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        """Generate with NaN retry and instrumental fallback."""
        lyrics = params.get("lyrics", "")
        has_lyrics = bool(lyrics.strip())
        last_error = None

        for attempt in range(_MAX_NAN_RETRIES):
            try:
                return self._generate_real(
                    prompt, duration_seconds, on_progress, **params
                )
            except RuntimeError as e:
                error_str = str(e).lower()
                if "nan" not in error_str and "failed" not in error_str:
                    raise
                last_error = e
                new_seed = random.randint(0, 999999)
                logger.warning(
                    "Generation attempt %d failed: %s. Retrying with seed=%d",
                    attempt + 1, e, new_seed,
                )
                params["seed"] = new_seed

                # On second-to-last attempt, drop lyrics as fallback
                if attempt == _MAX_NAN_RETRIES - 2 and has_lyrics:
                    logger.warning("Dropping lyrics for instrumental fallback")
                    params["lyrics"] = ""

        raise RuntimeError(
            f"Generation failed after {_MAX_NAN_RETRIES} retries: {last_error}"
        )

    def _generate_real(
        self,
        prompt: str,
        duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        from acestep.inference import GenerationConfig, GenerationParams, generate_music

        lyrics = params.get("lyrics", "")
        bpm = params.get("bpm")
        key = params.get("key")  # frontend sends "C major" etc.
        time_signature = params.get("time_signature", "")
        language = params.get("language", "en")
        inference_steps = params.get("inference_steps", 8)
        guidance_scale = params.get("guidance_scale", 5.0)
        task_type = params.get("task_type", "text2music")
        seed = params.get("seed", -1)

        logger.info(
            "ACE-Step generating: task=%s, duration=%.1fs, steps=%d, guidance=%.1f",
            task_type, duration_seconds, inference_steps, guidance_scale,
        )

        if on_progress:
            on_progress(5)

        # Build GenerationParams dataclass with real ACE-Step field names
        gen_params = GenerationParams(
            task_type=task_type,
            caption=prompt,
            lyrics=lyrics,
            instrumental=(not lyrics),
            vocal_language=language if language else "unknown",
            bpm=bpm,
            keyscale=key or "",
            timesignature=time_signature or "",
            duration=duration_seconds,
            inference_steps=inference_steps,
            guidance_scale=guidance_scale,
            seed=seed if seed >= 0 else -1,
            thinking=settings.ace_step_thinking_enabled,
        )

        gen_config = GenerationConfig(
            batch_size=1,
            use_random_seed=(seed < 0),
            seeds=[seed] if seed >= 0 else None,
            audio_format="wav",
        )

        if on_progress:
            on_progress(10)

        # Create temp dir for output
        with tempfile.TemporaryDirectory(prefix="lofty_ace_") as save_dir:
            result = generate_music(
                dit_handler=self._dit_handler,
                llm_handler=self._llm_handler,
                params=gen_params,
                config=gen_config,
                save_dir=save_dir,
            )

            if on_progress:
                on_progress(85)

            if not result.success:
                raise RuntimeError(f"ACE-Step generation failed: {result.error}")

            if not result.audios:
                raise RuntimeError("ACE-Step returned no audio")

            # Extract audio from result
            audio_np, sample_rate = self._extract_audio(result)

        if on_progress:
            on_progress(90)

        # Normalize audio shape
        if audio_np.ndim == 1:
            audio_np = audio_np[np.newaxis, :]

        n_channels = audio_np.shape[0]
        wav_bytes = self.numpy_to_wav(audio_np, sample_rate, n_channels)
        actual_duration = audio_np.shape[1] / sample_rate
        output_sr = sample_rate

        if on_progress:
            on_progress(100)

        logger.info(
            "ACE-Step generated %.1fs %s audio at %dHz",
            actual_duration, "stereo" if n_channels == 2 else "mono", output_sr,
        )

        return wav_bytes, output_sr, actual_duration

    def _extract_audio(self, result) -> tuple[np.ndarray, int]:
        """Extract numpy audio array and sample rate from GenerationResult.

        ACE-Step GenerationResult.audios is a list of dicts:
        {
            "path": str,           # file path to saved audio
            "tensor": Tensor,      # [channels, samples]
            "sample_rate": int,    # default 48000
            "key": str,
            "params": dict,
        }
        """
        audio_item = result.audios[0]

        # Prefer tensor (avoids re-reading from disk)
        if "tensor" in audio_item and audio_item["tensor"] is not None:
            audio = audio_item["tensor"]
            if hasattr(audio, "cpu"):
                audio = audio.cpu()
            if hasattr(audio, "numpy"):
                audio = audio.numpy()
            sr = audio_item.get("sample_rate", 48000)
            return audio.squeeze(), sr

        # Fallback: read from file path
        if "path" in audio_item and audio_item["path"]:
            return self._load_audio_file(audio_item["path"])

        raise ValueError("ACE-Step audio item has neither tensor nor path")

    @staticmethod
    def _load_audio_file(path: str) -> tuple[np.ndarray, int]:
        """Load audio from a file path returned by ACE-Step."""
        try:
            import soundfile as sf
            audio, sr = sf.read(path)
            # soundfile returns (samples, channels) — transpose to (channels, samples)
            if audio.ndim == 2:
                audio = audio.T
            return audio, sr
        except ImportError:
            import scipy.io.wavfile as wavfile
            sr, audio = wavfile.read(path)
            audio = audio.astype(np.float64) / 32768.0
            if audio.ndim == 2:
                audio = audio.T
            return audio, sr

    def _load_lora(self, adapter_path: str) -> None:
        """Load a LoRA/LoKR adapter for style customization."""
        if self._dit_handler is None:
            return

        try:
            logger.info("Loading LoRA adapter from %s", adapter_path)
            # Try known ACE-Step adapter loading methods
            if hasattr(self._dit_handler, "load_lora"):
                self._dit_handler.load_lora(adapter_path)
            elif hasattr(self._dit_handler, "load_adapter"):
                self._dit_handler.load_adapter(adapter_path)
            else:
                logger.warning("AceStepHandler does not have a LoRA loading method")
        except Exception as e:
            logger.warning("Failed to load LoRA adapter: %s", e)

    def _generate_mock(
        self,
        prompt: str,
        duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[bytes, int, float]:
        """Mock generation for development without ACE-Step installed."""
        import time

        from lofty.worker.mock_generator import generate_procedural_music

        sample_rate = 48000  # ACE-Step default

        total_steps = 20
        step_delay = max(0.03, duration_seconds / 80)
        for step in range(total_steps):
            time.sleep(step_delay)
            if on_progress:
                pct = min(95, int((step + 1) / total_steps * 95))
                on_progress(pct)

        logger.info("ACE-Step MOCK mode: generating procedural music for: '%s'", prompt[:80])
        audio = generate_procedural_music(prompt, duration_seconds, sample_rate)

        audio_2d = audio[np.newaxis, :]
        wav_bytes = self.numpy_to_wav(audio_2d, sample_rate, n_channels=1)

        if on_progress:
            on_progress(100)

        return wav_bytes, sample_rate, duration_seconds
