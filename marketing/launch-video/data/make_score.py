"""Synthesise a 60 s ambient score timed to the launch video's beats.

Warm detuned pad (chord changes at each act), soft bell hits on every cut,
a gentle pulse under the Digest beat. Royalty-free by construction.
Run: python3 marketing/launch-video/data/make_score.py
"""

import wave
from pathlib import Path

import numpy as np

SR = 44100
FPS = 30
TOTAL = 1800 / FPS
OUT = Path(__file__).resolve().parents[1] / "remotion" / "public" / "score.wav"

CUTS = [0, 150, 270, 420, 810, 900, 1020, 1380, 1590]  # frames, mirrors BEATS in Launch.tsx

# (start_frame, chord as MIDI notes): D major -> B minor -> G major -> A -> D
# Changes at the reveal, the Brief, the bridge, the Digest and the loop.
CHORDS = [
    (0, [50, 57, 62, 66, 69]),
    (270, [47, 54, 59, 62, 66]),
    (810, [43, 50, 55, 59, 62]),
    (1020, [45, 52, 57, 61, 64]),
    (1380, [50, 57, 62, 66, 69, 74]),
]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def pad(t: np.ndarray) -> np.ndarray:
    out = np.zeros((len(t), 2))
    edges = [c[0] / FPS for c in CHORDS] + [TOTAL]
    for (start, notes), s, e in zip(CHORDS, edges, edges[1:]):
        xf = 1.5  # crossfade seconds
        env = np.clip((t - (s - xf)) / xf, 0, 1) * np.clip(((e + xf) - t) / xf, 0, 1)
        if not env.any():
            continue
        for n in notes:
            f = hz(n)
            for side, detune in ((0, -0.12), (1, 0.12)):
                ph = 2 * np.pi * f * (1 + detune / 100) * t
                tone = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.12 * np.sin(3 * ph)
                out[:, side] += tone * env / len(notes)
    # Slow breathing amplitude.
    out *= (0.75 + 0.25 * np.sin(2 * np.pi * t / 7.5))[:, None]
    return out * 0.22


def bell(t: np.ndarray, at: float, midi: float, gain: float) -> np.ndarray:
    dt = t - at
    on = dt >= 0
    env = np.where(on, np.exp(-np.maximum(dt, 0) * 2.2), 0)
    f = hz(midi)
    tone = np.sin(2 * np.pi * f * dt) + 0.4 * np.sin(2 * np.pi * f * 2.76 * dt) * np.exp(-np.maximum(dt, 0) * 5)
    return (tone * env * gain)[:, None] * np.array([[0.9, 1.0]])


def pulse(t: np.ndarray) -> np.ndarray:
    """Soft heartbeat under the Digest beats (frames 900-1380), 96 bpm."""
    s, e = 900 / FPS, 1380 / FPS
    period = 60 / 96
    ph = np.mod(t - s, period)
    env = np.exp(-ph * 14) * ((t >= s) & (t < e))
    env *= np.clip((t - s) / 2, 0, 1) * np.clip((e - t) / 2, 0, 1)
    return (np.sin(2 * np.pi * 55 * t) * env * 0.35)[:, None] * np.array([[1.0, 1.0]])


def main() -> None:
    t = np.arange(int(TOTAL * SR)) / SR
    mix = pad(t) + pulse(t)
    notes = [74, 78, 81, 78, 83, 81, 86, 85, 86]
    for frame, note in zip(CUTS, notes):
        mix += bell(t, frame / FPS, note, 0.10)
    # Final resolve: an extra low bell when the logo lands.
    mix += bell(t, 1630 / FPS, 62, 0.14)
    # Fade in/out and normalise.
    fade = np.clip(t / 1.5, 0, 1) * np.clip((TOTAL - t) / 2.5, 0, 1)
    mix *= fade[:, None]
    mix /= np.max(np.abs(mix)) / 0.8
    pcm = (mix * 32767).astype(np.int16)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("wrote", OUT, f"{TOTAL:.0f}s")


if __name__ == "__main__":
    main()
