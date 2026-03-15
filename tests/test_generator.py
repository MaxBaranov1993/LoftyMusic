"""Tests for the music generator (mock mode), procedural generator, and prompt enrichment."""

import io
import wave

import numpy as np
import pytest

from lofty.worker.generator import MusicGenerator, _enrich_prompt
from lofty.worker.mock_generator import generate_procedural_music


# ---------------------------------------------------------------------------
# Mock generator integration tests (via MusicGenerator)
# ---------------------------------------------------------------------------


def test_mock_generator():
    """Test that the mock generator produces valid WAV bytes."""
    gen = MusicGenerator(model_name="mock", device="cpu", cache_dir="/tmp")
    gen.load()

    wav_bytes, sample_rate, duration = gen._generate_mock(
        prompt="test electronic music",
        duration_seconds=2.0,
    )

    assert isinstance(wav_bytes, bytes)
    assert len(wav_bytes) > 0
    assert sample_rate == 32000
    assert abs(duration - 2.0) < 0.01

    # Verify it's a valid WAV file
    buffer = io.BytesIO(wav_bytes)
    with wave.open(buffer, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 32000
        assert wf.getnframes() == int(32000 * 2.0)


def test_mock_generator_different_prompts():
    """Test that different prompts produce different audio."""
    gen = MusicGenerator(model_name="mock", device="cpu", cache_dir="/tmp")

    wav1, _, _ = gen._generate_mock("jazz piano", 1.0)
    wav2, _, _ = gen._generate_mock("heavy metal guitar", 1.0)

    # Different prompts should produce different audio
    assert wav1 != wav2


def test_mock_generator_duration():
    """Test that the generator respects the requested duration."""
    gen = MusicGenerator(model_name="mock", device="cpu", cache_dir="/tmp")

    for dur in [1.0, 5.0, 10.0]:
        wav_bytes, sr, actual = gen._generate_mock("test", dur)
        buffer = io.BytesIO(wav_bytes)
        with wave.open(buffer, "rb") as wf:
            frames = wf.getnframes()
            expected_frames = int(sr * dur)
            assert frames == expected_frames


# ---------------------------------------------------------------------------
# Procedural generator unit tests
# ---------------------------------------------------------------------------


def test_procedural_output_shape():
    """Test that procedural generator returns correct array shape and type."""
    audio = generate_procedural_music("test melody", 3.0, sample_rate=32000)

    assert isinstance(audio, np.ndarray)
    assert audio.dtype == np.float32
    assert len(audio) == int(32000 * 3.0)


def test_procedural_output_range():
    """Test that output is normalized within [-1, 1]."""
    audio = generate_procedural_music("upbeat pop song", 5.0)

    assert np.max(audio) <= 1.0
    assert np.min(audio) >= -1.0
    # Should have actual audio content, not silence
    assert np.max(np.abs(audio)) > 0.1


def test_procedural_deterministic():
    """Test that same prompt produces identical output."""
    audio1 = generate_procedural_music("chill lofi beats", 2.0)
    audio2 = generate_procedural_music("chill lofi beats", 2.0)

    np.testing.assert_array_equal(audio1, audio2)


def test_procedural_different_prompts():
    """Test that different prompts produce different audio."""
    audio1 = generate_procedural_music("jazz piano", 2.0)
    audio2 = generate_procedural_music("heavy metal guitar", 2.0)

    assert not np.array_equal(audio1, audio2)


def test_procedural_genre_keywords():
    """Test that genre keywords in prompt affect the output."""
    audio_jazz = generate_procedural_music("smooth jazz saxophone", 2.0)
    audio_electronic = generate_procedural_music("smooth electronic synthesizer", 2.0)
    audio_rock = generate_procedural_music("smooth rock guitar", 2.0)

    # All three should be different from each other
    assert not np.array_equal(audio_jazz, audio_electronic)
    assert not np.array_equal(audio_jazz, audio_rock)
    assert not np.array_equal(audio_electronic, audio_rock)


def test_procedural_short_duration():
    """Test minimum duration edge case."""
    audio = generate_procedural_music("test", 0.5, sample_rate=32000)
    assert len(audio) == int(32000 * 0.5)
    assert np.max(np.abs(audio)) > 0


# ---------------------------------------------------------------------------
# Post-processing tests
# ---------------------------------------------------------------------------


def test_post_process():
    """Test the post-processing pipeline on MusicGenerator."""
    audio = np.zeros(32000, dtype=np.float64)
    audio[1000:2000] = 2.0
    audio[5000:6000] = -1.5

    processed = MusicGenerator._post_process(audio, 32000)

    assert np.max(processed) <= 1.0
    assert np.min(processed) >= -1.0
    assert processed[0] == 0.0


# ---------------------------------------------------------------------------
# WAV encoding tests (mono and stereo)
# ---------------------------------------------------------------------------


def test_numpy_to_wav_mono():
    """Test mono WAV encoding."""
    audio = np.random.randn(1, 16000).astype(np.float64)
    wav_bytes = MusicGenerator._numpy_to_wav(audio, 32000, n_channels=1)

    buffer = io.BytesIO(wav_bytes)
    with wave.open(buffer, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 32000


def test_numpy_to_wav_stereo():
    """Test stereo WAV encoding with proper interleaving."""
    audio = np.random.randn(2, 16000).astype(np.float64)
    wav_bytes = MusicGenerator._numpy_to_wav(audio, 32000, n_channels=2)

    buffer = io.BytesIO(wav_bytes)
    with wave.open(buffer, "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 32000
        assert wf.getnframes() == 16000


# ---------------------------------------------------------------------------
# Prompt enrichment tests
# ---------------------------------------------------------------------------


def test_enrich_prompt_adds_quality():
    """Test that all prompts get quality descriptors."""
    enriched = _enrich_prompt("random music")
    assert "high quality" in enriched
    assert "professional" in enriched


def test_enrich_prompt_genre():
    """Test that genre keywords trigger enrichment."""
    enriched = _enrich_prompt("smooth jazz piece")
    assert "saxophone" in enriched or "piano" in enriched


def test_enrich_prompt_mood():
    """Test that mood keywords trigger enrichment."""
    enriched = _enrich_prompt("sad piano melody")
    assert "melancholic" in enriched or "minor key" in enriched


def test_enrich_prompt_preserves_original():
    """Test that original prompt is preserved."""
    original = "my custom music description"
    enriched = _enrich_prompt(original)
    assert enriched.startswith(original)


def test_enrich_prompt_length_limit():
    """Test that enriched prompt doesn't exceed 500 chars."""
    long_prompt = "a" * 600
    enriched = _enrich_prompt(long_prompt)
    assert len(enriched) <= 500
