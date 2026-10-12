"""Synthesise the reel's sound effects (clean UI sounds plus the icy ending), all from numpy/scipy so
nothing can draw a copyright claim.

Usage: python -I build_sfx.py <timeline.json> <outdir>

Writes <outdir>/<name>.wav for every name used in timeline.json "sfx": 48 kHz mono float32,
peak-normalised to -3 dBFS, starting at sample 0 so each sound lands exactly on its cue.
Every sound has a fixed seed, so renders are reproducible.
"""
import json
import os
import sys
import zlib

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000


def tax(d):
    return np.arange(int(round(d * SR))) / SR


def sos(kind, f, order=2):
    return signal.butter(order, f, kind, fs=SR, output="sos")


def filt(s, x):
    return signal.sosfilt(s, x)


def env(n, a, d, curve=4.0):
    """Attack a seconds (linear), then exponential-ish decay over the rest."""
    t = np.arange(n) / SR
    e = np.minimum(1.0, t / max(a, 1e-4))
    rest = np.clip((t - a) / max(d, 1e-4), 0, 1)
    return e * (1 - rest) ** curve


def sweep(f0, f1, n, shape=1.0):
    f = f0 + (f1 - f0) * (np.linspace(0, 1, n) ** shape)
    return 2 * np.pi * np.cumsum(f) / SR


def unit(x):
    return x / (np.abs(x).max() + 1e-9)


def finish(y, fade=0.015):
    y = np.asarray(y, float)
    nz = np.nonzero(np.abs(y) > 1e-4 * np.abs(y).max())[0]
    if len(nz):
        y = y[nz[0]:]
    k = min(len(y), int(fade * SR))
    if k:
        y[-k:] *= np.linspace(1, 0, k) ** 2
    y[: int(0.0005 * SR)] *= np.linspace(0, 1, int(0.0005 * SR))
    return unit(y) * 10 ** (-3 / 20)


def noise(rng, n):
    return rng.standard_normal(n)


def small_room(rng, x, rt=0.35, wet=0.15):
    n = int(rt * SR)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
    ir = filt(sos("lowpass", 6000), ir)
    wetsig = signal.fftconvolve(x, ir) * wet / np.abs(ir).sum() * 40
    out = np.zeros(len(wetsig))
    out[: len(x)] += x
    return out + wetsig


# ------------------------------------------------------------------ sounds
def slam(rng):
    t = tax(0.45)
    n = len(t)
    body = np.sin(sweep(150, 48, n, 0.35)) * env(n, 0.002, 0.30, 3)
    smack = filt(sos("bandpass", [900, 5200]), noise(rng, n)) * env(n, 0.001, 0.05, 2)
    pop = np.sin(sweep(1200, 380, n, 0.5)) * env(n, 0.001, 0.07, 3) * 0.5
    return small_room(rng, 1.0 * body + 0.8 * smack + pop, 0.4, 0.10)


def whoosh(rng, dur, lo, hi, peak=0.55):
    n = int(dur * SR)
    x = noise(rng, n)
    u = np.linspace(0, 1, n)
    fc = lo * (hi / lo) ** np.sin(np.pi * np.clip(u / peak / 2, 0, 0.5))
    out = np.zeros(n)
    blk = 256
    for i in range(0, n, blk):
        f = fc[i]
        s = sos("bandpass", [max(40, f * 0.6), min(20000, f * 1.6)])
        out[i:i + blk] = filt(s, x[max(0, i - 2048):i + blk])[-len(x[i:i + blk]):]
    shape = np.sin(np.pi * u) ** 1.6 * (1 - 0.4 * u)
    return out * shape


def whoosh_fast(rng):
    return whoosh(rng, 0.26, 350, 3400, 0.45)


def whoosh_soft(rng):
    return filt(sos("lowpass", 4000), whoosh(rng, 0.36, 220, 1500, 0.55))


def pop(rng, f0=950, f1=330, d=0.075):
    t = tax(d + 0.03)
    n = len(t)
    y = np.sin(sweep(f0, f1, n, 0.6)) * env(n, 0.001, d, 2.5)
    click = filt(sos("highpass", 2500), noise(rng, n)) * env(n, 0.0005, 0.004, 2) * 0.25
    return y + click


def pop_out(rng):
    return pop(rng, 700, 250, 0.08) * 0.8


def pop_hi(rng):
    return pop(rng, 1400, 520, 0.065)


def pop_hi2(rng):
    return pop(rng, 1750, 640, 0.06)


def pop_cute(rng):
    t = tax(0.2)
    n = len(t)
    a = np.sin(sweep(900, 420, n // 2, 0.5)) * env(n // 2, 0.001, 0.08, 2)
    b = np.sin(sweep(700, 1500, n - n // 2, 1.5)) * env(n - n // 2, 0.002, 0.09, 2) * 0.6
    return np.concatenate([a, b])


def ticks(rng):
    out = np.zeros(int(0.95 * SR))
    times = np.cumsum(np.linspace(0.12, 0.035, 14))
    times = times / times[-1] * 0.82
    for i, tt in enumerate(np.concatenate([[0], times[:-1]])):
        n = int(0.012 * SR)
        f = 3000 + 900 * i / 14
        k = np.sin(2 * np.pi * f * np.arange(n) / SR) * env(n, 0.0004, 0.010, 3)
        k += filt(sos("highpass", 3000), noise(rng, n)) * env(n, 0.0002, 0.003, 2) * 0.4
        j = int(tt * SR)
        out[j:j + n] += k * (0.6 + 0.4 * i / 14)
    return out


def blip_stuck(rng):
    n = int(0.07 * SR)
    a = np.sin(2 * np.pi * 1046.5 * np.arange(n) / SR) * env(n, 0.002, 0.06, 2)
    b = np.sin(2 * np.pi * 932.3 * np.arange(n) / SR) * env(n, 0.002, 0.06, 2)
    gap = np.zeros(int(0.05 * SR))
    return np.concatenate([a, gap, b, np.zeros(int(0.05 * SR))])


def badge_clip(rng):
    n = int(0.5 * SR)
    t = np.arange(n) / SR
    clink = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / d) for f, a, d in
                ((2150, 1.0, 0.06), (3420, 0.6, 0.04), (5230, 0.35, 0.025), (7400, 0.2, 0.015)))
    clink = np.concatenate([np.zeros(int(0.10 * SR)), clink])[:n]
    sw = np.pad(filt(sos("lowpass", 3000), whoosh(rng, 0.14, 300, 1800, 0.5)), (0, n))[:n] * 0.6
    return clink * 0.7 + sw


def stamp(rng):
    t = tax(0.4)
    n = len(t)
    thud = np.sin(sweep(110, 52, n, 0.4)) * env(n, 0.001, 0.22, 3)
    slap = filt(sos("bandpass", [400, 3000]), noise(rng, n)) * env(n, 0.0005, 0.035, 2)
    return small_room(rng, thud + 0.7 * slap, 0.3, 0.08)


def holo(rng):
    n = int(0.9 * SR)
    out = np.zeros(n)
    notes = [1046.5, 1318.5, 1568.0, 2093.0, 2637.0, 3136.0]
    for i, f in enumerate(notes):
        j = int(i * 0.055 * SR)
        m = n - j
        tt = np.arange(m) / SR
        out[j:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.18) * (0.8 - 0.08 * i)
    air = filt(sos("bandpass", [4000, 11000]), noise(rng, n)) * np.sin(np.pi * np.linspace(0, 1, n)) * 0.15
    return out * 0.5 + air


def tap(rng):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    click = filt(sos("highpass", 2000), noise(rng, n)) * env(n, 0.0002, 0.003, 2)
    tock = np.sin(2 * np.pi * 620 * t) * env(n, 0.001, 0.03, 3) * 0.7
    return click * 0.8 + tock


def ding(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    y = (np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t / 0.25) + 0.55 * np.sin(2 * np.pi * 1975.5 * t) * np.exp(-t / 0.18)
         + 0.2 * np.sin(2 * np.pi * 3951 * t) * np.exp(-t / 0.08))
    return y * np.minimum(1, t / 0.003)


def shutter(rng, f=1.0):
    n = int(0.22 * SR)
    out = np.zeros(n)
    for j, (dl, g) in enumerate(((0.0, 1.0), (0.045, 0.75))):
        m = int(0.03 * SR)
        nb = filt(sos("bandpass", [1800 * f, 6500 * f]), noise(rng, m)) * env(m, 0.0003, 0.02, 3)
        ring = np.sin(2 * np.pi * (2700 + 500 * j) * f * np.arange(m) / SR) * env(m, 0.0005, 0.015, 3) * 0.4
        k = int(dl * SR)
        out[k:k + m] += (nb + ring) * g
    thump = np.sin(2 * np.pi * 140 * np.arange(n) / SR) * env(n, 0.001, 0.05, 3) * 0.35
    return out + thump


def shutter2(rng):
    return shutter(rng, 1.12)


def ring(rng):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    whoom = np.sin(sweep(95, 50, n, 0.5)) * env(n, 0.01, 0.45, 2.5)
    ping = (np.sin(2 * np.pi * 1600 * t) + 0.6 * np.sin(2 * np.pi * 2410 * t)) * np.exp(-t / 0.16) * 0.35
    air = filt(sos("highpass", 5000), noise(rng, n)) * env(n, 0.005, 0.2, 2) * 0.08
    return whoom + ping + air


def frost(rng):
    d = 1.5
    n = int(d * SR)
    u = np.linspace(0, 1, n)
    out = np.zeros(n)
    # crackles getting denser
    k = 0
    while k < n:
        dens = 18 + 140 * u[k] ** 1.5
        k += int(SR / dens * rng.uniform(0.3, 1.7))
        if k >= n:
            break
        m = int(rng.uniform(0.002, 0.006) * SR)
        c = filt(sos("bandpass", [rng.uniform(2500, 4500), rng.uniform(7000, 12000)]), noise(rng, m)) * env(m, 0.0002, m / SR, 2)
        out[k:k + m] += c[: len(out[k:k + m])] * rng.uniform(0.2, 1.0) * (0.3 + 0.7 * u[k])
    rise = whoosh(rng, d, 1500, 9000, 0.98) * 0.35
    shimmer_t = np.arange(n) / SR
    glass = sum(np.sin(2 * np.pi * f * shimmer_t + rng.uniform(0, 6)) for f in (2637, 3520, 4186)) * u ** 2 * 0.05
    return out + rise + glass


def crack(rng):
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    snap = filt(sos("highpass", 1200), noise(rng, n)) * env(n, 0.0002, 0.012, 3) * 1.4
    crackle = np.zeros(n)
    k = int(0.004 * SR)
    while k < int(0.3 * SR):
        k += int(rng.uniform(0.004, 0.02) * SR)
        m = int(0.003 * SR)
        crackle[k:k + m] += filt(sos("bandpass", [3000, 11000]), noise(rng, m)) * rng.uniform(0.2, 0.8) * (1 - k / (0.32 * SR))
    body = np.sin(sweep(160, 70, n, 0.5)) * env(n, 0.001, 0.2, 3) * 0.7
    ringing = sum(a * np.sin(2 * np.pi * f * t) * np.exp(-t / dd) for f, a, dd in
                  ((3150, 0.4, 0.12), (4470, 0.3, 0.09), (6230, 0.2, 0.06)))
    return small_room(rng, snap + crackle + body + ringing, 0.6, 0.12)


def end_hit(rng):
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    sub = np.sin(sweep(70, 42, n, 0.4)) * env(n, 0.01, 0.9, 2.5) * 0.9
    sw = np.pad(whoosh(rng, 0.3, 300, 2500, 0.8), (0, n))[:n] * 0.4
    notes = (1479.98, 1864.66, 2217.46, 2793.83)          # F#6 A#6 C#7 F7 (F# major sparkle)
    sp = np.zeros(n)
    for i, f in enumerate(notes):
        j = int((0.05 + i * 0.07) * SR)
        tt = np.arange(n - j) / SR
        sp[j:] += np.sin(2 * np.pi * f * tt) * np.exp(-tt / 0.5) * 0.18
    return sub + sw + sp


SOUNDS = {name: fn for name, fn in globals().items() if callable(fn) and name in {
    "slam", "whoosh_fast", "whoosh_soft", "pop", "pop_out", "pop_hi", "pop_hi2", "pop_cute", "ticks", "blip_stuck",
    "badge_clip", "stamp", "holo", "tap", "ding", "shutter", "shutter2", "ring", "frost", "crack", "end_hit"}}


def main(tl_path, outdir):
    tl = json.load(open(tl_path))
    os.makedirs(outdir, exist_ok=True)
    names = sorted({e["s"] for e in tl["sfx"]})
    for name in names:
        rng = np.random.default_rng(zlib.crc32(name.encode()))
        y = finish(SOUNDS[name](rng))
        sf.write(os.path.join(outdir, f"{name}.wav"), y.astype(np.float32), SR, subtype="FLOAT")
        print(f"{name:12s} {len(y) / SR:5.2f}s")


if __name__ == "__main__":
    main(*sys.argv[1:3])
