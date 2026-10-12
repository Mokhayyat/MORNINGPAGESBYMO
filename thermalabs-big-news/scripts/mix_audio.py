"""Final audio for one version: the cleaned voice cut to the version's segments, the quiet pad ducked
under the voice, and the sound effects on their cues.

Usage: python -I mix_audio.py <timeline.json> <version> <voice_clean.wav> <pad.wav> <sfx_dir> <out.wav>

Levels match the earlier reels: master -14 LUFS integrated, true peak <= -1.5 dBTP (4x oversampled
look-ahead limiter). Stems are written next to <out.wav> for checking.
"""
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import lfilter, resample_poly

sys.path.insert(0, os.path.dirname(__file__))
from edl import Version, load  # noqa: E402

SR = 48000
XF = 0.008          # crossfade at every cut


def db(v):
    return 10 ** (v / 20)


def read(path):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g, axis=0)
    return x


def envelope_db(x, attack=0.012, release=0.35):
    rms = np.sqrt(uniform_filter1d(x ** 2, int(0.03 * SR)) + 1e-12)
    a_att, a_rel = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    up = lfilter([1 - a_att], [1, -a_att], rms)
    env = np.maximum(up, lfilter([1 - a_rel], [1, -a_rel], np.maximum(rms, up)))
    return 20 * np.log10(env + 1e-9)


def true_peak_limit(x, ceiling_db=-1.5):
    ceil = db(ceiling_db)
    up = resample_poly(x, 4, 1, axis=0)
    need = np.minimum(1.0, ceil / np.maximum(np.abs(up).max(1), 1e-9))
    need = need[: len(need) // 4 * 4].reshape(-1, 4).min(1)[: len(x)]
    look = int(0.005 * SR)
    g = uniform_filter1d(minimum_filter1d(need, 2 * look + 1), look)
    out = x.copy()
    out[: len(g)] *= g[:, None]
    return out


def cut_voice(v, voice):
    """Concatenate the kept segments with short equal-power crossfades; silence under the end card."""
    n = int(round(v.duration * SR))
    out = np.zeros(n)
    k = int(XF * SR)
    for (a, b), o in zip(v.segments, v.starts):
        i0, i1 = int(round(a * SR)), int(round(b * SR))
        seg = voice[i0:i1].copy()
        if len(seg) > 2 * k:
            ramp = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
            seg[:k] *= ramp
            seg[-k:] *= ramp[::-1]
        j = int(round(o * SR))
        m = min(len(seg), n - j)
        out[j:j + m] += seg[:m]
    return out


def main(tl_path, name, voice_p, pad_p, sfx_dir, out_p):
    tl = load(tl_path)
    v = Version(tl, name)
    n = int(round(v.duration * SR))
    meter = pyln.Meter(SR)

    voice = cut_voice(v, read(voice_p).mean(1))
    voice *= db(-16.0 - meter.integrated_loudness(voice))

    pad = read(pad_p)[:n]
    pad = np.pad(pad, ((0, n - len(pad)), (0, 0)))
    m = tl["music"]
    pad *= db(m["level_lufs"] - meter.integrated_loudness(pad))
    duck = np.clip((envelope_db(voice) + 46) / 14, 0, 1)
    pad *= db(-m["duck_db"] * duck)[:, None]

    sfx = np.zeros((n, 2))
    placed = 0
    for e in tl["sfx"]:
        t = v.cue_out(e)                      # a cue inside a removed gap snaps to the next kept moment
        clip = read(os.path.join(sfx_dir, e["s"] + ".wav"))
        clip = clip / (np.abs(clip).max() + 1e-9) * db(-6.0) * db(e["db"])
        i = int(round(t * SR))
        if 0 <= i < n:
            seg = clip[: n - i]
            sfx[i:i + len(seg)] += seg
            placed += 1

    mix = voice[:, None] * np.array([1.0, 1.0]) + pad + sfx
    mix *= db(-14.0 - meter.integrated_loudness(mix))
    mix = true_peak_limit(mix, -1.5)
    mix *= db(-14.0 - meter.integrated_loudness(mix))
    mix = true_peak_limit(mix, -1.5)

    base = os.path.splitext(out_p)[0]
    sf.write(out_p, mix.astype(np.float32), SR, subtype="FLOAT")
    for nm, stem in (("voice", voice[:, None] * np.array([1.0, 1.0])), ("pad", pad), ("sfx", sfx)):
        sf.write(f"{base}_{nm}.wav", stem.astype(np.float32), SR, subtype="FLOAT")
    tp = 20 * np.log10(np.abs(resample_poly(mix, 4, 1, axis=0)).max() + 1e-12)
    print(f"{name}: {n / SR:.2f}s  {meter.integrated_loudness(mix):.2f} LUFS  true peak {tp:.2f} dBTP  "
          f"pad {meter.integrated_loudness(pad):.1f} LUFS  sfx placed {placed}/{len(tl['sfx'])}")


if __name__ == "__main__":
    main(*sys.argv[1:7])
