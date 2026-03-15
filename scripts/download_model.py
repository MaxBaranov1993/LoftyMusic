"""Pre-download the MusicGen model to local cache."""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Download MusicGen model weights")
    parser.add_argument(
        "--model",
        default="facebook/musicgen-small",
        help="HuggingFace model ID (default: facebook/musicgen-small)",
    )
    parser.add_argument(
        "--cache-dir",
        default="./model_cache",
        help="Directory to cache model files (default: ./model_cache)",
    )
    args = parser.parse_args()

    try:
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
    except ImportError:
        print("Error: transformers package not installed.")
        print("Install with: pip install -e '.[worker]'")
        sys.exit(1)

    print(f"Downloading model: {args.model}")
    print(f"Cache directory: {args.cache_dir}")

    print("Downloading processor...")
    AutoProcessor.from_pretrained(args.model, cache_dir=args.cache_dir)

    print("Downloading model weights...")
    MusicgenForConditionalGeneration.from_pretrained(args.model, cache_dir=args.cache_dir)

    print("Done! Model is cached and ready for inference.")


if __name__ == "__main__":
    main()
