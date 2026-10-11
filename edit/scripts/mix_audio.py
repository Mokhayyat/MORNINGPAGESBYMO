"""Final audio mix: clean voice + original lo-fi bed (ducked under the voice) + timed sound effects.

Usage:
  python -I mix_audio.py <beats.json> <voice_clean.wav> <music.wav> <sfx_dir> <kenney_dir> <out.wav> [--from S --to S]

Levels: the master is normalised to -14 LUFS integrated with a true-peak ceiling of -1.5 dBTP
(4x-oversampled look-ahead limiter). Stems are written next to <out.wav> for checking.
"""
import glob
import json
import os
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import lfilter, resample_poly

SR = 48000


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def load(path, mono=False):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g, axis=0)
    if mono:
        return x.mean(1)
    return x if x.shape[1] == 2 else np.repeat(x[:, :1], 2, 1)


def db(v):
    return 10 ** (v / 20)


def envelope_db(x, attack=0.012, release=0.35):
    """Smoothed level follower (dBFS) of a mono signal."""
    rms = np.sqrt(uniform_filter1d(x ** 2, int(0.03 * SR)) + 1e-12)
    a_att, a_rel = np.exp(-1 / (attack * SR)), np.exp(-1 / (release * SR))
    # asymmetric one-pole: fast up, slow down (vectorised in two passes)
    up = lfilter([1 - a_att], [1, -a_att], rms)
    env = np.maximum(up, lfilter([1 - a_rel], [1, -a_rel], np.maximum(rms, up)))
    return 20 * np.log10(env + 1e-9)


def resolve_sfx(spec, sfx_dir, kenney_dir):
    kind, rest = spec.split(":", 1)
    if kind == "k":
        pack, name = rest.split("/", 1)
        hits = glob.glob(os.path.join(kenney_dir, pack, "**", name + ".ogg"), recursive=True)
        if not hits:
            raise FileNotFoundError(spec)
        return hits[0]
    parts = rest.split(":")
    return os.path.join(sfx_dir, "_".join(parts) + ".wav")


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


def main():
    beats_p, voice_p, music_p, sfx_dir, kenney_dir, out_p = sys.argv[1:7]
    beats = json.load(open(beats_p))
    dur = beats["meta"]["duration"]
    n = int(round(dur * SR))
    meter = pyln.Meter(SR)

    voice = load(voice_p, mono=True)[:n]
    voice = np.pad(voice, (0, n - len(voice)))
    voice *= db(-16.0 - meter.integrated_loudness(voice))             # voice stem at -16 LUFS

    music = load(music_p)[:n]
    music = np.pad(music, ((0, n - len(music)), (0, 0)))
    mcfg = beats["music"]
    music *= db(mcfg["level_lufs"] + 4 - meter.integrated_loudness(music))   # un-ducked bed ~ -21 LUFS
    venv = envelope_db(voice)
    duck = np.clip((venv + 46) / 14, 0, 1)                            # -46 dBFS -> no duck, -32 dBFS -> full duck
    music *= db(-mcfg["duck_db"] * duck)[:, None]

    sfx = np.zeros((n, 2))
    placed, missing = 0, []
    for e in beats["sfx"]:
        try:
            path = resolve_sfx(e["s"], sfx_dir, kenney_dir)
            clip = load(path)
        except (FileNotFoundError, RuntimeError, sf.LibsndfileError):
            missing.append(e["s"])
            continue
        clip = clip / (np.abs(clip).max() + 1e-9) * db(-6.0) * db(e["db"])
        i = int(round(e["t"] * SR))
        if i >= n:
            continue
        seg = clip[: n - i]
        sfx[i:i + len(seg)] += seg
        placed += 1

    mix = voice[:, None] * np.array([1.0, 1.0]) + music + sfx
    mix *= db(-14.0 - meter.integrated_loudness(mix))
    mix = true_peak_limit(mix, -1.5)
    mix *= db(-14.0 - meter.integrated_loudness(mix))                 # re-trim after limiting
    mix = true_peak_limit(mix, -1.5)

    t0, t1 = float(arg("--from", 0)), float(arg("--to", dur))
    a, b = int(t0 * SR), int(t1 * SR)
    base = os.path.splitext(out_p)[0]
    sf.write(out_p, mix[a:b].astype(np.float32), SR, subtype="FLOAT")
    for name, stem in (("voice", voice[:, None] * np.array([1.0, 1.0])), ("music", music), ("sfx", sfx)):
        sf.write(f"{base}_{name}.wav", stem[a:b].astype(np.float32), SR, subtype="FLOAT")
    tp = 20 * np.log10(np.abs(resample_poly(mix, 4, 1, axis=0)).max() + 1e-12)
    print(f"mix: {len(mix) / SR:.3f}s  {meter.integrated_loudness(mix):.2f} LUFS  true peak {tp:.2f} dBTP  "
          f"sfx placed {placed}/{len(beats['sfx'])}" + (f"  MISSING: {missing}" if missing else ""))


if __name__ == "__main__":
    main()
