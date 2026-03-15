"""Procedural music generator for mock/development mode.

Generates multi-layered melodic audio using only numpy — no ML model required.
Produces bass lines, chord pads, and lead melodies with ADSR envelopes,
seeded deterministically from the text prompt.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Musical constants
# ---------------------------------------------------------------------------

# Semitone intervals from root for common scales
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "pentatonic": [0, 2, 4, 7, 9],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}

# Chord progressions as scale-degree indices (0-based)
PROGRESSIONS = {
    "major": [
        [0, 3, 4, 0],    # I-IV-V-I
        [0, 4, 5, 3],    # I-V-vi-IV
        [0, 5, 3, 4],    # I-vi-IV-V
        [0, 3, 0, 4],    # I-IV-I-V
    ],
    "minor": [
        [0, 3, 6, 4],    # i-iv-VII-v
        [0, 5, 3, 6],    # i-vi-iv-VII
        [0, 6, 5, 4],    # i-VII-vi-v
        [0, 3, 4, 0],    # i-iv-v-i
    ],
}

# Genre keyword mappings
GENRE_HINTS = {
    "drum and bass": {"bpm": (170, 180), "scale": "minor", "swing": 0.0, "wave": "sawtooth"},
    "dnb": {"bpm": (170, 180), "scale": "minor", "swing": 0.0, "wave": "sawtooth"},
    "drum": {"bpm": (170, 180), "scale": "minor", "swing": 0.0, "wave": "sawtooth"},
    "jungle": {"bpm": (160, 175), "scale": "minor", "swing": 0.1, "wave": "sawtooth"},
    "dubstep": {"bpm": (138, 142), "scale": "minor", "swing": 0.0, "wave": "square"},
    "house": {"bpm": (120, 130), "scale": "minor", "swing": 0.0, "wave": "square"},
    "trance": {"bpm": (135, 150), "scale": "minor", "swing": 0.0, "wave": "sawtooth"},
    "jazz": {"bpm": (90, 130), "scale": "dorian", "swing": 0.3, "wave": "sine"},
    "blues": {"bpm": (70, 110), "scale": "blues", "swing": 0.2, "wave": "sine"},
    "electronic": {"bpm": (120, 150), "scale": "minor", "swing": 0.0, "wave": "square"},
    "techno": {"bpm": (125, 145), "scale": "minor", "swing": 0.0, "wave": "square"},
    "edm": {"bpm": (125, 150), "scale": "minor", "swing": 0.0, "wave": "square"},
    "classical": {"bpm": (70, 110), "scale": "major", "swing": 0.0, "wave": "sine"},
    "piano": {"bpm": (80, 120), "scale": "major", "swing": 0.0, "wave": "sine"},
    "rock": {"bpm": (110, 140), "scale": "pentatonic", "swing": 0.0, "wave": "sawtooth"},
    "metal": {"bpm": (130, 170), "scale": "minor", "swing": 0.0, "wave": "sawtooth"},
    "pop": {"bpm": (100, 130), "scale": "major", "swing": 0.0, "wave": "triangle"},
    "ambient": {"bpm": (60, 90), "scale": "pentatonic", "swing": 0.0, "wave": "sine"},
    "chill": {"bpm": (70, 100), "scale": "pentatonic", "swing": 0.1, "wave": "sine"},
    "lofi": {"bpm": (70, 95), "scale": "dorian", "swing": 0.15, "wave": "triangle"},
    "hip-hop": {"bpm": (80, 110), "scale": "minor", "swing": 0.1, "wave": "triangle"},
    "funk": {"bpm": (100, 125), "scale": "dorian", "swing": 0.2, "wave": "square"},
    "reggae": {"bpm": (70, 95), "scale": "major", "swing": 0.15, "wave": "sine"},
    "r&b": {"bpm": (85, 115), "scale": "dorian", "swing": 0.1, "wave": "sine"},
    "trap": {"bpm": (130, 170), "scale": "minor", "swing": 0.0, "wave": "square"},
}


# ---------------------------------------------------------------------------
# Waveform generators
# ---------------------------------------------------------------------------

def _sine(phase: np.ndarray) -> np.ndarray:
    return np.sin(phase)


def _triangle(phase: np.ndarray) -> np.ndarray:
    return 2.0 * np.abs(2.0 * (phase / (2 * np.pi) % 1.0) - 1.0) - 1.0


def _sawtooth(phase: np.ndarray) -> np.ndarray:
    return 2.0 * (phase / (2 * np.pi) % 1.0) - 1.0


def _square(phase: np.ndarray) -> np.ndarray:
    return np.sign(np.sin(phase))


WAVE_FUNCS = {
    "sine": _sine,
    "triangle": _triangle,
    "sawtooth": _sawtooth,
    "square": _square,
}


# ---------------------------------------------------------------------------
# ADSR envelope
# ---------------------------------------------------------------------------

def _adsr_envelope(
    n_samples: int,
    sample_rate: int,
    attack_ms: float = 30,
    decay_ms: float = 80,
    sustain_level: float = 0.6,
    release_ms: float = 60,
) -> np.ndarray:
    """Generate an ADSR envelope curve."""
    a = int(sample_rate * attack_ms / 1000)
    d = int(sample_rate * decay_ms / 1000)
    r = int(sample_rate * release_ms / 1000)
    s = max(0, n_samples - a - d - r)

    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False),
        np.linspace(1, sustain_level, d, endpoint=False),
        np.full(s, sustain_level),
        np.linspace(sustain_level, 0, r, endpoint=True),
    ])
    # Trim or pad to exact length
    if len(env) > n_samples:
        env = env[:n_samples]
    elif len(env) < n_samples:
        env = np.pad(env, (0, n_samples - len(env)))
    return env


# ---------------------------------------------------------------------------
# Note frequency helper
# ---------------------------------------------------------------------------

def _midi_to_freq(midi_note: int) -> float:
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


# ---------------------------------------------------------------------------
# Prompt analysis
# ---------------------------------------------------------------------------

def _parse_prompt(prompt: str, rng: np.random.Generator) -> dict:
    """Extract musical parameters from prompt text."""
    lower = prompt.lower()

    # Find genre hints
    matched_genre = None
    for keyword, hints in GENRE_HINTS.items():
        if keyword in lower:
            matched_genre = hints
            break

    if matched_genre is None:
        # Default: pick based on prompt hash
        default_scales = ["major", "minor", "pentatonic"]
        scale_name = rng.choice(default_scales)
        bpm = int(rng.integers(90, 130))
        swing = 0.0
        wave = rng.choice(["sine", "triangle"])
    else:
        scale_name = matched_genre["scale"]
        bpm = int(rng.integers(*matched_genre["bpm"]))
        swing = matched_genre["swing"]
        wave = matched_genre["wave"]

    # Determine mode (major/minor) for chord progressions
    mode = "minor" if scale_name in ("minor", "blues", "dorian") else "major"

    # Pick root note: C3-B3 (MIDI 48-59)
    root_midi = 48 + (sum(ord(c) for c in prompt) % 12)

    return {
        "bpm": bpm,
        "scale_name": scale_name,
        "scale": SCALES[scale_name],
        "mode": mode,
        "root_midi": root_midi,
        "swing": swing,
        "wave": wave,
    }


# ---------------------------------------------------------------------------
# Layer renderers
# ---------------------------------------------------------------------------

def _render_note(
    freq: float,
    duration_samples: int,
    sample_rate: int,
    wave_func,
    adsr_params: dict | None = None,
    vibrato_hz: float = 0.0,
    vibrato_depth: float = 0.0,
) -> np.ndarray:
    """Render a single note with envelope and optional vibrato."""
    t = np.arange(duration_samples) / sample_rate
    phase = 2 * np.pi * freq * t

    if vibrato_hz > 0 and vibrato_depth > 0:
        phase += vibrato_depth * np.sin(2 * np.pi * vibrato_hz * t)

    audio = wave_func(phase)

    params = adsr_params or {}
    env = _adsr_envelope(duration_samples, sample_rate, **params)
    return audio * env


def _render_bass(
    t_total: np.ndarray,
    sample_rate: int,
    chord_notes: list[list[int]],
    beat_duration: float,
    beats_per_chord: int,
    duration_seconds: float,
) -> np.ndarray:
    """Render bass line: root notes of each chord, octave below."""
    audio = np.zeros(len(t_total), dtype=np.float64)
    samples_per_chord = int(beat_duration * beats_per_chord * sample_rate)
    chord_idx = 0
    pos = 0

    while pos < len(audio):
        chord = chord_notes[chord_idx % len(chord_notes)]
        root_freq = _midi_to_freq(chord[0] - 12)  # One octave down
        note_len = min(samples_per_chord, len(audio) - pos)
        note = _render_note(
            root_freq, note_len, sample_rate, _sine,
            adsr_params={"attack_ms": 20, "decay_ms": 100, "sustain_level": 0.7, "release_ms": 80},
        )
        audio[pos:pos + note_len] += note
        pos += samples_per_chord
        chord_idx += 1

    return audio


def _render_chords(
    t_total: np.ndarray,
    sample_rate: int,
    chord_notes: list[list[int]],
    beat_duration: float,
    beats_per_chord: int,
    wave_func,
) -> np.ndarray:
    """Render chord pads."""
    audio = np.zeros(len(t_total), dtype=np.float64)
    samples_per_chord = int(beat_duration * beats_per_chord * sample_rate)
    chord_idx = 0
    pos = 0

    while pos < len(audio):
        chord = chord_notes[chord_idx % len(chord_notes)]
        note_len = min(samples_per_chord, len(audio) - pos)

        for midi_note in chord:
            freq = _midi_to_freq(midi_note)
            note = _render_note(
                freq, note_len, sample_rate, wave_func,
                adsr_params={"attack_ms": 80, "decay_ms": 150, "sustain_level": 0.5, "release_ms": 120},
            )
            audio[pos:pos + note_len] += note * (1.0 / len(chord))

        pos += samples_per_chord
        chord_idx += 1

    return audio


def _render_melody(
    t_total: np.ndarray,
    sample_rate: int,
    melody_notes: list[tuple[int, float]],
    beat_duration: float,
    wave_func,
    swing: float,
) -> np.ndarray:
    """Render lead melody from list of (midi_note, duration_in_beats)."""
    audio = np.zeros(len(t_total), dtype=np.float64)
    pos = 0
    is_even = True

    for midi_note, dur_beats in melody_notes:
        actual_dur = dur_beats * beat_duration
        if swing > 0 and not is_even:
            actual_dur *= (1.0 - swing * 0.5)

        note_samples = int(actual_dur * sample_rate)
        if pos + note_samples > len(audio):
            note_samples = len(audio) - pos
        if note_samples <= 0:
            break

        if midi_note > 0:  # 0 = rest
            freq = _midi_to_freq(midi_note)
            note = _render_note(
                freq, note_samples, sample_rate, wave_func,
                adsr_params={"attack_ms": 15, "decay_ms": 60, "sustain_level": 0.55, "release_ms": 50},
                vibrato_hz=4.5,
                vibrato_depth=0.02,
            )
            audio[pos:pos + note_samples] += note

        pos += note_samples
        is_even = not is_even

    return audio


# ---------------------------------------------------------------------------
# Melody generation
# ---------------------------------------------------------------------------

def _generate_melody_sequence(
    rng: np.random.Generator,
    scale: list[int],
    root_midi: int,
    duration_seconds: float,
    bpm: int,
) -> list[tuple[int, float]]:
    """Generate a sequence of (midi_note, duration_in_beats) tuples."""
    beat_duration = 60.0 / bpm
    total_beats = duration_seconds / beat_duration
    melody: list[tuple[int, float]] = []
    current_beat = 0.0

    # Build available notes across 2 octaves
    notes = []
    for octave_offset in [12, 24]:
        for interval in scale:
            notes.append(root_midi + octave_offset + interval)

    current_note_idx = rng.integers(0, len(notes) // 2)
    note_durations = [0.25, 0.5, 0.5, 1.0, 1.0, 1.0, 1.5, 2.0]

    while current_beat < total_beats:
        dur = float(rng.choice(note_durations))
        if current_beat + dur > total_beats:
            dur = total_beats - current_beat

        # Occasional rest (~15%)
        if rng.random() < 0.15:
            melody.append((0, dur))
        else:
            # Walk the scale: step by -2 to +2
            step = int(rng.integers(-2, 3))
            current_note_idx = max(0, min(len(notes) - 1, current_note_idx + step))
            melody.append((notes[current_note_idx], dur))

        current_beat += dur

    return melody


# ---------------------------------------------------------------------------
# Chord progression builder
# ---------------------------------------------------------------------------

def _build_chord_notes(
    rng: np.random.Generator,
    scale: list[int],
    root_midi: int,
    mode: str,
) -> list[list[int]]:
    """Build a 4-chord progression as lists of MIDI notes (triads)."""
    progs = PROGRESSIONS[mode]
    prog = progs[rng.integers(0, len(progs))]

    chord_notes = []
    for degree in prog:
        root = root_midi + scale[degree % len(scale)]
        # Build triad: root, 3rd (or approximation), 5th
        third_interval = scale[(degree + 2) % len(scale)] - scale[degree % len(scale)]
        if third_interval <= 0:
            third_interval += 12
        fifth_interval = scale[(degree + 4) % len(scale)] - scale[degree % len(scale)]
        if fifth_interval <= 0:
            fifth_interval += 12
        chord_notes.append([root, root + third_interval, root + fifth_interval])

    return chord_notes


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_procedural_music(
    prompt: str,
    duration_seconds: float,
    sample_rate: int = 32000,
) -> np.ndarray:
    """Generate procedural music from a text prompt.

    Returns a float32 numpy array of audio samples in [-1, 1] range.
    """
    seed = sum(ord(c) for c in prompt)
    rng = np.random.default_rng(seed)

    params = _parse_prompt(prompt, rng)
    scale = params["scale"]
    root_midi = params["root_midi"]
    bpm = params["bpm"]
    wave_func = WAVE_FUNCS[params["wave"]]

    beat_duration = 60.0 / bpm
    beats_per_chord = 4  # One chord per bar (4/4 time)

    n_samples = int(sample_rate * duration_seconds)
    t_total = np.arange(n_samples, dtype=np.float64) / sample_rate

    # Build musical structure
    chord_notes = _build_chord_notes(rng, scale, root_midi, params["mode"])
    melody_seq = _generate_melody_sequence(rng, scale, root_midi, duration_seconds, bpm)

    # Render layers
    bass = _render_bass(t_total, sample_rate, chord_notes, beat_duration, beats_per_chord, duration_seconds)
    chords = _render_chords(t_total, sample_rate, chord_notes, beat_duration, beats_per_chord, _triangle)
    lead = _render_melody(t_total, sample_rate, melody_seq, beat_duration, wave_func, params["swing"])

    # Mix layers
    audio = 0.30 * bass + 0.25 * chords + 0.35 * lead

    # Add subtle reverb-like effect (simple delay feedback)
    delay_samples = int(sample_rate * 0.15)
    if delay_samples < len(audio):
        reverb = np.zeros_like(audio)
        reverb[delay_samples:] += audio[:-delay_samples] * 0.2
        if 2 * delay_samples < len(audio):
            reverb[2 * delay_samples:] += audio[:-2 * delay_samples] * 0.1
        audio += reverb

    # Apply fade in/out
    fade_samples = int(0.05 * sample_rate)
    if len(audio) > 2 * fade_samples:
        audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
        audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.89  # -1 dBFS

    return audio.astype(np.float32)
