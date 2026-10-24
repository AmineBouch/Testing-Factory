"""Original royalty-free background music for the CV video (synthesised with numpy).

Calm electronic / ambient loop, 96 BPM, Am - F - C - G.
Pad alone during the intro, then bass, pluck arpeggio and a soft beat; fade out at the end.
Usage: python cv/make_music.py [seconds]  ->  cv/.music.wav
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 96
BEAT = 60 / BPM
BAR = 4 * BEAT
OUT = Path(__file__).resolve().parent / ".music.wav"

# Chords as MIDI notes (root position, mid register) and bass roots.
CHORDS = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]  # Am F C G
BASS = [45, 41, 36, 43]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lowpass(x, cutoff):
    """One-pole low-pass filter."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def env(n, attack, release):
    e = np.ones(max(n, 0))
    a, r = min(int(attack * SR), n), min(int(release * SR), n)
    if a > 0:
        e[:a] = np.linspace(0, 1, a)
    if r > 0:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def main():
    seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 32.0
    n = int(seconds * SR)
    t_all = np.arange(n) / SR
    pad = np.zeros(n); bass = np.zeros(n); pluck = np.zeros(n); drums = np.zeros(n)
    rng = np.random.default_rng(7)

    bars = int(np.ceil(seconds / BAR))
    for b in range(bars):
        start = int(b * BAR * SR)
        length = min(int(BAR * SR), n - start)
        if length <= 0:
            break
        t = np.arange(length) / SR
        chord = CHORDS[b % 4]
        # Pad: two slightly detuned saw-ish tones per note, soft attack
        p = np.zeros(length)
        for note in chord:
            for det in (-0.08, 0.08):
                f = hz(note + 12) * (1 + det / 100)
                p += 2 * ((t * f) % 1) - 1
        pad[start:start + length] += p * env(length, 0.6, 0.6) / 6

        # Bass: sine on beats 1 and 3 (from bar 2)
        if b >= 1:
            for beat in (0, 2):
                s = int(beat * BEAT * SR)
                ln = min(int(1.6 * BEAT * SR), length - s)
                if ln <= 0:
                    continue
                tt = np.arange(ln) / SR
                bass[start + s:start + s + ln] += (np.sin(2 * np.pi * hz(BASS[b % 4]) * tt)
                                                  * np.exp(-tt * 1.6) * env(ln, 0.01, 0.08))
        # Pluck arpeggio: 8th notes (from bar 2)
        if b >= 1:
            pattern = [chord[0], chord[1], chord[2], chord[1] + 12, chord[2], chord[1], chord[0] + 12, chord[2]]
            for k, note in enumerate(pattern):
                s = int(k * BEAT / 2 * SR)
                ln = min(int(0.5 * SR), length - s)
                if ln <= 0:
                    continue
                tt = np.arange(ln) / SR
                f = hz(note + 12)
                tri = 2 * np.abs(2 * ((tt * f) % 1) - 1) - 1
                pluck[start + s:start + s + ln] += tri * np.exp(-tt * 9) * env(ln, 0.003, 0.05)
        # Drums (from bar 2): soft kick on every beat, hi-hat on off-beats (from bar 3)
        if b >= 1:
            for beat in range(4):
                s = int(beat * BEAT * SR)
                ln = min(int(0.25 * SR), length - s)
                if ln <= 0:
                    continue
                tt = np.arange(ln) / SR
                kick = np.sin(2 * np.pi * (50 * tt + 60 * (1 - np.exp(-tt * 30)) / 30)) * np.exp(-tt * 14)
                drums[start + s:start + s + ln] += kick * 0.9
                if b >= 2:
                    h = int((beat + 0.5) * BEAT * SR)
                    hl = min(int(0.05 * SR), length - h)
                    if hl > 0:
                        noise = rng.standard_normal(hl)
                        noise = noise - lowpass(noise, 6000)  # keep the highs
                        drums[start + h:start + h + hl] += noise * np.exp(-np.arange(hl) / SR * 70) * 0.25

    pad = lowpass(pad, 1400)
    # Simple feedback delay on the pluck (dotted 8th)
    d = int(0.75 * BEAT * SR)
    wet = pluck.copy()
    for i in range(d, n):
        wet[i] += 0.35 * wet[i - d]
    pluck = lowpass(wet, 3500)

    mix = 0.55 * pad + 0.5 * bass + 0.22 * pluck + 0.35 * drums
    # Gentle stereo: pluck slightly wider via a short offset
    left = mix + 0.05 * np.roll(pluck, 300)
    right = mix + 0.05 * np.roll(pluck, -300)
    stereo = np.stack([left, right], axis=1)
    stereo *= env(n, 1.0, 2.5)[:, None]
    stereo /= np.max(np.abs(stereo)) + 1e-9
    stereo *= 0.89  # about -1 dBFS peak; the video mixes it lower
    data = (stereo * 32767).astype(np.int16)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(OUT, f"{seconds:.1f}s")


if __name__ == "__main__":
    main()
