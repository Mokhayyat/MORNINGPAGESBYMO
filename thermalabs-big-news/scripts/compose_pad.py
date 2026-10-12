"""A quiet, warm pad for one version, written in output time (original, generated from code).

Usage: python -I compose_pad.py <timeline.json> <version> <out.wav>

F# major (the pad under the STOP. and ENGINEER? reels sits on F#), 90 BPM, two bars per chord:
F#maj9 -> D#m7 -> Bmaj7(#11) -> C#sus4, landing back on F#maj9 when the frost starts. It fades in
after the hook's slam, opens up at the thank-you, gets a high shimmer for the frost and rings out
under the end card. Mixed well under the voice by mix_audio.py.
"""
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

sys.path.insert(0, os.path.dirname(__file__))
from edl import Version, load  # noqa: E402

SR = 48000


def hz(n):
    """MIDI note -> Hz."""
    return 440.0 * 2 ** ((n - 69) / 12)


# MIDI voicings
CHORDS = {
    "F#maj9": [54, 61, 65, 68, 70],      # F#3 C#4 E#4 G#4 A#4
    "D#m7": [51, 58, 61, 66],            # D#3 A#3 C#4 F#4
    "Bmaj7#11": [47, 54, 58, 63, 65],    # B2 F#3 A#3 D#4 E#4
    "C#sus4": [49, 56, 61, 66],          # C#3 G#3 C#4 F#4
}
ROOT = {"F#maj9": 42, "D#m7": 39, "Bmaj7#11": 35, "C#sus4": 37}


def pad_note(f, n, rng, bright):
    t = np.arange(n) / SR
    y = np.zeros(n)
    for det in (-0.0045, 0.0, 0.0052):                 # three slightly detuned layers (chorus)
        ph = rng.uniform(0, 2 * np.pi)
        vib = 0.0012 * np.sin(2 * np.pi * rng.uniform(0.15, 0.35) * t + rng.uniform(0, 6))
        fr = f * (1 + det + vib)
        phase = 2 * np.pi * np.cumsum(fr) / SR + ph
        for h in range(1, 9):
            if f * h > 7000:
                break
            amp = (1 / h) * (bright ** (h - 1))
            y += amp * np.sin(h * phase)
    return y / 3


def main(tl_path, name, out_path):
    tl = load(tl_path)
    v = Version(tl, name)
    n = int(round(v.duration * SR)) + int(0.05 * SR)
    rng = np.random.default_rng(90)
    t = np.arange(n) / SR
    bar = 60 / 90 * 4
    L = 2 * bar                                          # 5.33 s per chord
    t_in = 0.22                                          # after the slam
    t_thank = v.out(13.31)
    t_frost = v.out(tl["cues"]["frost"]["in"])
    t_end = v.src_len

    seq = ["F#maj9", "D#m7", "Bmaj7#11", "C#sus4"]
    events, s, i = [], t_in, 0
    while s < t_frost - 0.4:
        e = min(s + L, t_frost)
        events.append((seq[i % 4], s, e))
        s, i = e, i + 1
    events.append(("F#maj9", t_frost, v.duration + 0.05))

    out = np.zeros(n)
    for chord, s0, s1 in events:
        a, r = (1.4 if s0 <= t_in + 1e-6 else 0.5), 0.9
        i0, i1 = int(s0 * SR), min(n, int((s1 + r) * SR))
        m = i1 - i0
        tt = np.arange(m) / SR
        envl = np.minimum(1, tt / a) * np.clip(1 - (tt - (s1 - s0)) / r, 0, 1)
        bright = 0.42 if s0 < t_thank else 0.5
        y = sum(pad_note(hz(k), m, rng, bright) * (0.9 if j else 1.0) for j, k in enumerate(CHORDS[chord]))
        sub = np.sin(2 * np.pi * hz(ROOT[chord]) * tt) * 0.55
        out[i0:i1] += (y + sub) * envl

    # slow filter sweep: darker in the body, opens at the thank-you and in the frost
    cut = np.where(t < t_thank, 1100.0, 1700.0) + 600 * np.sin(2 * np.pi * 0.11 * t)
    cut = np.where(t > t_frost, cut + 1200 * np.clip((t - t_frost) / 0.8, 0, 1), cut)
    y = np.zeros(n)
    blk = 1024
    zi = None
    for k in range(0, n, blk):
        b, a = signal.butter(2, min(cut[k], 9000) / (SR / 2), "low")
        seg, zi = signal.lfilter(b, a, out[k:k + blk], zi=zi if zi is not None else signal.lfilter_zi(b, a) * 0)
        y[k:k + blk] = seg
    # gentle eighth-note pulse for momentum (90 BPM), off in the end card
    pulse = 1 - 0.12 * (0.5 + 0.5 * np.cos(2 * np.pi * t / (60 / 90 / 2)))
    pulse = np.where(t > t_end, 1.0, pulse)
    y *= pulse
    # frost shimmer: F#6 C#7 A#6 swelling in, then ringing out
    sh = np.zeros(n)
    for f in (hz(90), hz(97), hz(94), hz(102)):
        sh += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * (0.6 + 0.4 * np.sin(2 * np.pi * rng.uniform(3, 6) * t))
    sh *= np.clip((t - t_frost + 0.2) / 1.0, 0, 1) * 0.10
    y += sh
    # air
    air = signal.sosfilt(signal.butter(2, [3000, 9000], "band", fs=SR, output="sos"), rng.standard_normal(n)) * 0.012
    y += air
    # fade in after the hook, fade out at the very end
    y *= np.clip((t - t_in) / 1.2, 0, 1)
    y *= np.clip((v.duration - t) / 0.9, 0, 1)
    st = np.stack([y, np.roll(y, int(0.011 * SR)) * 0.96 + 0.04 * y], 1)   # a little width
    st /= np.abs(st).max() + 1e-9
    sf.write(out_path, (st * 0.5).astype(np.float32), SR, subtype="FLOAT")
    print(f"{name}: pad {n / SR:.2f}s, chords: " + ", ".join(f"{c}@{s0:.2f}" for c, s0, _ in events))


if __name__ == "__main__":
    main(*sys.argv[1:4])
