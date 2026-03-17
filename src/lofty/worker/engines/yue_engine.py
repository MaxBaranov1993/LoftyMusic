"""YuE music generation engine.

YuE (by HKUST/M-A-P) is a 2-stage LLaMA-based model for lyrics-to-song generation.
It produces dual-track output (vocal + instrumental) mixed to stereo WAV at 44.1kHz.

Pipeline:
  Stage 1 (7B, m-a-p/YuE-s1-7B-anneal-en-cot): lyrics → semantic audio tokens
  Stage 2 (1B, m-a-p/YuE-s2-1B-general): semantic → acoustic tokens
  xcodec decoder: acoustic tokens → 16kHz waveform
  Vocoder upsampler: 16kHz → 44.1kHz

For free Google Colab (T4 GPU, 15GB VRAM):
  - Stage 1 uses 4-bit NF4 quantization via bitsandbytes (~4-5GB)
  - Stage 2 runs in bf16 (~2GB)
  - Max 2 segments (~60s total) to avoid OOM
  - stage2_batch_size=1 for safety
  - Flash Attention 2 for memory efficiency
"""

import gc
import logging
import math
import os
import re
import tempfile
from typing import Callable

import numpy as np

from lofty.config import settings
from lofty.worker.engines.base import MusicEngine

logger = logging.getLogger(__name__)


def _split_lyrics(lyrics: str) -> list[str]:
    """Split lyrics into structured segments by section markers.

    Mirrors the split_lyrics() function from YuE's infer.py.
    """
    pattern = r"\[(\w+)\](.*?)(?=\[|\Z)"
    segments = re.findall(pattern, lyrics, re.DOTALL)
    structured = [f"[{seg[0]}]\n{seg[1].strip()}\n\n" for seg in segments]
    return structured if structured else [lyrics.strip()]


def _select_stage1_model(language: str) -> str:
    """Select the appropriate Stage 1 model variant for the language."""
    lang_model_map = {
        "en": settings.yue_stage1_model,  # default en-cot
        "zh": "m-a-p/YuE-s1-7B-anneal-zh-cot",
        "ja": "m-a-p/YuE-s1-7B-anneal-jp-kr-cot",
        "ko": "m-a-p/YuE-s1-7B-anneal-jp-kr-cot",
    }
    return lang_model_map.get(language, settings.yue_stage1_model)


class YuEEngine(MusicEngine):
    """YuE engine for lyrics-to-song generation with vocals.

    Optimized for free Google Colab T4 GPU with 4-bit quantization.
    """

    def __init__(
        self,
        device: str = settings.model_device,
        cache_dir: str = "",
        use_4bit: bool = True,
    ) -> None:
        self.device = device
        self.cache_dir = cache_dir or settings.yue_cache_dir
        self.use_4bit = use_4bit if use_4bit is not None else settings.yue_use_4bit
        self._stage1_model = None
        self._stage2_model = None
        self._codec_model = None
        self._mmtokenizer = None
        self._codectool = None
        self._codectool_stage2 = None
        self._loaded = False
        self._mock_mode = False
        self._current_stage1_id = None

    @property
    def engine_name(self) -> str:
        return "yue"

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        if self._loaded:
            return

        if settings.mock_gpu:
            logger.info("MOCK_GPU=true — YuE running in mock mode")
            self._loaded = True
            self._mock_mode = True
            return

        try:
            self._load_tokenizer_and_codec()
            self._loaded = True
            self._mock_mode = False
            logger.info("YuEEngine ready (tokenizer + codec loaded, models load on demand)")
        except ImportError as e:
            logger.warning(
                "Cannot load YuE dependencies: %s. "
                "Install from: https://github.com/multimodal-art-projection/YuE "
                "Running in MOCK mode.",
                e,
            )
            self._loaded = True
            self._mock_mode = True
        except Exception as e:
            logger.warning("Cannot initialize YuE: %s. Running in MOCK mode.", e)
            self._loaded = True
            self._mock_mode = True

    def _load_tokenizer_and_codec(self) -> None:
        """Load the MM tokenizer and xcodec model (lightweight, always needed)."""
        import sys
        import torch
        from omegaconf import OmegaConf

        # Ensure inference dir is on path for YuE imports
        yue_inference_dir = os.environ.get("YUE_INFERENCE_DIR", "")
        if yue_inference_dir and yue_inference_dir not in sys.path:
            sys.path.insert(0, yue_inference_dir)
            xcodec_dir = os.path.join(yue_inference_dir, "xcodec_mini_infer")
            if os.path.isdir(xcodec_dir):
                sys.path.insert(0, xcodec_dir)
                dac_dir = os.path.join(xcodec_dir, "descriptaudiocodec")
                if os.path.isdir(dac_dir):
                    sys.path.insert(0, dac_dir)

        from codecmanipulator import CodecManipulator
        from mmtokenizer import _MMSentencePieceTokenizer

        # Tokenizer
        tokenizer_path = os.path.join(
            yue_inference_dir or ".", "mm_tokenizer_v0.2_hf", "tokenizer.model"
        )
        self._mmtokenizer = _MMSentencePieceTokenizer(tokenizer_path)

        # Codec tools
        self._codectool = CodecManipulator("xcodec", 0, 1)
        self._codectool_stage2 = CodecManipulator("xcodec", 0, 8)

        # xcodec model
        xcodec_config_path = os.path.join(
            yue_inference_dir or ".", "xcodec_mini_infer", "final_ckpt", "config.yaml"
        )
        xcodec_ckpt_path = os.path.join(
            yue_inference_dir or ".", "xcodec_mini_infer", "final_ckpt", "ckpt_00360000.pth"
        )

        if os.path.exists(xcodec_config_path):
            from models.soundstream_hubert_new import SoundStream

            device = torch.device(self.device if torch.cuda.is_available() else "cpu")
            model_config = OmegaConf.load(xcodec_config_path)
            self._codec_model = eval(model_config.generator.name)(
                **model_config.generator.config
            ).to(device)
            params = torch.load(xcodec_ckpt_path, map_location="cpu", weights_only=False)
            self._codec_model.load_state_dict(params["codec_model"])
            self._codec_model.eval()
            logger.info("xcodec model loaded")

    @staticmethod
    def _get_optimal_dtype():
        """Select optimal dtype based on GPU capability.

        T4 (sm_75) does not support bf16 natively — use float16.
        A100/L4/H100 (sm_80+) support bf16.
        """
        try:
            import torch
            if torch.cuda.is_available():
                cap = torch.cuda.get_device_capability()
                if cap[0] >= 8:
                    return torch.bfloat16
            return torch.float16
        except Exception:
            import torch
            return torch.float16

    def _load_stage1(self, model_id: str) -> None:
        """Load Stage 1 (7B) model with 4-bit quantization."""
        import torch
        from transformers import AutoModelForCausalLM

        if self._stage1_model is not None and self._current_stage1_id == model_id:
            return

        # Unload existing stage1 if different model
        if self._stage1_model is not None:
            del self._stage1_model
            self._stage1_model = None
            torch.cuda.empty_cache()
            gc.collect()

        device = torch.device(self.device if torch.cuda.is_available() else "cpu")
        dtype = self._get_optimal_dtype()
        logger.info("Loading YuE Stage 1 model: %s (4bit=%s, dtype=%s)", model_id, self.use_4bit, dtype)

        load_kwargs = {
            "torch_dtype": dtype,
            "cache_dir": self.cache_dir,
        }

        # Use flash attention if available
        try:
            import flash_attn  # noqa: F401
            load_kwargs["attn_implementation"] = "flash_attention_2"
        except ImportError:
            logger.info("flash-attn not available, using default attention")

        if self.use_4bit:
            from transformers import BitsAndBytesConfig

            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )
            load_kwargs["device_map"] = "auto"
        else:
            load_kwargs["device_map"] = None

        self._stage1_model = AutoModelForCausalLM.from_pretrained(model_id, **load_kwargs)
        if not self.use_4bit:
            self._stage1_model.to(device)
        self._stage1_model.eval()
        self._current_stage1_id = model_id

        logger.info("Stage 1 model loaded")

    def _load_stage2(self) -> None:
        """Load Stage 2 (1B) model. Uses float16 on T4, bf16 on A100+."""
        if self._stage2_model is not None:
            return

        import torch
        from transformers import AutoModelForCausalLM

        device = torch.device(self.device if torch.cuda.is_available() else "cpu")
        dtype = self._get_optimal_dtype()
        logger.info("Loading YuE Stage 2 model: %s (dtype=%s)", settings.yue_stage2_model, dtype)

        load_kwargs = {
            "torch_dtype": dtype,
            "cache_dir": self.cache_dir,
        }

        try:
            import flash_attn  # noqa: F401
            load_kwargs["attn_implementation"] = "flash_attention_2"
        except ImportError:
            pass

        self._stage2_model = AutoModelForCausalLM.from_pretrained(
            settings.yue_stage2_model, **load_kwargs
        )
        self._stage2_model.to(device)
        self._stage2_model.eval()
        logger.info("Stage 2 model loaded")

    def _offload_stage1(self) -> None:
        """Offload Stage 1 from GPU to free VRAM for Stage 2."""
        if self._stage1_model is not None:
            del self._stage1_model
            self._stage1_model = None
            self._current_stage1_id = None
        import torch

        torch.cuda.empty_cache()
        gc.collect()
        logger.info("Stage 1 offloaded from GPU")

    def _offload_stage2(self) -> None:
        """Offload Stage 2 from GPU."""
        if self._stage2_model is not None:
            del self._stage2_model
            self._stage2_model = None
        import torch

        torch.cuda.empty_cache()
        gc.collect()

    def unload(self) -> None:
        self._offload_stage1()
        self._offload_stage2()
        self._codec_model = None
        self._mmtokenizer = None
        self._codectool = None
        self._codectool_stage2 = None
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
        duration_seconds: float = 30.0,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        """Generate a song from genre tags (prompt) and lyrics.

        YuE-specific params (via **params):
            lyrics: str — structured lyrics with [verse], [chorus] markers
            temperature: float — sampling temperature (default 1.0)
            top_p: float — nucleus sampling (default 0.93)
            repetition_penalty: float — repetition penalty (default 1.1)
            max_new_tokens: int — max tokens per segment (default 3000, ~30s)
            num_segments: int — number of segments to generate (default 2, max 2)
            language: str — language code for model selection (en/zh/ja/ko)
            seed: int — random seed (default 42)
        """
        if self._mock_mode:
            return self._generate_mock(prompt, duration_seconds, on_progress)

        return self._generate_real(prompt, duration_seconds, on_progress, **params)

    def _generate_real(
        self,
        prompt: str,
        duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
        **params,
    ) -> tuple[bytes, int, float]:
        import copy
        import random
        from collections import Counter

        import torch
        import torchaudio
        from einops import rearrange
        from transformers import LogitsProcessor, LogitsProcessorList

        lyrics = params.get("lyrics", "")
        temperature = params.get("temperature", 1.0)
        top_p = params.get("top_p", 0.93)
        repetition_penalty = params.get("repetition_penalty", 1.1)
        max_new_tokens = params.get("max_new_tokens", 3000)
        num_segments = min(params.get("num_segments", 2), 2)
        language = params.get("language", "en")
        seed = params.get("seed", 42)

        # Cap duration to max
        duration_seconds = min(duration_seconds, settings.yue_max_duration_seconds)
        # Calculate segments from duration if not explicit
        if num_segments < 1:
            num_segments = max(1, min(2, math.ceil(duration_seconds / 30)))

        logger.info(
            "YuE generating: segments=%d, duration=%.1fs, temp=%.2f, top_p=%.2f, "
            "rep_penalty=%.2f, max_tokens=%d, lang=%s",
            num_segments, duration_seconds, temperature, top_p,
            repetition_penalty, max_new_tokens, language,
        )

        # Seed
        self._seed_everything(seed)

        if on_progress:
            on_progress(5)

        # Select and load Stage 1 model based on language
        stage1_model_id = _select_stage1_model(language)
        self._load_stage1(stage1_model_id)

        device = next(self._stage1_model.parameters()).device

        if on_progress:
            on_progress(10)

        # Parse lyrics into segments
        lyrics_segments = _split_lyrics(lyrics)
        full_lyrics = "\n".join(lyrics_segments)

        # Build prompt texts (YuE format)
        genres = prompt.strip()
        prompt_texts = [
            f"Generate music from the given lyrics segment by segment.\n[Genre] {genres}\n{full_lyrics}"
        ]
        prompt_texts += lyrics_segments

        # Token IDs
        mmtok = self._mmtokenizer
        codectool = self._codectool
        start_of_segment = mmtok.tokenize("[start_of_segment]")
        end_of_segment = mmtok.tokenize("[end_of_segment]")

        # Block processor to restrict token ranges
        class BlockTokenRangeProcessor(LogitsProcessor):
            def __init__(self, start_id, end_id):
                self.blocked = list(range(start_id, end_id))

            def __call__(self, input_ids, scores):
                scores[:, self.blocked] = -float("inf")
                return scores

        # Stage 1: Generate semantic tokens segment by segment
        run_n = min(num_segments + 1, len(prompt_texts))
        raw_output = None

        for i in range(1, run_n):
            section_text = prompt_texts[i].replace("[start_of_segment]", "").replace(
                "[end_of_segment]", ""
            )

            if i == 1:
                head_id = mmtok.tokenize(prompt_texts[0])
                prompt_ids = (
                    head_id
                    + start_of_segment
                    + mmtok.tokenize(section_text)
                    + [mmtok.soa]
                    + codectool.sep_ids
                )
            else:
                prompt_ids = (
                    end_of_segment
                    + start_of_segment
                    + mmtok.tokenize(section_text)
                    + [mmtok.soa]
                    + codectool.sep_ids
                )

            prompt_ids_t = torch.as_tensor(prompt_ids).unsqueeze(0).to(device)
            input_ids = (
                torch.cat([raw_output, prompt_ids_t], dim=1) if i > 1 else prompt_ids_t
            )

            # Window slicing for context limit
            max_context = 16384 - max_new_tokens - 1
            if input_ids.shape[-1] > max_context:
                input_ids = input_ids[:, -max_context:]

            with torch.no_grad():
                output_seq = self._stage1_model.generate(
                    input_ids=input_ids,
                    max_new_tokens=max_new_tokens,
                    min_new_tokens=100,
                    do_sample=True,
                    top_p=top_p,
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    eos_token_id=mmtok.eoa,
                    pad_token_id=mmtok.eoa,
                    logits_processor=LogitsProcessorList(
                        [
                            BlockTokenRangeProcessor(0, 32002),
                            BlockTokenRangeProcessor(32016, 32016),
                        ]
                    ),
                )

                if output_seq[0][-1].item() != mmtok.eoa:
                    tensor_eoa = torch.as_tensor([[mmtok.eoa]]).to(device)
                    output_seq = torch.cat((output_seq, tensor_eoa), dim=1)

            if i > 1:
                raw_output = torch.cat(
                    [raw_output, prompt_ids_t, output_seq[:, input_ids.shape[-1] :]],
                    dim=1,
                )
            else:
                raw_output = output_seq

            # Report progress for each segment
            if on_progress:
                seg_pct = 10 + int((i / (run_n - 1)) * 40)
                on_progress(min(seg_pct, 50))

        if on_progress:
            on_progress(50)

        # Extract vocal and instrumental codec IDs from stage 1 output
        ids = raw_output[0].cpu().numpy()
        soa_idx = np.where(ids == mmtok.soa)[0].tolist()
        eoa_idx = np.where(ids == mmtok.eoa)[0].tolist()

        if len(soa_idx) != len(eoa_idx):
            raise RuntimeError(
                f"Invalid soa/eoa pairs: {len(soa_idx)} soa vs {len(eoa_idx)} eoa"
            )

        vocals_list = []
        instrumentals_list = []
        for idx in range(len(soa_idx)):
            codec_ids = ids[soa_idx[idx] + 1 : eoa_idx[idx]]
            if len(codec_ids) > 0 and codec_ids[0] == 32016:
                codec_ids = codec_ids[1:]
            codec_ids = codec_ids[: 2 * (codec_ids.shape[0] // 2)]
            vocals_ids = codectool.ids2npy(
                rearrange(codec_ids, "(n b) -> b n", b=2)[0]
            )
            instrumentals_ids = codectool.ids2npy(
                rearrange(codec_ids, "(n b) -> b n", b=2)[1]
            )
            vocals_list.append(vocals_ids)
            instrumentals_list.append(instrumentals_ids)

        vocals_npy = np.concatenate(vocals_list, axis=1)
        instrumentals_npy = np.concatenate(instrumentals_list, axis=1)

        # Save stage 1 outputs to temp files
        with tempfile.TemporaryDirectory(prefix="lofty_yue_") as tmpdir:
            vocal_path = os.path.join(tmpdir, "stage1_vocal.npy")
            inst_path = os.path.join(tmpdir, "stage1_inst.npy")
            np.save(vocal_path, vocals_npy)
            np.save(inst_path, instrumentals_npy)
            stage1_outputs = [vocal_path, inst_path]

            # Offload stage 1, load stage 2
            self._offload_stage1()
            if on_progress:
                on_progress(55)

            self._load_stage2()
            if on_progress:
                on_progress(60)

            # Stage 2: Refine tokens
            stage2_results = self._stage2_inference(
                stage1_outputs, tmpdir, batch_size=1, on_progress=on_progress
            )

            if on_progress:
                on_progress(80)

            # Offload stage 2
            self._offload_stage2()

            # Decode audio from tokens via xcodec
            codec_device = next(self._codec_model.parameters()).device
            tracks = []
            for npy_path in stage2_results:
                codec_result = np.load(npy_path)
                with torch.no_grad():
                    decoded = self._codec_model.decode(
                        torch.as_tensor(
                            codec_result.astype(np.int16), dtype=torch.long
                        )
                        .unsqueeze(0)
                        .permute(1, 0, 2)
                        .to(codec_device)
                    )
                decoded = decoded.cpu().squeeze(0)
                tracks.append(decoded)

            if on_progress:
                on_progress(90)

            # Mix vocal + instrumental
            if len(tracks) == 2:
                # Ensure same length
                min_len = min(tracks[0].shape[-1], tracks[1].shape[-1])
                vocal_audio = tracks[0][..., :min_len]
                inst_audio = tracks[1][..., :min_len]
                mixed = (vocal_audio + inst_audio) / 2.0
            elif len(tracks) == 1:
                mixed = tracks[0]
            else:
                raise RuntimeError("No audio tracks decoded")

            # Convert to numpy
            mixed_np = mixed.numpy()
            if mixed_np.ndim == 1:
                mixed_np = mixed_np[np.newaxis, :]

            # xcodec outputs at 16kHz — try to upsample via vocoder if available
            sample_rate = 16000
            try:
                mixed_np, sample_rate = self._upsample_vocoder(
                    stage2_results, tmpdir, codec_device
                )
                if on_progress:
                    on_progress(95)
            except Exception as e:
                logger.warning("Vocoder upsampling failed, using 16kHz output: %s", e)

        # Build WAV
        n_channels = min(mixed_np.shape[0], 2) if mixed_np.ndim > 1 else 1
        if mixed_np.ndim == 1:
            mixed_np = mixed_np[np.newaxis, :]
        wav_bytes = self.numpy_to_wav(mixed_np[:n_channels], sample_rate, n_channels)
        actual_duration = mixed_np.shape[-1] / sample_rate

        if on_progress:
            on_progress(100)

        logger.info(
            "YuE generated %.1fs audio at %dHz (%d channels)",
            actual_duration, sample_rate, n_channels,
        )

        return wav_bytes, sample_rate, actual_duration

    def _stage2_inference(
        self,
        stage1_outputs: list[str],
        output_dir: str,
        batch_size: int = 1,
        on_progress: Callable[[int], None] | None = None,
    ) -> list[str]:
        """Run Stage 2 refinement on stage 1 outputs."""
        import copy
        from collections import Counter

        import torch
        from transformers import LogitsProcessorList

        class BlockTokenRangeProcessor:
            def __init__(self, start_id, end_id):
                self.blocked = list(range(start_id, end_id))

            def __call__(self, input_ids, scores):
                scores[:, self.blocked] = -float("inf")
                return scores

        mmtok = self._mmtokenizer
        codectool = self._codectool
        codectool_s2 = self._codectool_stage2
        device = next(self._stage2_model.parameters()).device

        block_list = LogitsProcessorList(
            [
                BlockTokenRangeProcessor(0, 46358),
                BlockTokenRangeProcessor(53526, mmtok.vocab_size),
            ]
        )

        results = []
        for file_idx, npy_path in enumerate(stage1_outputs):
            out_path = os.path.join(output_dir, f"stage2_{file_idx}.npy")
            prompt = np.load(npy_path).astype(np.int32)

            # Process in 6-second chunks
            output_duration = prompt.shape[-1] // 50 // 6 * 6
            num_batch = output_duration // 6

            if num_batch <= batch_size:
                output = self._stage2_generate_batch(
                    prompt[:, : output_duration * 50],
                    batch_size=num_batch,
                    device=device,
                    block_list=block_list,
                )
            else:
                segments = []
                num_segs = (num_batch // batch_size) + (
                    1 if num_batch % batch_size != 0 else 0
                )
                for seg in range(num_segs):
                    start = seg * batch_size * 300
                    end = min((seg + 1) * batch_size * 300, output_duration * 50)
                    cur_bs = (
                        batch_size
                        if seg != num_segs - 1 or num_batch % batch_size == 0
                        else num_batch % batch_size
                    )
                    segment = self._stage2_generate_batch(
                        prompt[:, start:end],
                        batch_size=cur_bs,
                        device=device,
                        block_list=block_list,
                    )
                    segments.append(segment)
                output = np.concatenate(segments, axis=0)

            # Process ending if needed
            if output_duration * 50 != prompt.shape[-1]:
                ending = self._stage2_generate_batch(
                    prompt[:, output_duration * 50 :],
                    batch_size=1,
                    device=device,
                    block_list=block_list,
                )
                output = np.concatenate([output, ending], axis=0)

            output = codectool_s2.ids2npy(output)

            # Fix invalid codes
            fixed = copy.deepcopy(output)
            for i, line in enumerate(output):
                for j, elem in enumerate(line):
                    if elem < 0 or elem > 1023:
                        counter = Counter(line)
                        most_freq = sorted(counter.items(), key=lambda x: x[1], reverse=True)[0][0]
                        fixed[i, j] = most_freq

            np.save(out_path, fixed)
            results.append(out_path)

            if on_progress:
                pct = 60 + int((file_idx + 1) / len(stage1_outputs) * 20)
                on_progress(min(pct, 80))

        return results

    def _stage2_generate_batch(
        self,
        prompt: np.ndarray,
        batch_size: int,
        device,
        block_list,
    ) -> np.ndarray:
        """Run Stage 2 teacher-forcing generation for a batch of chunks."""
        import torch

        mmtok = self._mmtokenizer
        codectool = self._codectool

        codec_ids = codectool.unflatten(prompt, n_quantizer=1)
        codec_ids = codectool.offset_tok_ids(
            codec_ids,
            global_offset=codectool.global_offset,
            codebook_size=codectool.codebook_size,
            num_codebooks=codectool.num_codebooks,
        ).astype(np.int32)

        if batch_size > 1:
            codec_list = []
            for i in range(batch_size):
                codec_list.append(codec_ids[:, i * 300 : (i + 1) * 300])
            codec_ids = np.concatenate(codec_list, axis=0)
            prompt_ids = np.concatenate(
                [
                    np.tile([mmtok.soa, mmtok.stage_1], (batch_size, 1)),
                    codec_ids,
                    np.tile([mmtok.stage_2], (batch_size, 1)),
                ],
                axis=1,
            )
        else:
            prompt_ids = np.concatenate(
                [
                    np.array([mmtok.soa, mmtok.stage_1]),
                    codec_ids.flatten(),
                    np.array([mmtok.stage_2]),
                ]
            ).astype(np.int32)
            prompt_ids = prompt_ids[np.newaxis, ...]

        codec_ids_t = torch.as_tensor(codec_ids).to(device)
        prompt_ids_t = torch.as_tensor(prompt_ids).to(device)
        len_prompt = prompt_ids_t.shape[-1]

        # Teacher-forcing: feed one frame at a time, generate 7 new tokens
        for frame_idx in range(codec_ids_t.shape[1]):
            cb0 = codec_ids_t[:, frame_idx : frame_idx + 1]
            prompt_ids_t = torch.cat([prompt_ids_t, cb0], dim=1)

            with torch.no_grad():
                stage2_out = self._stage2_model.generate(
                    input_ids=prompt_ids_t,
                    min_new_tokens=7,
                    max_new_tokens=7,
                    eos_token_id=mmtok.eoa,
                    pad_token_id=mmtok.eoa,
                    logits_processor=block_list,
                )

            prompt_ids_t = stage2_out

        if batch_size > 1:
            output = prompt_ids_t.cpu().numpy()[:, len_prompt:]
            output = np.concatenate([output[i] for i in range(batch_size)], axis=0)
        else:
            output = prompt_ids_t[0].cpu().numpy()[len_prompt:]

        return output

    def _upsample_vocoder(
        self, stage2_results: list[str], tmpdir: str, device
    ) -> tuple[np.ndarray, int]:
        """Try to upsample via YuE's vocoder for 44.1kHz output."""
        from vocoder import build_codec_model, process_audio

        yue_inference_dir = os.environ.get("YUE_INFERENCE_DIR", ".")
        config_path = os.path.join(
            yue_inference_dir, "xcodec_mini_infer", "decoders", "config.yaml"
        )
        vocal_decoder_path = os.path.join(
            yue_inference_dir, "xcodec_mini_infer", "decoders", "decoder_131000.pth"
        )
        inst_decoder_path = os.path.join(
            yue_inference_dir, "xcodec_mini_infer", "decoders", "decoder_151000.pth"
        )

        vocal_decoder, inst_decoder = build_codec_model(
            config_path, vocal_decoder_path, inst_decoder_path
        )

        import argparse

        args = argparse.Namespace(
            basic_model_config=os.path.join(
                yue_inference_dir, "xcodec_mini_infer", "final_ckpt", "config.yaml"
            ),
            resume_path=os.path.join(
                yue_inference_dir, "xcodec_mini_infer", "final_ckpt", "ckpt_00360000.pth"
            ),
            config_path=config_path,
            vocal_decoder_path=vocal_decoder_path,
            inst_decoder_path=inst_decoder_path,
            rescale=True,
        )

        vocal_output = None
        inst_output = None

        for npy_path in stage2_results:
            stems_dir = os.path.join(tmpdir, "vocoder_stems")
            os.makedirs(stems_dir, exist_ok=True)

            if "0" in os.path.basename(npy_path):  # vocal track
                vocal_output = process_audio(
                    npy_path,
                    os.path.join(stems_dir, "vtrack.mp3"),
                    True,
                    args,
                    vocal_decoder,
                    self._codec_model,
                )
            else:  # instrumental track
                inst_output = process_audio(
                    npy_path,
                    os.path.join(stems_dir, "itrack.mp3"),
                    True,
                    args,
                    inst_decoder,
                    self._codec_model,
                )

        if vocal_output is not None and inst_output is not None:
            min_len = min(vocal_output.shape[-1], inst_output.shape[-1])
            mixed = vocal_output[..., :min_len] + inst_output[..., :min_len]
            mixed_np = mixed.numpy() if hasattr(mixed, "numpy") else np.array(mixed)
            if mixed_np.ndim == 1:
                mixed_np = mixed_np[np.newaxis, :]
            return mixed_np, 44100
        elif vocal_output is not None:
            mixed_np = vocal_output.numpy() if hasattr(vocal_output, "numpy") else np.array(vocal_output)
            if mixed_np.ndim == 1:
                mixed_np = mixed_np[np.newaxis, :]
            return mixed_np, 44100

        raise RuntimeError("Vocoder produced no output")

    @staticmethod
    def _seed_everything(seed: int = 42) -> None:
        import random

        import torch

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    def _generate_mock(
        self,
        prompt: str,
        duration_seconds: float,
        on_progress: Callable[[int], None] | None = None,
    ) -> tuple[bytes, int, float]:
        """Mock generation for development without YuE installed."""
        import time

        from lofty.worker.mock_generator import generate_procedural_music

        sample_rate = 44100

        # Simulate slower YuE generation (~3-6 min on T4)
        total_steps = 30
        step_delay = max(0.05, duration_seconds / 60)
        for step in range(total_steps):
            time.sleep(step_delay)
            if on_progress:
                pct = min(95, int((step + 1) / total_steps * 95))
                on_progress(pct)

        logger.info("YuE MOCK mode: generating procedural music for: '%s'", prompt[:80])
        audio = generate_procedural_music(prompt, duration_seconds, sample_rate)

        audio_2d = audio[np.newaxis, :]
        wav_bytes = self.numpy_to_wav(audio_2d, sample_rate, n_channels=1)

        if on_progress:
            on_progress(100)

        return wav_bytes, sample_rate, duration_seconds
