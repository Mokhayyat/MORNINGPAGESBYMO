"""Original lo-fi music bed for the "Morning Pages by Mo" intro Reel.

Usage:
  python -I compose_lofi.py <beats.json> <out.wav>

Every sound is synthesized here with numpy/scipy -- no samples, no borrowed
loops -- so the bed cannot draw a copyright claim. Renders are reproducible
(fixed seed, no dependence on set/hash ordering).

Read from beats.json:
  meta.duration                  output length (64.95 s)
  music.bpm, music.grid_anchor   76 BPM; a bar line falls exactly on grid_anchor
  music.sections[]               t0/t1, drums, lp_hz, crackle, wobble, filter_open,
                                 glock_motif, glock_sting, silence, final_chord

Music: a four-bar jazzy loop Dm9 - G13 - Cmaj9 - A7(b9) in swung 8ths (59 %),
phased so Dm9 lands on the grid anchor (the intro opens on Cmaj9 and the
flashback ends on A7(b9), which resolves into the groove).
  rhodes  FM electric piano: 1:1 carrier:modulator, index ~3 -> 0.4 over ~1 s,
          faint ratio-14 tine, ~2.5 s decay, lightly strummed, 4.5 Hz auto-pan,
          humanized timing (+-10 ms) and velocity
  bass    sine / soft-triangle sub on the roots, pluck envelope, a little tanh
  glock   music-box bell (partials 1, 2.76, 5.40, 8.93): intro motif, cameo sting
  drums   soft dusty kick / snare-rim / swung hats, low-passed and saturated
Texture: tape saturation, wow and flutter, small room reverb, time-varying
master low-pass (5.2 kHz; 950 Hz "old radio" in the flashback, with narrower
stereo and a thinner bottom), vinyl crackle and surface noise.

The record-stop (silent section) is clean: everything before it is faded out
over 20 ms, and the outro is rendered as a separate take, so no tails leak
back in when the music restarts.

Output: 48 kHz stereo float32, exactly meta.duration long, normalized to
-20 LUFS integrated with true peak <= -2 dBTP (the mixer sets the final level
and ducks it under the voice).
"""
import json
import sys

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d

SR = 48000
SEED = 1066
PRE = 0.6             # seconds rendered before t=0 so the first bar can ring in
SWING = 0.59          # swung 8ths: the off-beat lands 59 % of the way through the beat
SNAP = 0.03           # an event this close before a section boundary belongs to the next section
XFADE = 0.5           # default filter/texture crossfade, centred on a section boundary
STOP_FADE = 0.02      # record-stop fade at the start of a silent section
TARGET_LUFS = -20.0
TP_CEILING = -2.0
FADE_IN, FADE_OUT = 0.4, 0.12

# Four-bar loop: (name, sub-bass root, left-hand root, right-hand voicing) as MIDI notes.
LOOP = [
    ("Dm9", 38, 50, [65, 69, 72, 76]),    # D2 | D3 | F4 A4 C5 E5
    ("G13", 43, 55, [65, 69, 71, 76]),    # G2 | G3 | F4 A4 B4 E5
    ("Cmaj9", 36, 48, [64, 67, 71, 74]),  # C2 | C3 | E4 G4 B4 D5
    ("A7b9", 33, 45, [64, 67, 70, 73]),   # A1 | A2 | E4 G4 Bb4 C#5
]
FIFTH = {38: 45, 43: 38, 36: 43, 33: 40}      # D2->A2, G2->D2, C2->G2, A1->E2
APPROACH = {43: 42, 36: 37, 33: 34, 38: 37}   # chromatic lead-in to the next bar's root

# Rhodes comping per style: (beat in bar, notes, velocity, length in beats).
# "full" = left-hand root + voicing; "top3"/"top2" = the upper voices only.
COMP = {
    "intro": [[(0.0, "full", 0.58, 3.8), (2.5, "top3", 0.36, 1.4)]],
    "flashback": [[(0.0, "full", 0.60, 3.8), (2.5, "top2", 0.40, 1.4)]],
    "groove": [[(0.0, "full", 0.72, 3.8), (1.5, "top3", 0.44, 0.7), (2.5, "top3", 0.50, 1.4)],
               [(0.0, "full", 0.70, 3.8), (2.0, "top3", 0.46, 0.8), (3.0, "top2", 0.40, 0.9)]],
    "cameo": [[(0.0, "full", 0.52, 3.8), (2.5, "top3", 0.33, 1.4)]],
}
LICK_COMP = [(0.0, "full", 0.70, 3.8)]
# Little Rhodes pickups on the groove's A7(b9) bars; the last note rings on into Dm9.
LICKS = [
    [(2.5, 76, 0.48, 0.5), (3.0, 79, 0.45, 0.5), (3.5, 81, 0.52, 2.2)],                        # E5 G5 A5
    [(2.0, 73, 0.42, 0.5), (2.5, 76, 0.45, 0.5), (3.0, 79, 0.44, 0.5), (3.5, 77, 0.50, 2.2)],  # C#5 E5 G5 F5
]
# Sub bass: (beat, "R" root / "5" fifth / "A" approach, velocity, length in beats).
BASS = {
    "groove": [[(0.0, "R", 0.95, 1.7), (2.5, "R", 0.62, 0.42), (3.0, "5", 0.60, 0.85)],
               [(0.0, "R", 0.95, 1.7), (2.5, "R", 0.62, 0.42), (3.5, "A", 0.58, 0.45)]],
    "cameo": [[(0.0, "R", 0.72, 3.6)]],
}
# Drums, two-bar pattern: kick/snare as (beat, velocity); hats on every swung 8th.
DRUMS = [
    {"kick": [(0.0, 0.95), (2.5, 0.72)], "snare": [(1.0, 0.80), (3.0, 0.86)], "ohat": ()},
    {"kick": [(0.0, 0.95), (1.5, 0.55), (2.5, 0.70)], "snare": [(1.0, 0.80), (3.0, 0.86)], "ohat": (3.5,)},
]
# Glockenspiel: intro motif in beats from the bar holding the section start
# (E6 G6 A6 | G6 . E6 . | D6), cameo sting in seconds from glock_sting (G5 A5 B5 D6 E6 .. G6).
GLOCK_MOTIF = [(2.0, 88, 0.80), (3.0, 91, 0.70), (3.5, 93, 0.74), (4.0, 91, 0.78), (6.0, 88, 0.62),
               (8.0, 86, 0.66)]
GLOCK_STING = [(0.0, 79, 0.55), (0.075, 81, 0.60), (0.15, 83, 0.64), (0.225, 86, 0.70), (0.30, 88, 0.74),
               (0.47, 91, 0.92)]
FINAL_VOICING = [48, 55, 64, 71, 74, 76]   # C3 G3 E4 B4 D5 E5: a wide, warm Cmaj9

# Mix (balanced by stem loudness in the groove: Rhodes ref, bass -1 LU, kick -1.5, snare -5, hats -12)
G_RHODES, G_GLOCK, G_BASS = 0.20, 0.068, 0.185
G_KICK, G_SNARE, G_HAT = 0.41, 0.27, 0.70
SEND_RHODES, SEND_GLOCK = 0.26, 0.40      # reverb sends (unit-energy IR)
DUCK_DEPTH = 0.18                         # gentle kick -> Rhodes pump
TAPE_DRIVE = 1.15
WOW, DRIFT, FLUTTER = 0.00050, 0.00022, 0.000012   # seconds of delay modulation
# Vinyl, in absolute output units (added after the music is normalized)
CRACKLE_RATE, POP_RATE = 9.0, 0.35        # per second at crackle amount 1
CLICK_GAIN, POP_GAIN, HISS_GAIN = 0.030, 0.012, 0.0011
SILENT_CRACKLE = 0.55                     # crackle amount in a silent section

# Fixed filters
LP_2500 = signal.butter(2, 2500, "low", fs=SR, output="sos")
LP_DRUMS = signal.butter(2, 7000, "low", fs=SR, output="sos")
BP_SNARE = signal.butter(2, [1500, 2500], "band", fs=SR, output="sos")
BP_AIR = signal.butter(2, [700, 5000], "band", fs=SR, output="sos")
BP_HAT = signal.butter(2, [3000, 8000], "band", fs=SR, output="sos")
HP_TICK = signal.butter(2, 3000, "high", fs=SR, output="sos")
HP_DC = signal.butter(2, 22, "high", fs=SR, output="sos")


def hz(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def ramp(n):
    """Raised-cosine 0 -> 1 over n samples."""
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / max(n, 1))


def release(env, start, n_rel):
    """Fade env to zero over n_rel samples from `start` (raised cosine); zero after."""
    if start < len(env):
        end = min(len(env), start + n_rel)
        env[start:end] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(end - start) / n_rel)
        env[end:] = 0.0
    return env


def pan_gains(p):
    """Equal-power pan, unity at centre. p in [-1, 1]."""
    th = (np.asarray(p) + 1.0) * np.pi / 4.0
    return np.cos(th) * np.sqrt(2.0), np.sin(th) * np.sqrt(2.0)


def place(buf, sig, idx, gl=1.0, gr=None):
    """Add mono `sig` into buf (mono or stereo) starting at sample idx, clipped to the buffer."""
    s0, s1 = max(idx, 0), min(len(buf), idx + len(sig))
    if s1 <= s0:
        return
    seg = sig[s0 - idx:s1 - idx]
    if buf.ndim == 1:
        buf[s0:s1] += seg * gl
    else:
        buf[s0:s1, 0] += seg * gl
        buf[s0:s1, 1] += seg * (gl if gr is None else gr)


# ----------------------------------------------------------------------------- instruments

def rhodes_note(f, vel, dur, rel, rng):
    """FM electric piano: 1:1 carrier:modulator with a decaying index, plus a faint tine."""
    n = int((dur + rel) * SR) + 1
    t = np.arange(n) / SR
    reg = f / 261.63
    i_peak = (1.5 + 1.7 * vel) * reg ** -0.25          # ~3 for a firm mid-register hit
    index = 0.4 + (i_peak - 0.4) * np.exp(-t / 0.33)   # ~3 -> ~0.45 after one second
    w = 2.0 * np.pi * f * t
    tone = np.sin(w + index * np.sin(w))
    w2 = w * 1.0008 + rng.uniform(0.0, 2.0 * np.pi)     # faint detuned twin: suitcase warmth
    tone2 = np.sin(w2 + 0.7 * index * np.sin(w2))
    tine = 0.07 * vel * np.sin(14.0 * w) * np.exp(-t / 0.010) if 14.0 * f < 0.45 * SR else 0.0
    tau = 2.5 * reg ** -0.35                             # ~2.5 s at middle C, shorter up high
    env = 0.72 * np.exp(-t / tau) + 0.28 * np.exp(-t / 0.28)
    k = int(0.0025 * SR)
    env[:k] *= ramp(k)
    release(env, int(dur * SR), max(int(rel * SR), 8))
    return (0.86 * tone + 0.14 * tone2 + tine) * env * vel ** 1.5


BELL = ((1.0, 1.0, 1.0), (2.76, 0.32, 0.24), (5.40, 0.12, 0.085), (8.93, 0.05, 0.045))  # ratio, amp, tau @ C6


def glock_note(f, vel, rng, length=2.4):
    """Music-box / glockenspiel bell with inharmonic partials and fast upper decays."""
    n = int(length * SR)
    t = np.arange(n) / SR
    scale = (f / 1046.5) ** -0.3
    y = np.zeros(n)
    for ratio, amp, tau in BELL:
        if f * ratio < 0.45 * SR:
            y += amp * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 2 * np.pi)) * np.exp(-t / (tau * scale))
    y += 0.3 * np.sin(2 * np.pi * f * 1.0016 * t) * np.exp(-t / scale)   # slow music-box beating
    k = int(0.003 * SR)
    y[:k] += 0.12 * signal.sosfilt(HP_TICK, rng.standard_normal(k)) * np.exp(-np.arange(k) / (0.0006 * SR))
    y[:int(0.001 * SR)] *= ramp(int(0.001 * SR))
    tail = int(0.05 * SR)
    y[-tail:] *= ramp(tail)[::-1]
    return y * vel ** 1.3


def bass_note(f, vel, dur, rel):
    """Sine / soft-triangle sub with a pluck (brightness and level fall after the attack)."""
    n = int((dur + rel) * SR) + 1
    t = np.arange(n) / SR
    ph = 2 * np.pi * np.cumsum(f * (1 + 0.02 * np.exp(-t / 0.012))) / SR
    bright = 0.35 + 0.65 * np.exp(-t / 0.12)
    x = np.sin(ph) + bright * (0.10 * np.sin(2 * ph) - 0.11 * np.sin(3 * ph) + 0.04 * np.sin(5 * ph))
    env = 0.45 * np.exp(-t / 0.35) + 0.55 * np.exp(-t / 2.2)
    k = int(0.006 * SR)
    env[:k] *= ramp(k)
    release(env, int(dur * SR), max(int(rel * SR), 8))
    return np.tanh(1.8 * x * env * vel) / np.tanh(1.8)


def kick(vel, rng):
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 45 + 65 * np.exp(-t / 0.022)                     # 110 Hz -> ~49 Hz at 70 ms -> 45 Hz
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)   # ~-22 dB at 280 ms
    click = 0.3 * signal.sosfilt(LP_2500, rng.standard_normal(n)) * np.exp(-t / 0.0025)
    y = np.tanh(2.0 * (body + click)) / np.tanh(2.0)
    tail = int(0.06 * SR)
    y[-tail:] *= ramp(tail)[::-1]
    return y * vel


def snare(vel, rng):
    """Soft rim/snare: band-passed noise around 1.5-2.5 kHz with a small 185 Hz body."""
    n = int(0.25 * SR)
    t = np.arange(n) / SR
    w = rng.standard_normal(n)
    crack = signal.sosfilt(BP_SNARE, w) * np.exp(-t / 0.05)
    air = 0.35 * signal.sosfilt(BP_AIR, w) * np.exp(-t / 0.085)
    body = 0.6 * np.sin(2 * np.pi * np.cumsum(185 + 30 * np.exp(-t / 0.008)) / SR) * np.exp(-t / 0.035)
    y = 1.7 * crack + air + body
    y[:40] *= ramp(40)
    y = np.tanh(1.4 * y) / np.tanh(1.4)
    tail = int(0.04 * SR)
    y[-tail:] *= ramp(tail)[::-1]
    return y * vel


def hat(vel, rng, open_hat=False):
    length, tau = (0.30, 0.10) if open_hat else (0.07, 0.016)
    n = int(length * SR)
    t = np.arange(n) / SR
    y = signal.sosfilt(BP_HAT, rng.standard_normal(n)) * np.exp(-t / tau)
    y[:24] *= ramp(24)
    tail = int(0.02 * SR)
    y[-tail:] *= ramp(tail)[::-1]
    return y * vel


# ----------------------------------------------------------------------------- arrangement

class Grid:
    def __init__(self, bpm, anchor):
        self.beat = 60.0 / bpm
        self.bar = 4.0 * self.beat
        self.anchor = anchor

    def bar_index(self, t):
        return int(np.floor((t - self.anchor) / self.bar + 1e-9))

    def time(self, bar, pos):
        """Time of `pos` beats into `bar`; off-beat 8ths are swung, 16ths scaled to match."""
        whole = np.floor(pos)
        f = pos - whole
        f = f / 0.5 * SWING if f <= 0.5 else SWING + (f - 0.5) / 0.5 * (1.0 - SWING)
        return self.anchor + bar * self.bar + (whole + f) * self.beat

    @staticmethod
    def chord(bar):
        return LOOP[bar % 4]


def compose(music, duration, rng):
    """Return the list of note/drum events (dicts) for the whole piece."""
    grid = Grid(float(music["bpm"]), float(music["grid_anchor"]))
    secs = sorted(music["sections"], key=lambda s: s["t0"])
    ev = []

    def section(t):
        t = t + SNAP
        if t < secs[0]["t0"]:
            return secs[0]
        return next((s for s in secs if s["t0"] <= t < s["t1"]), None)

    def style(t):
        s = section(t)
        if s is None or s.get("silence"):
            return None
        if s.get("final_chord") is not None:
            return "outro"
        if s.get("drums"):
            return "groove"
        if s.get("glock_sting") is not None:
            return "cameo"
        if s.get("lp_hz", 1e9) < 2000:
            return "flashback"
        return "intro"

    def jit(sd, lim):
        return float(np.clip(rng.normal(0.0, sd), -lim, lim))

    def vary(v, amount):
        return float(min(1.0, v * (1.0 + rng.uniform(-amount, amount))))

    def rhodes(t, m, vel, dur):
        ev.append(dict(inst="rhodes", t=t, midi=m, vel=vel, dur=max(dur, 0.12), rel=0.22))

    def chord(t, notes, vel, dur, lh=None, spread=None, jitter=True, down=False):
        """A lightly strummed chord: 10-25 ms spread, +-10 ms timing, +-8 % velocity."""
        notes = sorted(notes, reverse=down)
        spread = rng.uniform(0.010, 0.025) if spread is None else spread
        t = t + (jit(0.004, 0.010) if jitter else 0.0)
        top = max(notes)
        for i, m in enumerate(notes):
            dt = spread * i / max(len(notes) - 1, 1) + (rng.uniform(-0.002, 0.002) if (jitter and i) else 0.0)
            v = vary(vel, 0.08) * (0.62 if m == lh else 1.0) * (1.03 if m == top else 1.0)
            rhodes(t + dt, m, min(v, 1.0), dur - dt)

    def bass(t, m, vel, dur):
        ev.append(dict(inst="bass", t=t, midi=m, vel=vel, dur=dur, rel=0.07))

    def drum(inst, t, vel):
        ev.append(dict(inst=inst, t=t, vel=vel))

    for b in range(grid.bar_index(-PRE), grid.bar_index(duration) + 1):
        _, root, lh, voicing = grid.chord(b)
        next_root = grid.chord(b + 1)[1]
        present = sorted({style(grid.time(b, k / 4.0)) for k in range(16)} - {None, "outro"})
        for st in present:
            lick = LICKS[(b // 4) % 2] if (st == "groove" and b % 4 == 3) else None
            rows = LICK_COMP if lick else COMP[st][b % len(COMP[st])]
            for pos, which, vel, length in rows:
                t = grid.time(b, pos)
                if style(t) == st:
                    notes = {"full": [lh] + voicing, "top3": voicing[1:], "top2": voicing[2:]}[which]
                    chord(t, notes, vel, length * grid.beat, lh=lh if which == "full" else None,
                          down=(which != "full" and rng.random() < 0.3))
            for pos, m, vel, length in (lick or []):
                t = grid.time(b, pos)
                if style(t) == st:
                    rhodes(t + jit(0.004, 0.010), m, vary(vel, 0.06), length * grid.beat)
            for pos, kind, vel, length in (BASS[st][b % len(BASS[st])] if st in BASS else []):
                t = grid.time(b, pos)
                if style(t) == st:
                    m = {"R": root, "5": FIFTH[root], "A": APPROACH[next_root]}[kind]
                    bass(t + jit(0.003, 0.008), m, vary(vel, 0.06), length * grid.beat)
            if st == "groove":
                pat = DRUMS[b % 2]
                for pos, vel in pat["kick"]:
                    t = grid.time(b, pos)
                    if style(t) == st:
                        drum("kick", t + jit(0.002, 0.004), vary(vel, 0.05))
                snares = list(pat["snare"]) + ([(3.75, 0.28)] if b % 4 == 3 else [])   # ghost-note fill
                for pos, vel in snares:
                    t = grid.time(b, pos)
                    if style(t) == st:
                        drum("snare", t + jit(0.003, 0.006), vary(vel, 0.07))
                for k in range(8):
                    pos = k / 2.0
                    t = grid.time(b, pos)
                    if style(t) == st:
                        vel = (0.55 if k % 2 == 0 else 0.38) + rng.uniform(-0.08, 0.08)
                        drum("ohat" if pos in pat["ohat"] else "hat", t + jit(0.003, 0.007), vel)

    for s in secs:
        # Drums re-entering mid-bar start with a kick on the first beat.
        if s.get("drums"):
            off = (s["t0"] - grid.anchor) / grid.bar
            if abs(off - round(off)) * grid.bar > SNAP:
                tb = grid.anchor + np.ceil((s["t0"] - SNAP - grid.anchor) / grid.beat) * grid.beat
                if not any(e["inst"] == "kick" and abs(e["t"] - tb) < SNAP for e in ev):
                    drum("kick", tb, 0.9)
        if s.get("glock_motif"):
            b0 = grid.bar_index(s["t0"])
            for pos, m, vel in GLOCK_MOTIF:
                t = grid.time(b0 + int(pos // 4), pos % 4)
                if s["t0"] <= t < s["t1"]:
                    ev.append(dict(inst="glock", t=t + jit(0.003, 0.008), midi=m, vel=vary(vel, 0.05)))
        if s.get("glock_sting") is not None:
            for dt, m, vel in GLOCK_STING:
                ev.append(dict(inst="glock", t=float(s["glock_sting"]) + dt, midi=m, vel=vel))
        if s.get("final_chord") is not None:
            # Outro: ii (at the restart) -> V (next bar line) -> I struck exactly at final_chord.
            t0, tf = float(s["t0"]), float(s["final_chord"])
            _, r2, lh2, v2 = LOOP[0]
            _, r5, lh5, v5 = LOOP[1]
            tb = grid.anchor + np.ceil((t0 + 0.4 - grid.anchor) / grid.bar) * grid.bar
            if tb < tf - 0.6:
                chord(t0, [lh2] + v2, 0.55, tb - t0, lh=lh2, spread=0.030, jitter=False)
                bass(t0, r2, 0.70, tb - t0)
                chord(tb, [lh5] + v5, 0.55, tf - tb, lh=lh5, spread=0.025, jitter=False)
                bass(tb, r5, 0.70, tf - tb)
            else:
                chord(t0, [lh5] + v5, 0.55, tf - t0, lh=lh5, spread=0.030, jitter=False)
                bass(t0, r5, 0.70, tf - t0)
            ring = duration - tf + 2.0
            chord(tf, FINAL_VOICING, 0.60, ring, lh=FINAL_VOICING[0], spread=0.035, jitter=False)
            bass(tf, 36, 0.66, ring)
            ev.append(dict(inst="glock", t=tf + 0.03, midi=91, vel=0.40))

    # A re-struck Rhodes key cuts its previous ring; the bass is monophonic.
    for key in sorted({e["midi"] for e in ev if e["inst"] == "rhodes"}):
        same = sorted((e for e in ev if e["inst"] == "rhodes" and e["midi"] == key), key=lambda e: e["t"])
        for a, nxt in zip(same, same[1:]):
            if a["t"] + a["dur"] > nxt["t"] - 0.01:
                a["dur"], a["rel"] = max(nxt["t"] - a["t"] - 0.01, 0.03), 0.05
    line = sorted((e for e in ev if e["inst"] == "bass"), key=lambda e: e["t"])
    for a, nxt in zip(line, line[1:]):
        if a["t"] + a["dur"] > nxt["t"] - 0.01:
            a["dur"], a["rel"] = max(nxt["t"] - a["t"] - 0.01, 0.03), 0.03
    return sorted((e for e in ev if e["t"] >= -PRE), key=lambda e: e["t"])


# ----------------------------------------------------------------------------- texture / processing

def control_curves(sections, t):
    """Per-sample section controls: master low-pass, 'memory' amount, wobble, crackle."""
    secs = sorted(sections, key=lambda s: s["t0"])
    lp_vals, last = [], None
    for s in secs:
        last = float(s.get("lp_hz", last if last is not None else 5200.0))
        lp_vals.append(last)
    lp_open, lp_closed = max(lp_vals), min(lp_vals)

    def values(i):
        s = secs[i]
        return {"loglp": np.log(lp_vals[i]), "wobble": float(s.get("wobble", 1.0)),
                "crackle": float(s.get("crackle", SILENT_CRACKLE if s.get("silence") else 1.0))}

    cur = values(0)
    out = {k: np.full(len(t), v) for k, v in cur.items()}
    for i in range(1, len(secs)):
        s, prev, new = secs[i], secs[i - 1], values(i)
        if "filter_open" in s:
            a, b = s["t0"], s["t0"] + float(s["filter_open"])
        elif s.get("silence") or prev.get("silence"):
            a, b = s["t0"], s["t0"] + STOP_FADE
        else:
            a, b = s["t0"] - XFADE / 2, s["t0"] + XFADE / 2
        w = smoothstep((t - a) / (b - a))
        sel = t >= a
        for k in out:
            if new[k] != cur[k]:
                out[k][sel] = cur[k] + (new[k] - cur[k]) * w[sel]
        cur = new
    span = np.log(lp_open / lp_closed) if lp_open > lp_closed else 1.0
    mem = np.clip((np.log(lp_open) - out["loglp"]) / span, 0.0, 1.0)
    return {"lp": np.exp(out["loglp"]), "mem": mem, "q": 0.707 + 0.35 * mem, "hp": 25.0 + 115.0 * mem,
            "width": 1.0 - 0.6 * mem, "gain": 10 ** (2.5 * mem / 20), "wobble": out["wobble"],
            "crackle": out["crackle"]}


def biquad(kind, fc, q):
    w0 = 2 * np.pi * min(fc, 0.45 * SR) / SR
    cw, alpha = np.cos(w0), np.sin(w0) / (2 * q)
    if kind == "low":
        b = np.array([(1 - cw) / 2, 1 - cw, (1 - cw) / 2])
    else:
        b = np.array([(1 + cw) / 2, -(1 + cw), (1 + cw) / 2])
    a = np.array([1 + alpha, -2 * cw, 1 - alpha])
    return b / a[0], a / a[0]


def tv_biquad(x, kind, fc, q, block=64):
    """Biquad whose cutoff/Q follow per-sample curves (coefficients updated every `block`
    samples, filter state carried across; runs of constant settings go in one call)."""
    n = len(x)
    fc = np.broadcast_to(np.asarray(fc, dtype=float), (n,))
    q = np.broadcast_to(np.asarray(q, dtype=float), (n,))
    centers = np.minimum(np.arange(0, n, block) + block // 2, n - 1)
    keys = np.round(np.log(fc[centers]) * 2000).astype(np.int64) * 100000 + np.round(q[centers] * 1000).astype(np.int64)
    change = np.flatnonzero(np.diff(keys)) + 1
    starts, ends = np.concatenate([[0], change]), np.concatenate([change, [len(centers)]])
    y = np.empty_like(x)
    zi = np.zeros((2,) + x.shape[1:])
    for s, e in zip(starts, ends):
        a0, a1 = s * block, min(e * block, n)
        b, a = biquad(kind, fc[centers[s]], q[centers[s]])
        y[a0:a1], zi = signal.lfilter(b, a, x[a0:a1], axis=0, zi=zi)
    return y


def frac_read(x, pos):
    """Read x at fractional sample positions (4-point cubic Hermite)."""
    i = np.floor(pos).astype(np.int64)
    f = pos - i
    i = np.clip(i, 1, len(x) - 3)
    if x.ndim == 2:
        f = f[:, None]
    xm1, x0, x1, x2 = x[i - 1], x[i], x[i + 1], x[i + 2]
    c1 = 0.5 * (x1 - xm1)
    c2 = xm1 - 2.5 * x0 + 2.0 * x1 - 0.5 * x2
    c3 = 0.5 * (x2 - xm1) + 1.5 * (x0 - x1)
    return ((c3 * f + c2) * f + c1) * f + x0


def make_drift(rng, t_lo, t_hi):
    """Slow random tape-speed drift (+-1 before scaling), a deterministic function of time."""
    kr = 50.0
    tk = np.arange(t_lo - 2.0, t_hi + 2.0, 1.0 / kr)
    d = signal.sosfiltfilt(signal.butter(2, 0.3, "low", fs=kr, output="sos"), rng.standard_normal(len(tk)))
    d /= np.max(np.abs(d)) + 1e-12
    return lambda t: DRIFT * np.interp(t, tk, d)


def reverb_ir(rng, rt60=1.25, length=1.8, predelay=0.012):
    """Small warm room: decorrelated stereo noise tails, highs dying faster than lows."""
    n = int(length * SR)
    t = np.arange(n) / SR
    lo_sos = signal.butter(2, 2200, "low", fs=SR, output="sos")
    ir = np.zeros((n, 2))
    for ch in range(2):
        w = rng.standard_normal(n)
        lo = signal.sosfilt(lo_sos, w)
        ir[:, ch] = lo * np.exp(-6.91 * t / rt60) + 0.3 * (w - lo) * np.exp(-6.91 * t / (0.4 * rt60))
    k = int(0.006 * SR)
    ir[:k] *= ramp(k)[:, None]
    ir = np.concatenate([np.zeros((int(predelay * SR), 2)), ir])[:n]
    return ir / np.sqrt(np.sum(ir ** 2, axis=0))


def master_chain(x, t, cv, drift):
    """Tape saturation -> wow & flutter -> section low-pass/high-pass -> stereo width."""
    x = np.tanh(TAPE_DRIVE * x) / TAPE_DRIVE
    mod = cv["wobble"] * (WOW * np.sin(2 * np.pi * 0.5 * t + 0.7) + drift(t)) \
        + FLUTTER * (np.sin(2 * np.pi * 6.3 * t) + 0.5 * np.sin(2 * np.pi * 9.7 * t + 1.3))
    x = frac_read(x, np.arange(len(x)) - mod * SR)
    x = tv_biquad(x, "low", cv["lp"], cv["q"])
    x = tv_biquad(x, "low", cv["lp"] * 1.3, 0.6)
    x = tv_biquad(x, "low", cv["lp"] * 4.0 ** (1.0 - cv["mem"]), 0.707)   # only bites in the flashback
    x = tv_biquad(x, "high", cv["hp"], 0.707)
    mid = 0.5 * (x[:, 0] + x[:, 1])
    side = 0.5 * (x[:, 0] - x[:, 1]) * cv["width"]
    return np.stack([mid + side, mid - side], axis=1) * cv["gain"][:, None]


def render_segment(events, a, b, first, last, sections, ir, drift, rng):
    """Render the events of one continuous take [a, b) through the full chain, gated to it."""
    t0 = a if first else a - 0.05
    t1 = b if last else b + 0.1
    n = int(round((t1 - t0) * SR))
    t = t0 + np.arange(n) / SR
    rh, gl, dr = np.zeros((n, 2)), np.zeros((n, 2)), np.zeros((n, 2))
    bs = np.zeros(n)
    kicks = np.zeros(n)
    for e in events:
        i = int(round((e["t"] - t0) * SR))
        inst = e["inst"]
        if inst == "rhodes":
            p = float(np.clip((e["midi"] - 62) / 28.0, -0.4, 0.4))
            place(rh, rhodes_note(hz(e["midi"]), e["vel"], e["dur"], e["rel"], rng), i, *pan_gains(p))
        elif inst == "glock":
            p = float(np.clip((e["midi"] - 84) / 20.0, -0.3, 0.3))
            place(gl, glock_note(hz(e["midi"]), e["vel"], rng), i, *pan_gains(p))
        elif inst == "bass":
            place(bs, bass_note(hz(e["midi"]), e["vel"], e["dur"], e["rel"]), i)
        elif inst == "kick":
            place(dr, G_KICK * kick(e["vel"], rng), i)
            if 0 <= i < n:
                kicks[i] += e["vel"]
        elif inst == "snare":
            place(dr, G_SNARE * snare(e["vel"], rng), i, *pan_gains(-0.12))
        else:
            place(dr, G_HAT * hat(e["vel"], rng, inst == "ohat"), i, *pan_gains(0.25))

    ap = 0.12 * np.sin(2 * np.pi * 4.5 * t)               # light suitcase auto-pan
    rh[:, 0] *= 1 + ap
    rh[:, 1] *= 1 - ap
    k = np.arange(int(0.6 * SR)) / SR
    duck = 1 - DUCK_DEPTH * np.clip(signal.oaconvolve(kicks, (1 - np.exp(-k / 0.004)) * np.exp(-k / 0.13))[:n], 0, 1.2)
    rh *= G_RHODES * duck[:, None]
    gl *= G_GLOCK
    send = 0.5 * (SEND_RHODES * rh.sum(axis=1) + SEND_GLOCK * gl.sum(axis=1))
    wet = np.stack([signal.oaconvolve(send, ir[:, ch])[:n] for ch in range(2)], axis=1)
    dr = signal.sosfilt(LP_DRUMS, dr, axis=0)
    dr = np.tanh(1.3 * dr) / 1.3
    mix = rh + gl + G_BASS * bs[:, None] + dr + wet

    out = master_chain(mix, t, control_curves(sections, t), drift)
    gate = np.ones(n)
    if not first:
        gate *= smoothstep((t - (a - 0.006)) / 0.004)
    if not last:
        gate *= 1.0 - smoothstep((t - b) / STOP_FADE)
    return t0, out * gate[:, None]


def vinyl(t, amount, rng):
    """Sparse clicks, rarer duller pops and faint surface noise (33 1/3 rpm breathing)."""
    n = len(t)
    idx = np.flatnonzero(rng.random(n) < CRACKLE_RATE * amount / SR)
    amp = (0.1 + 0.9 * rng.random(len(idx)) ** 4) * rng.choice([-1.0, 1.0], len(idx)) * np.sqrt(amount[idx])
    gl, gr = pan_gains(rng.uniform(-0.7, 0.7, len(idx)))
    imp = np.zeros((n, 2))
    imp[idx, 0], imp[idx, 1] = amp * gl, amp * gr
    clicks = signal.sosfilt(signal.butter(2, [1000, 7000], "band", fs=SR, output="sos"), imp, axis=0)

    idx = np.flatnonzero(rng.random(n) < POP_RATE * amount / SR)
    amp = (0.4 + 0.6 * rng.random(len(idx))) * rng.choice([-1.0, 1.0], len(idx)) * np.sqrt(amount[idx])
    gl, gr = pan_gains(rng.uniform(-0.4, 0.4, len(idx)))
    imp = np.zeros((n, 2))
    imp[idx, 0], imp[idx, 1] = amp * gl, amp * gr
    pops = signal.sosfilt(signal.butter(2, [300, 2500], "band", fs=SR, output="sos"), imp, axis=0)

    hiss = signal.sosfilt(signal.butter(2, [400, 6000], "band", fs=SR, output="sos"),
                          rng.standard_normal((n, 2)), axis=0)
    hiss *= ((1 + 0.3 * np.sin(2 * np.pi * (100.0 / 3.0 / 60.0) * t)) * np.sqrt(amount))[:, None]
    return CLICK_GAIN * clicks / 0.25 + POP_GAIN * pops / 0.1 + HISS_GAIN * hiss / 0.35


def true_peak_db(x):
    return 20 * np.log10(np.max(np.abs(signal.resample_poly(x, 4, 1, axis=0))) + 1e-12)


def limit(x, ceiling_db):
    """Smooth look-around peak limiter on the 4x-oversampled envelope (only used if needed)."""
    c = 10 ** (ceiling_db / 20)
    up = np.abs(signal.resample_poly(x, 4, 1, axis=0)).max(axis=1)
    env = up[:4 * len(x)].reshape(-1, 4).max(axis=1)
    env = maximum_filter1d(env, int(0.002 * SR))
    w = int(0.008 * SR)
    g = uniform_filter1d(minimum_filter1d(np.minimum(1.0, c / np.maximum(env, 1e-12)), w), w)
    return x * g[:, None]


def edge_fades(x):
    k = int(FADE_IN * SR)
    x[:k] *= ramp(k)[:, None]
    k = int(FADE_OUT * SR)
    x[-k:] *= ramp(k)[::-1][:, None]
    return x


def main(beats_path, out_path):
    with open(beats_path) as fh:
        spec = json.load(fh)
    music = spec["music"]
    duration = float(spec["meta"]["duration"])
    secs = sorted(music["sections"], key=lambda s: s["t0"])
    n_out = int(round(duration * SR))

    rng = np.random.default_rng(SEED)
    events = compose(music, duration, rng)
    ir = reverb_ir(np.random.default_rng(SEED + 1))
    drift = make_drift(np.random.default_rng(SEED + 2), -PRE, duration)

    # Continuous takes between silent sections (the record stop).
    silences = [(float(s["t0"]), float(s["t1"])) for s in secs if s.get("silence")]
    bounds, start = [], -PRE
    for a, b in silences:
        bounds.append((start, a))
        start = b
    bounds.append((start, duration))

    full = np.zeros((int(round((duration + PRE) * SR)), 2))
    synth_rng = np.random.default_rng(SEED + 3)
    for j, (a, b) in enumerate(bounds):
        first, last = j == 0, j == len(bounds) - 1
        seg_events = [e for e in events if (first or e["t"] >= a - SNAP) and (last or e["t"] < b)]
        t0, y = render_segment(seg_events, a, b, first, last, secs, ir, drift, synth_rng)
        i0 = int(round((t0 + PRE) * SR))
        i1 = min(len(full), i0 + len(y))
        full[i0:i1] += y[:i1 - i0]
        print(f"take {j}: {a:6.2f}-{b:6.2f} s, {len(seg_events)} events")

    music_out = full[int(round(PRE * SR)):][:n_out]
    music_out = np.pad(music_out, ((0, n_out - len(music_out)), (0, 0)))
    music_out = signal.sosfilt(HP_DC, edge_fades(music_out), axis=0)

    meter = pyln.Meter(SR)
    music_out *= 10 ** ((TARGET_LUFS - meter.integrated_loudness(music_out)) / 20)
    t = np.arange(n_out) / SR
    crackle = vinyl(t, control_curves(secs, t)["crackle"], np.random.default_rng(SEED + 4))
    out = music_out + signal.sosfilt(HP_DC, edge_fades(crackle), axis=0)

    for _ in range(4):
        out *= 10 ** ((TARGET_LUFS - meter.integrated_loudness(out)) / 20)
        if true_peak_db(out) <= TP_CEILING - 0.05:
            break
        out = limit(out, TP_CEILING - 0.3)
    out = out.astype(np.float32)
    sf.write(out_path, out, SR, subtype="FLOAT")

    print(f"wrote {out_path}: {len(out) / SR:.3f} s, {SR} Hz, {out.shape[1]} ch")
    print(f"integrated {meter.integrated_loudness(out.astype(np.float64)):.2f} LUFS, "
          f"true peak {true_peak_db(out.astype(np.float64)):.2f} dBTP, "
          f"sample peak {20 * np.log10(np.max(np.abs(out))):.2f} dBFS")
    for s in secs:
        i0, i1 = int(s["t0"] * SR), int(min(s["t1"], duration) * SR)
        rms = np.sqrt(np.mean(out[i0:i1].astype(np.float64) ** 2))
        print(f"  {s['name']:<10} {s['t0']:6.2f}-{s['t1']:6.2f} s  rms {20 * np.log10(rms + 1e-12):6.1f} dBFS")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
