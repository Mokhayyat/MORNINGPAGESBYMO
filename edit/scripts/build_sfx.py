"""Synthesize the original sound effects referenced as "synth:<name>[:args]" in beats.json.

Usage:
  python -I build_sfx.py <beats.json> <outdir>

For every distinct synth:<name>[:args] in beats.json "sfx", writes
<outdir>/<name>[_<args joined by _>].wav -- 48 kHz mono float32, peak-normalized
to -3 dBFS, starting at sample 0 (each file is placed at an exact timestamp),
ending with a short fade. Everything is generated with numpy/scipy (no samples),
so nothing can draw a copyright claim; each sound has its own fixed seed, so
renders are reproducible. "k:..." entries (Kenney CC0 files) are handled elsewhere.

Sounds aim for soft, friendly, cartoon-cozy rather than harsh:
  scribble, scribble_long   pencil strokes: 2-5 kHz noise shaped by random strokes
  slap                      sticky-note slap: transient + ~150 Hz body + paper rustle
  whoosh                    band-passed noise, centre sweeps up then down
  swell_down / swell_up     reverse-swell into a memory (darker, pitch sinks) /
                            warm rising swell (brighter, pitch settles up)
  typewriter                7 slightly irregular key clacks, no bell
  crumple, rip, rip2        paper crumple / tears (dense band-passed crackle)
  snap, thud, ball, splat   small impacts
  chime, shimmer            glockenspiel C6-E6-G6 / ascending sparkle of tiny bells
  pop, pop_hi, pop_hi2,     cartoon pops (fast downward sine sweeps); pop_cute adds an
  pop_cute                  upward chirp at the end
  waves                     gentle ocean swell
  type_boops:<n>:<dur>      n cute pentatonic typing blips spread over dur seconds
  boop_up / boop_down       two-note rising / falling boops
  whistle                   referee pea-whistle, two short blasts
"""
import json
import os
import sys
import zlib

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
SEED = 1492
PEAK_DB = -3.0

# Note frequencies used by the tonal sounds
G5, A5, C6, D6, E6, G6, A6 = 783.99, 880.00, 1046.50, 1174.66, 1318.51, 1567.98, 1760.00
E5, C7, D7, E7 = 659.26, 2093.00, 2349.32, 2637.02
PENTATONIC = (E5, G5, A5, C6, D6)


# ----------------------------------------------------------------------------- helpers

def taxis(dur):
    return np.arange(int(round(dur * SR))) / SR


def bp(lo, hi, order=2):
    return signal.butter(order, [lo, hi], "band", fs=SR, output="sos")


def lp(fc, order=2):
    return signal.butter(order, fc, "low", fs=SR, output="sos")


def hp(fc, order=2):
    return signal.butter(order, fc, "high", fs=SR, output="sos")


def filt(sos, x):
    return signal.sosfilt(sos, x)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def ramp(n):
    """Raised-cosine 0 -> 1 over n samples."""
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / max(n, 1))


def phase(f):
    """Phase of an oscillator whose frequency follows the array f (Hz)."""
    return 2.0 * np.pi * np.cumsum(f) / SR


def unit(x):
    return x / (np.max(np.abs(x)) + 1e-12)


def place(buf, sig, t):
    i = int(round(t * SR))
    j = min(len(buf), i + len(sig))
    if j > i:
        buf[i:j] += sig[:j - i]


def biquad(kind, fc, q):
    w0 = 2 * np.pi * np.clip(fc, 20.0, 0.45 * SR) / SR
    cw, alpha = np.cos(w0), np.sin(w0) / (2 * q)
    if kind == "low":
        b = np.array([(1 - cw) / 2, 1 - cw, (1 - cw) / 2])
    elif kind == "high":
        b = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2])
    else:                                   # band-pass, 0 dB at the centre
        b = np.array([alpha, 0.0, -alpha])
    a = np.array([1 + alpha, -2 * cw, 1 - alpha])
    return b / a[0], a / a[0]


def tv_filter(x, kind, fc, q, block=32):
    """Biquad with a per-sample cutoff curve (coefficients updated every `block` samples)."""
    fc = np.broadcast_to(np.asarray(fc, dtype=float), x.shape)
    y = np.empty_like(x)
    zi = np.zeros(2)
    for s in range(0, len(x), block):
        b, a = biquad(kind, fc[min(s + block // 2, len(x) - 1)], q)
        y[s:s + block], zi = signal.lfilter(b, a, x[s:s + block], zi=zi)
    return y


def bell(f, length, rng, partials=((1.0, 1.0, 0.9), (2.76, 0.30, 0.20), (5.40, 0.10, 0.07), (8.93, 0.04, 0.035)),
         shimmer=0.3):
    """Glockenspiel / music-box bell: inharmonic partials with fast upper decays."""
    t = taxis(length)
    scale = (f / C6) ** -0.3
    y = np.zeros(len(t))
    for ratio, amp, tau in partials:
        if f * ratio < 0.45 * SR:
            y += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / (tau * scale))
    y += shimmer * np.sin(2 * np.pi * f * 1.0016 * t) * np.exp(-t / (partials[0][2] * scale))
    k = int(0.003 * SR)
    y[:k] += 0.1 * filt(hp(3000), rng.standard_normal(k)) * np.exp(-np.arange(k) / (0.0006 * SR))
    y[:48] *= ramp(48)
    return y


def room(x, rng, rt60=0.7, wet=0.18):
    """A touch of small-room reverb (synthetic decaying-noise impulse response)."""
    t = taxis(rt60 * 1.2)
    ir = filt(lp(4500), rng.standard_normal(len(t))) * np.exp(-6.91 * t / rt60)
    ir[:int(0.004 * SR)] *= ramp(int(0.004 * SR))
    ir = np.concatenate([np.zeros(int(0.008 * SR)), ir])
    ir /= np.sqrt(np.sum(ir ** 2))
    return x + wet * signal.fftconvolve(x, ir)[:len(x)]


def finish(y, fade=0.02):
    """Start at sample 0 (trim any lead-in, 0.5 ms anti-click ramp), fade the tail out,
    peak-normalize to PEAK_DB, float32."""
    y = np.asarray(y, dtype=float)
    first = int(np.argmax(np.abs(y) > 1e-3 * np.max(np.abs(y))))
    y = y[first:].copy()
    y[:24] *= ramp(24)
    k = max(int(min(fade, 0.25 * len(y) / SR) * SR), 1)
    y[-k:] *= ramp(k)[::-1]
    y *= 10 ** (PEAK_DB / 20) / (np.max(np.abs(y)) + 1e-12)
    return y.astype(np.float32)


# ----------------------------------------------------------------------------- sounds

def scribble(rng, dur=0.5, strokes=(4, 6)):
    """Pencil scribble: 2-5 kHz noise, amplitude-shaped by random back-and-forth strokes."""
    t = taxis(dur)
    n = len(t)
    k = int(rng.integers(strokes[0], strokes[1] + 1))
    edges = np.concatenate([[0.0], np.cumsum(rng.uniform(0.75, 1.25, k))])
    edges = (edges / edges[-1] * n).astype(int)
    env, tilt = np.zeros(n), np.zeros(n)
    for i in range(k):
        a, b = edges[i], edges[i + 1]
        x = np.arange(b - a) / (b - a)
        att = 0.04 if i == 0 else rng.uniform(0.10, 0.18)   # the first stroke starts at once
        shape = smoothstep(x / att) * (1.0 - smoothstep((x - 0.70) / 0.30))
        if i:
            shape = np.maximum(shape, 0.08)                 # turning points dip, never stop
        pressure = 1.0 + 0.2 * np.sin(2 * np.pi * x * rng.uniform(1.0, 3.0) + rng.uniform(0, 6.3))
        env[a:b] = shape * pressure * rng.uniform(0.6, 1.0)
        tilt[a:b] = rng.uniform(0.0, 1.0)
    tilt = np.convolve(tilt, np.ones(240) / 240, mode="same")
    w = rng.standard_normal(n)
    tone = filt(bp(1800, 3500), w) * (1 - tilt) + filt(bp(3000, 5200), w) * tilt
    grain = np.abs(filt(lp(260), rng.standard_normal(n)))
    grain = 0.45 + 0.55 * grain / grain.max()               # paper tooth
    return filt(lp(8000), tone * env * grain)


def scribble_long(rng):
    return scribble(rng, dur=1.0, strokes=(8, 11))


def slap(rng):
    """Sticker / sticky-note slap: sharp transient + short ~150 Hz body + paper rustle."""
    t = taxis(0.32)
    n = len(t)
    crack = 0.8 * filt(hp(1200), rng.standard_normal(n)) * np.exp(-t / 0.0012)
    thwap = 1.6 * filt(lp(1600), rng.standard_normal(n)) * np.exp(-t / 0.016)
    body = 0.9 * np.sin(phase(140 + 50 * np.exp(-t / 0.010))) * np.exp(-t / 0.05)
    renv = 0.12 * np.exp(-t / 0.08)
    for _ in range(3):
        t0, amp, tau = rng.uniform(0.01, 0.12), rng.uniform(0.15, 0.3), rng.uniform(0.015, 0.04)
        tt = t - t0
        renv += amp * smoothstep(tt / 0.002) * np.exp(-np.clip(tt, 0, None) / tau)
    rustle = filt(bp(2500, 6500), rng.standard_normal(n)) * renv
    return filt(lp(9500), crack + thwap + body + rustle)


def whoosh(rng, dur=0.4):
    """Band-passed noise whose centre sweeps up then down; swells in and out."""
    t = taxis(dur)
    x = t / dur
    up = smoothstep(x / 0.45)
    down = smoothstep((x - 0.45) / 0.55)
    fc = np.exp(np.log(450) + (np.log(2600) - np.log(450)) * up - (np.log(2600) - np.log(700)) * down)
    y = tv_filter(rng.standard_normal(len(t)), "band", fc, 1.4)
    y += 0.35 * tv_filter(rng.standard_normal(len(t)), "band", fc * 1.9, 2.0)
    env = np.where(x < 0.45, 0.12 + 0.88 * up, 1.0 - down) ** 1.2
    return y * env


def _pad(t, notes, bend, harmonics, detune_cents, rng):
    y = np.zeros(len(t))
    for f in notes:
        for d in (-detune_cents, detune_cents):
            ph = phase(f * bend * 2 ** (d / 1200)) + rng.uniform(0, 2 * np.pi)
            y += sum(a * np.sin(h * ph) for h, a in harmonics)
    return y


def swell_down(rng, dur=0.6):
    """Soft reverse-swell into a memory: a Dm(add9) pad swells up while the tone darkens
    (low-pass 5.5 kHz -> 550 Hz) and the pitch sinks about a semitone, like tape slowing."""
    t = taxis(dur)
    x = t / dur
    bend = 2 ** (-1.0 * x ** 1.5 / 12)
    pad = _pad(t, (293.66, 440.0, 659.26, 880.0), bend, ((1, 1.0), (2, 0.35), (3, 0.12)), 5, rng)
    fc = np.exp(np.log(5500) + (np.log(550) - np.log(5500)) * x)
    pad = tv_filter(pad, "low", fc, 0.9)
    air = 0.25 * unit(tv_filter(rng.standard_normal(len(t)), "low", fc * 0.8, 0.7)) * np.max(np.abs(pad))
    env = np.where(x < 0.78, 0.22 + 0.78 * (x / 0.78) ** 2.2, 0.5 + 0.5 * np.cos(np.pi * np.clip((x - 0.78) / 0.22, 0, 1)))
    return (0.8 * pad + air) * env


def swell_up(rng, dur=1.0):
    """Warm rising swell: an open D pad brightens (450 Hz -> 4.8 kHz) and slides up into tune."""
    t = taxis(dur)
    x = t / dur
    bend = 2 ** (-0.6 * (1 - smoothstep(x / 0.7)) / 12)
    harm = tuple((h, 1.0 / h ** 1.4) for h in range(1, 7))
    pad = _pad(t, (146.83, 220.0, 329.63, 440.0, 587.33), bend, harm, 6, rng)
    fc = np.exp(np.interp(x, [0.0, 0.75, 1.0], np.log([450.0, 4800.0, 3500.0])))
    pad = tv_filter(pad, "low", fc, 0.8)
    air = 0.12 * unit(tv_filter(rng.standard_normal(len(t)), "band", fc * 1.2, 0.9)) * np.max(np.abs(pad))
    sub = 0.15 * np.max(np.abs(pad)) * np.sin(2 * np.pi * 73.42 * t)
    env = np.where(x < 0.7, 0.12 + 0.88 * smoothstep(x / 0.7) ** 1.3, 1.0 - smoothstep((x - 0.7) / 0.3))
    return (pad + air + sub) * env


def typewriter(rng, keys=7):
    """Typewriter: 7 slightly irregular key clacks (click + type-bar ring + platen thump)."""
    gaps = rng.uniform(0.062, 0.095, keys - 1)
    gaps[rng.integers(0, keys - 1)] *= 1.4
    onsets = np.concatenate([[0.0], np.cumsum(gaps)])
    y = np.zeros(int((onsets[-1] + 0.1) * SR))
    tk = taxis(0.07)
    for t0 in onsets:
        f1 = rng.uniform(1100, 1450)
        click = filt(bp(1800, 6000), rng.standard_normal(len(tk))) * np.exp(-tk / 0.0007)
        ring = (0.55 * np.sin(2 * np.pi * f1 * tk + rng.uniform(0, 6.3)) * np.exp(-tk / 0.009)
                + 0.35 * np.sin(2 * np.pi * f1 * rng.uniform(1.85, 2.05) * tk) * np.exp(-tk / 0.006)
                + 0.18 * np.sin(2 * np.pi * f1 * rng.uniform(2.9, 3.3) * tk) * np.exp(-tk / 0.004))
        thump = 0.5 * np.sin(2 * np.pi * rng.uniform(160, 210) * tk) * np.exp(-tk / 0.014)
        key = rng.uniform(0.7, 1.0) * (0.9 * click + ring + thump)
        key[:12] *= ramp(12)
        place(y, key, t0)
    return filt(lp(8500), y)


def crumple(rng, dur=0.55):
    """Paper crumple: dense random crackles band-passed 1.5-7 kHz, in 4 squeezing gestures."""
    t = taxis(dur)
    n = len(t)
    density = np.zeros(n)
    for i, s0 in enumerate([0.0] + sorted(rng.uniform(0.08, 0.36, 3))):
        tt = t - s0
        rise = 0.004 if i == 0 else rng.uniform(0.01, 0.03)
        density += rng.uniform(0.5, 1.0) * smoothstep(tt / rise) * np.exp(-np.clip(tt - rise, 0, None) / rng.uniform(0.05, 0.12))
    density *= 1.0 - smoothstep((t - (dur - 0.08)) / 0.08)
    hits = rng.random(n) < 2200 * density / SR
    imp = np.where(hits, (0.15 + 0.3 * rng.pareto(3.0, n)) * rng.choice([-1.0, 1.0], n), 0.0)
    band = rng.integers(0, 3, n)
    y = np.zeros(n)
    for i, (lo, hi, g) in enumerate([(1500, 3000, 1.0), (2500, 5000, 0.8), (4000, 7000, 0.6)]):
        y += g * filt(bp(lo, hi), imp * (band == i))
    am = np.abs(filt(lp(120), rng.standard_normal(n)))
    rustle = filt(bp(1500, 7000), rng.standard_normal(n)) * density * (0.3 + 0.7 * am / am.max())
    body = filt(bp(400, 1400), rng.standard_normal(n)) * density
    return y + 0.06 * rustle + 0.03 * body


def snap(rng):
    """Twig / paper snap: sharp click and crack, a second micro-click, a tiny low thump."""
    t = taxis(0.12)
    n = len(t)
    click = filt(hp(2000), rng.standard_normal(n)) * np.exp(-t / 0.0005)
    crack = 0.6 * np.sin(2 * np.pi * 3100 * t) * np.exp(-t / 0.0028) + 0.35 * np.sin(2 * np.pi * 5200 * t + 1) * np.exp(-t / 0.0016)
    tt = t - 0.009
    second = 0.55 * filt(hp(2000), rng.standard_normal(n)) * (tt >= 0) * np.exp(-np.clip(tt, 0, None) / 0.0004)
    thump = 0.55 * np.sin(phase(105 + 45 * np.exp(-t / 0.015))) * np.exp(-t / 0.022)
    return filt(lp(9000), click + crack + second + thump)


def chime(rng):
    """Cozy glockenspiel chime: C6-E6-G6 rolled quickly, ~1 s ring, a little room."""
    y = np.zeros(int(1.3 * SR))
    for t0, f, v in [(0.0, C6, 0.85), (0.085, E6, 0.80), (0.17, G6, 0.92)]:
        place(y, v * bell(f, 1.3 - t0, rng), t0)
    y = room(y, rng, rt60=0.7, wet=0.18)
    y[-int(0.15 * SR):] *= ramp(int(0.15 * SR))[::-1]
    return y


def pop(rng, f_hi=900.0, f_lo=350.0, dur=0.07, click=0.22, harm=0.18):
    """Bubbly cartoon pop: sine blip with a fast downward sweep, plus a small click."""
    t = taxis(dur + 0.025)
    f = f_lo + (f_hi - f_lo) * np.exp(-t / (dur / 3.2))
    ph = phase(f)
    env = (1 - np.exp(-t / 0.0007)) * np.exp(-t / (dur / 3.0))
    y = (np.sin(ph) + harm * np.sin(2 * ph)) * env
    if click:
        k = int(0.003 * SR)
        y[:k] += click * filt(hp(1800), rng.standard_normal(k)) * np.exp(-np.arange(k) / (0.0006 * SR))
    return y


def pop_hi(rng):
    return pop(rng, 1400.0, 600.0, 0.06)


def pop_hi2(rng):
    return pop(rng, 1650.0, 700.0, 0.058)


def pop_cute(rng):
    """Rounder, cuter pop (no click) that ends with a tiny upward chirp."""
    y = np.zeros(int(0.14 * SR))
    place(y, pop(rng, 820.0, 430.0, 0.06, click=0.0, harm=0.1), 0.0)
    tc = taxis(0.045)
    chirp = 0.45 * np.sin(phase(600 + 550 * smoothstep(tc / 0.04))) * np.sin(np.pi * np.clip(tc / 0.045, 0, 1)) ** 1.5
    place(y, chirp, 0.052)
    return y


def waves(rng, dur=1.4):
    """Gentle ocean swell: low-passed (pink) noise whose level and brightness crest and fall."""
    t = taxis(dur)
    n = len(t)
    x = t / dur
    spec = np.fft.rfft(rng.standard_normal(n))
    fr = np.fft.rfftfreq(n, 1 / SR)
    pink = np.fft.irfft(spec / np.sqrt(np.maximum(fr, 20.0)), n)
    pink = unit(pink)
    crest = np.sin(np.pi * x ** 0.8) ** 1.5
    y = tv_filter(pink, "low", 350 + 2200 * crest, 0.7)
    foam = 0.10 * unit(filt(hp(2500), rng.standard_normal(n))) * crest ** 3 * np.max(np.abs(y))
    env = (0.15 + 0.85 * crest) * (1.0 - smoothstep((x - 0.8) / 0.2))
    return (y + foam) * env


def thud(rng):
    """Soft low thud (~70 Hz) for a wax-seal stamp, with a little 2nd harmonic for phones."""
    t = taxis(0.25)
    f = 62 + 33 * np.exp(-t / 0.018)
    body = np.sin(phase(f)) * np.exp(-t / 0.065)
    over = 0.22 * np.sin(phase(2 * f)) * np.exp(-t / 0.03)
    tex = 0.6 * filt(lp(380), rng.standard_normal(len(t))) * np.exp(-t / 0.010)
    y = np.tanh(1.4 * (body + over + tex))
    y[:48] *= ramp(48)
    return y


def shimmer(rng):
    """Ascending sparkle of tiny bells (C major pentatonic C6 -> E7) with a breath of air."""
    notes = (C6, D6, E6, G6, A6, C7, D7, E7)
    y = np.zeros(int(0.75 * SR))
    tiny = ((1.0, 1.0, 0.28), (2.76, 0.25, 0.07), (5.40, 0.08, 0.03))
    for i, f in enumerate(notes):
        t0 = 0.052 * i
        place(y, (0.55 + 0.05 * i) * bell(f, 0.75 - t0, rng, tiny, shimmer=0.15), t0)
    t = taxis(0.75)
    air = filt(hp(6000), rng.standard_normal(len(t))) * smoothstep(t / 0.3) * np.exp(-np.clip(t - 0.3, 0, None) / 0.12)
    y = room(y + 0.04 * air, rng, rt60=0.6, wet=0.2)
    return y


def rip(rng, dur=0.30, f0=6000.0, f1=1500.0, stutter=0.6, am_hz=60.0):
    """Paper tear: fibre crackle + noise through a band sweeping down (6 kHz -> 1.5 kHz)."""
    t = taxis(dur)
    n = len(t)
    x = t / dur
    fc = np.exp(np.log(f0) + (np.log(f1) - np.log(f0)) * x ** 0.8)
    fibres = np.where(rng.random(n) < 3500 / SR, (0.2 + 0.4 * rng.pareto(3.0, n)) * rng.choice([-1.0, 1.0], n), 0.0)
    src = 0.6 * rng.standard_normal(n) + 1.2 * filt(hp(500), fibres)
    am = np.abs(filt(lp(am_hz), rng.standard_normal(n)))
    am = 1.0 - stutter + stutter * am / am.max()
    y = tv_filter(src, "band", fc, 1.6) * am
    y += 0.25 * tv_filter(rng.standard_normal(n), "band", fc * 0.45, 1.0) * am
    env = (0.45 + 0.55 * smoothstep(t / 0.012)) * (1.0 - smoothstep((x - 0.65) / 0.35))
    return y * env


def rip2(rng):
    return rip(rng, dur=0.26, f0=5200.0, f1=1800.0, stutter=0.8, am_hz=35.0)


def splat(rng, dur=0.35):
    """Wet paint splat: low-passed noise burst + squelchy pitch drop + a few droplets."""
    t = taxis(dur)
    n = len(t)
    burst = filt(lp(1800), rng.standard_normal(n)) * np.exp(-t / 0.03)
    wet = filt(lp(90), rng.standard_normal(n))
    wet = 0.7 + 0.3 * wet / (np.std(wet) * 3)
    ph = phase(85 + 335 * np.exp(-t / 0.05))
    squelch = 0.8 * (np.sin(ph) + 0.3 * np.sin(2 * ph)) * np.exp(-t / 0.09) * wet * smoothstep(t / 0.003)
    y = burst + squelch
    td = taxis(0.025)
    for _ in range(int(rng.integers(4, 7))):
        f0 = rng.uniform(900, 1700)
        drop = rng.uniform(0.15, 0.3) * np.sin(phase(f0 * (1 - 0.35 * smoothstep(td / 0.02)))) * np.exp(-td / 0.008)
        drop[:24] *= ramp(24)
        place(y, drop, rng.uniform(0.07, 0.28))
    return np.tanh(1.2 * filt(lp(6000), y))


def type_boops(rng, count, span):
    """`count` soft cute typing blips (~35 ms sines on E5/G5/A5/C6/D6) spread over `span` s."""
    count, span = int(count), float(span)
    step = span / count
    onsets = np.sort(np.concatenate([[0.0], np.arange(1, count) * step + rng.uniform(-0.18, 0.18, count - 1) * step]))
    tb = taxis(0.035)
    y = np.zeros(int((onsets[-1] + 0.05) * SR))
    last = None
    for t0 in onsets:
        f = rng.choice([p for p in PENTATONIC if p != last])
        last = f
        ph = phase(f * (1 + 0.03 * np.exp(-tb / 0.006)))
        env = smoothstep(tb / 0.0015) * np.exp(-tb / 0.011)
        env[-48:] *= ramp(48)[::-1]
        place(y, rng.uniform(0.85, 1.0) * (np.sin(ph) + 0.12 * np.sin(2 * ph)) * env, t0)
    return y


def _boops(rng, notes, glide):
    y = np.zeros(int(0.185 * SR))
    tn = taxis(0.095)
    for i, f0 in enumerate(notes):
        ph = phase(f0 * (1 + glide * smoothstep(tn / 0.05)))
        env = smoothstep(tn / 0.002) * np.exp(-tn / 0.06)
        env[-int(0.015 * SR):] *= ramp(int(0.015 * SR))[::-1]
        place(y, (np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)) * env, 0.085 * i)
    return y


def boop_up(rng):
    """Cute rising two-note boop (G5 -> C6), each note gliding slightly up."""
    return _boops(rng, (G5, C6), 0.05)


def boop_down(rng):
    """Cute falling two-note boop (C6 -> G5), each note gliding slightly down."""
    return _boops(rng, (C6, G5), -0.05)


def ball(rng):
    """Soccer-ball bounce: rubbery thump with a quick pitch drop and a hollow resonance."""
    t = taxis(0.18)
    n = len(t)
    thump = np.sin(phase(85 + 125 * np.exp(-t / 0.018))) * np.exp(-t / 0.045)
    hollow = (0.30 * np.sin(2 * np.pi * 410 * t + 0.5) * np.exp(-t / 0.03)
              + 0.15 * np.sin(2 * np.pi * 760 * t + 1.1) * np.exp(-t / 0.02))
    contact = 0.4 * filt(lp(1500), rng.standard_normal(n)) * np.exp(-t / 0.004)
    y = np.tanh(1.3 * (thump + hollow * smoothstep(t / 0.002) + contact))
    y[:24] *= ramp(24)
    return y


def whistle(rng, f0=2900.0):
    """Referee pea-whistle: ~2.9 kHz tone with a fast pea trill (FM + AM), two short blasts."""
    t = taxis(0.45)
    n = len(t)
    rate = 30 + 4 * unit(filt(lp(8), rng.standard_normal(n)))
    trill = np.sin(phase(rate))
    env, scoop = np.zeros(n), np.zeros(n)
    for i, (a, b) in enumerate([(0.0, 0.16), (0.22, 0.45)]):
        tt = t - a
        on = (tt >= 0) & (t < b)
        attack = (0.25 + 0.75 * smoothstep(tt / 0.006)) if i == 0 else smoothstep(tt / 0.006)
        env += np.where(on, attack * (1.0 - smoothstep((t - (b - 0.018)) / 0.018)), 0.0)
        scoop += np.where(on, 0.03 * np.exp(-np.clip(tt, 0, None) / 0.025), 0.0)
    ph = phase(f0 * (1 + 0.035 * trill + scoop))
    tone = (np.sin(ph) + 0.06 * np.sin(2 * ph)) * (1.0 - 0.35 * (0.5 + 0.5 * trill))
    breath = 0.1 * filt(bp(2300, 3600), rng.standard_normal(n))
    return filt(lp(7000), (tone + breath) * env)


SOUNDS = {
    "scribble": scribble, "scribble_long": scribble_long, "slap": slap, "whoosh": whoosh,
    "swell_down": swell_down, "swell_up": swell_up, "typewriter": typewriter, "crumple": crumple,
    "snap": snap, "chime": chime, "pop": pop, "pop_hi": pop_hi, "pop_hi2": pop_hi2,
    "pop_cute": pop_cute, "waves": waves, "thud": thud, "shimmer": shimmer, "rip": rip, "rip2": rip2,
    "splat": splat, "type_boops": type_boops, "boop_up": boop_up, "boop_down": boop_down,
    "ball": ball, "whistle": whistle,
}


def main(beats_path, outdir):
    with open(beats_path) as fh:
        spec = json.load(fh)
    wanted = sorted({e["s"] for e in spec["sfx"] if e["s"].startswith("synth:")})
    missing = sorted({s.split(":")[1] for s in wanted} - set(SOUNDS))
    if missing:
        sys.exit(f"no synth for: {', '.join(missing)}")
    os.makedirs(outdir, exist_ok=True)
    for s in wanted:
        name, *args = s.split(":")[1:]
        rng = np.random.default_rng(SEED + zlib.crc32(s.encode()))
        y = finish(SOUNDS[name](rng, *args))
        path = os.path.join(outdir, "_".join([name] + args) + ".wav")
        sf.write(path, y, SR, subtype="FLOAT")
        print(f"{os.path.basename(path):<26} {len(y) / SR:6.3f} s  peak {20 * np.log10(np.max(np.abs(y))):5.1f} dBFS")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
