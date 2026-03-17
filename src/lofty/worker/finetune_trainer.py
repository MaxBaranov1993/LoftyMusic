"""LoRA/LoKR fine-tuning trainer using ACE-Step training API.

Uses the actual ACE-Step training pipeline:
  1. AceStepHandler.initialize_service() for VAE encoding
  2. DatasetBuilder.scan_directory() + update_sample() with metadata
  3. preprocess_to_tensors() via VAE + text encoder
  4. LoRATrainer/LoKRTrainer.train_from_preprocessed()
"""

import json
import logging
import os

from lofty.config import settings

logger = logging.getLogger(__name__)

# ACE-Step project root
_ACE_STEP_PROJECT_ROOT = os.environ.get(
    "ACE_STEP_PROJECT_ROOT",
    os.path.join(settings.ace_step_cache_dir, "ACE-Step-1.5"),
)


class FineTuneTrainer:
    """Manages ACE-Step LoRA/LoKR training."""

    def __init__(
        self,
        dataset_dir: str,
        output_dir: str,
        training_method: str = "lokr",
        max_epochs: int = 500,
        batch_size: int = 1,
        learning_rate: float = 1e-4,
    ):
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.training_method = training_method
        self.max_epochs = max_epochs
        self.batch_size = batch_size
        self.learning_rate = learning_rate

    def train(self, on_progress=None) -> str:
        """Run fine-tuning and return path to the adapter weights.

        Args:
            on_progress: Callable[[int], None] — reports 0-100 progress.

        Returns:
            Path to the output adapter directory.
        """
        if settings.mock_gpu:
            return self._train_mock(on_progress)

        return self._train_real(on_progress)

    def _train_real(self, on_progress=None) -> str:
        """Real training using ACE-Step's training pipeline.

        Matches the notebook v5 fine-tuning implementation:
        1. Initialize AceStepHandler (for VAE encoding during preprocessing)
        2. Build dataset via DatasetBuilder
        3. Preprocess audio to tensors (VAE encode)
        4. Train LoRA/LoKR adapter
        """
        import torch

        try:
            from acestep.handler import AceStepHandler
            from acestep.training import (
                DatasetBuilder,
                LoKRConfig,
                LoKRTrainer,
                LoRAConfig,
                LoRATrainer,
                TrainingConfig,
            )
        except ImportError:
            raise RuntimeError(
                "ACE-Step training modules not available. "
                "Install ACE-Step with training support: "
                "pip install -e '.[all]' from the ACE-Step-1.5 directory"
            )

        if on_progress:
            on_progress(0)

        os.makedirs(self.output_dir, exist_ok=True)

        # 1. Initialize handler for VAE encoding
        logger.info("Initializing AceStepHandler for preprocessing...")
        handler = AceStepHandler()

        config_path = "acestep-v15-turbo"
        # Try to find config file on disk
        for candidate in [
            os.path.join(_ACE_STEP_PROJECT_ROOT, "acestep/config/ace_step_v1.5_turbo.json"),
            os.path.join(_ACE_STEP_PROJECT_ROOT, "acestep", "config"),
        ]:
            if os.path.isfile(candidate):
                config_path = candidate
                break
            if os.path.isdir(candidate):
                jsons = [f for f in os.listdir(candidate) if f.endswith(".json")]
                if jsons:
                    config_path = os.path.join(candidate, jsons[0])
                    break

        msg, ok = handler.initialize_service(
            project_root=_ACE_STEP_PROJECT_ROOT,
            config_path=config_path,
            device="cuda" if torch.cuda.is_available() else "cpu",
            offload_to_cpu=settings.ace_step_cpu_offload,
        )
        logger.info("Handler init: %s", msg[:120])
        if not ok:
            raise RuntimeError(f"AceStepHandler init failed: {msg}")

        if on_progress:
            on_progress(10)

        # 2. Build dataset
        logger.info("Building dataset from %s...", self.dataset_dir)
        builder = DatasetBuilder()
        samples, scan_msg = builder.scan_directory(self.dataset_dir)
        logger.info("Found %d audio files", len(samples))
        if not samples:
            raise RuntimeError("No audio files found in dataset directory")

        # Load metadata from companion files
        for i in range(len(samples)):
            meta_path = None
            # Look for .json metadata file
            sample_path = samples[i].path if hasattr(samples[i], "path") else ""
            if sample_path:
                base = os.path.splitext(sample_path)[0]
                if os.path.exists(f"{base}.json"):
                    meta_path = f"{base}.json"

            kwargs = {"labeled": True}
            if meta_path:
                try:
                    with open(meta_path, encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("caption"):
                        kwargs["caption"] = meta["caption"]
                    if meta.get("bpm"):
                        kwargs["bpm"] = int(meta["bpm"])
                    if meta.get("key_scale"):
                        kwargs["keyscale"] = meta["key_scale"]
                except Exception as e:
                    logger.warning("Failed to read metadata %s: %s", meta_path, e)

            # Look for lyrics .txt file
            if sample_path:
                base = os.path.splitext(sample_path)[0]
                for lyrics_ext in [".txt", ".lyrics.txt"]:
                    lyrics_path = f"{base}{lyrics_ext}"
                    if os.path.exists(lyrics_path):
                        try:
                            with open(lyrics_path, encoding="utf-8") as f:
                                lyrics_text = f.read().strip()
                            if lyrics_text:
                                kwargs["lyrics"] = lyrics_text
                                kwargs["is_instrumental"] = False
                        except Exception:
                            pass
                        break
                else:
                    kwargs["is_instrumental"] = True

            builder.update_sample(i, **kwargs)

        if on_progress:
            on_progress(20)

        # 3. Preprocess to tensors (VAE encode)
        logger.info("Preprocessing audio to tensors...")
        tensor_dir = os.path.join(self.output_dir, "tensors")
        os.makedirs(tensor_dir, exist_ok=True)

        preprocess_mode = "lokr" if self.training_method == "lokr" else "lora"
        paths, preprocess_msg = builder.preprocess_to_tensors(
            dit_handler=handler,
            output_dir=tensor_dir,
            max_duration=240.0,
            preprocess_mode=preprocess_mode,
            progress_callback=lambda m: logger.info("Preprocess: %s", m),
        )
        logger.info("Preprocessed %d tensors", len(paths))
        if not paths:
            raise RuntimeError("Preprocessing produced no tensors")

        if on_progress:
            on_progress(40)

        # Free handler memory before training
        del builder
        torch.cuda.empty_cache()

        # 4. Train adapter
        logger.info("Starting %s training (%d epochs)...", self.training_method, self.max_epochs)

        # Detect optimal mixed precision
        mixed_precision = "fp16"
        if torch.cuda.is_available():
            cap = torch.cuda.get_device_capability()
            if cap[0] >= 8:
                mixed_precision = "bf16"

        training_config = TrainingConfig(
            learning_rate=self.learning_rate,
            batch_size=self.batch_size,
            max_epochs=self.max_epochs,
            output_dir=self.output_dir,
            gradient_accumulation_steps=4,
            save_every_n_epochs=max(self.max_epochs // 5, 10),
            warmup_steps=min(50, self.max_epochs * max(len(paths), 1) // 2),
            mixed_precision=mixed_precision,
            gradient_checkpointing=True,
            num_workers=2,
            seed=42,
        )

        if self.training_method == "lokr":
            adapter_config = LoKRConfig(linear_dim=64, linear_alpha=128)
            trainer = LoKRTrainer(handler, adapter_config, training_config)
        else:
            adapter_config = LoRAConfig(r=8, alpha=16, dropout=0.1)
            trainer = LoRATrainer(handler, adapter_config, training_config)

        training_state = {"stop": False}
        total_est = self.max_epochs * max(len(paths), 1)

        for step, loss, step_msg in trainer.train_from_preprocessed(
            tensor_dir=tensor_dir, training_state=training_state
        ):
            if on_progress:
                pct = min(40 + int(min(step / max(total_est, 1), 1.0) * 55), 95)
                on_progress(pct)

        logger.info("Training complete")

        # Cleanup
        del trainer
        torch.cuda.empty_cache()

        if on_progress:
            on_progress(100)

        # Find the adapter file
        adapter_file = self._find_adapter_file(self.output_dir)
        if adapter_file:
            logger.info("Adapter saved: %s", adapter_file)
            return os.path.dirname(adapter_file)

        return self.output_dir

    @staticmethod
    def _find_adapter_file(output_dir: str) -> str | None:
        """Find the adapter weights file in the output directory."""
        for ext in [".safetensors", ".bin", ".pt"]:
            for root, _, files in os.walk(output_dir):
                for f in files:
                    if f.endswith(ext):
                        return os.path.join(root, f)
        return None

    def _train_mock(self, on_progress=None) -> str:
        """Mock training for development without GPU."""
        import time

        logger.info("Mock training: simulating %d epochs", self.max_epochs)

        steps = 10
        for i in range(steps):
            time.sleep(0.5)
            if on_progress:
                on_progress(int((i + 1) / steps * 100))

        # Create a dummy adapter file
        os.makedirs(self.output_dir, exist_ok=True)
        adapter_path = os.path.join(self.output_dir, "adapter_model.safetensors")
        with open(adapter_path, "wb") as f:
            f.write(b"MOCK_ADAPTER_WEIGHTS" * 100)

        config_path = os.path.join(self.output_dir, "adapter_config.json")
        with open(config_path, "w") as f:
            json.dump(
                {
                    "method": self.training_method,
                    "base_model": settings.ace_step_model_path,
                    "epochs": self.max_epochs,
                    "mock": True,
                },
                f,
            )

        logger.info("Mock training complete: %s", self.output_dir)
        return self.output_dir


def prepare_dataset_directory(
    tracks: list[dict],
    storage_client,
    temp_dir: str,
) -> str:
    """Download dataset tracks from S3 and prepare ACE-Step training format.

    Args:
        tracks: List of dicts with keys: storage_key, original_filename,
                lyrics, caption, bpm, key_scale, format
        storage_client: StorageClient instance
        temp_dir: Temporary directory to store files

    Returns:
        Path to the prepared dataset directory.
    """
    dataset_dir = os.path.join(temp_dir, "dataset")
    os.makedirs(dataset_dir, exist_ok=True)

    for i, track in enumerate(tracks):
        # Download audio from S3
        audio_key = track["storage_key"]
        ext = track.get("format", "wav")
        audio_filename = f"track_{i:03d}.{ext}"
        audio_path = os.path.join(dataset_dir, audio_filename)

        # Download using boto3 get_object
        response = storage_client._client.get_object(
            Bucket=storage_client._bucket,
            Key=audio_key,
        )
        with open(audio_path, "wb") as f:
            for chunk in response["Body"].iter_chunks(8192):
                f.write(chunk)

        # Write lyrics file
        base_name = f"track_{i:03d}"
        lyrics = track.get("lyrics", "")
        if lyrics.strip():
            lyrics_path = os.path.join(dataset_dir, f"{base_name}.txt")
            with open(lyrics_path, "w", encoding="utf-8") as f:
                f.write(lyrics)

        # Write metadata JSON
        meta_path = os.path.join(dataset_dir, f"{base_name}.json")
        meta = {
            "caption": track.get("caption", ""),
            "bpm": track.get("bpm"),
            "key_scale": track.get("key_scale"),
            "time_signature": "4/4",
            "language": "en",
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    logger.info("Prepared %d tracks in %s", len(tracks), dataset_dir)
    return dataset_dir
