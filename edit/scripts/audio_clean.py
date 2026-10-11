"""Voice cleanup shoot-out: three chains, measured against the raw recording.

Usage:
  python -I audio_clean.py <raw48.wav> <transcript.json> <outdir> <deep-filter-bin> <rnnn-dir> [chains]

Chains (all share the same pre-filter and the same "polish" post-chain):
  A  high-pass + hum notches -> WPE dereverb -> DeepFilterNet3 -> polish
  B  high-pass + hum notches -> DeepFilterNet3 -> polish
  C  high-pass + hum notches -> RNNoise (arnndn) + afftdn + expander -> polish
  D  A, then a gentle expander after the compressor (pauses stay clean)
  E  like D but DeepFilterNet unlimited + post-filter (strongest)

Metrics use the word timestamps, so "speech", "echo tail" and "pause" are exact:
  pause_floor   mean level in the middle of gaps between phrases (dB re speech)
  tail_level    mean level 60-300 ms after a phrase ends (dB re speech): lower = drier
  hiss_4_16k    4-16 kHz energy in pauses minus 4-16 kHz energy in speech (dB)
  speech_lsd    log-spectral distance of speech frames vs raw, 150 Hz-6 kHz (dB): lower = more natural
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf

SR = 48000
PRE = "highpass=f=80:poles=2,equalizer=f=60:t=q:w=6:g=-14,equalizer=f=120:t=q:w=6:g=-8,equalizer=f=180:t=q:w=6:g=-4"
POLISH = ("equalizer=f=420:t=q:w=1.1:g=-2.5,"     # boxy room
          "equalizer=f=3800:t=q:w=0.9:g=2,"        # presence
          "bass=g=1.5:f=160:w=0.6,"                # warmth
          "deesser=i=0.35:m=0.5:f=0.5,"
          "acompressor=threshold=-22dB:ratio=3:attack=8:release=160:makeup=2:knee=4,"
          "alimiter=limit=0.89:attack=3:release=60:level=false")
# Downward expander placed after the compressor, so it cleans what the compressor lifted.
# threshold ~ -36 dBFS, max 14 dB of attenuation, slow release so word tails aren't chopped.
EXPANDER = "agate=threshold=0.016:ratio=2.5:range=0.2:attack=4:release=260:knee=3:detection=rms"


def ff(inp, out, af):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", inp, "-af", af, "-ar", str(SR),
                    "-ac", "1", "-c:a", "pcm_f32le", out], check=True)


def wpe_dereverb(inp, out, taps=30, delay=5, iterations=3):
    from nara_wpe.utils import istft, stft
    from nara_wpe.wpe import wpe
    y, sr = sf.read(inp, dtype="float64")
    size, shift = 1024, 256
    Y = stft(y[None, :], size=size, shift=shift)          # (D=1, T, F)
    Z = wpe(Y.transpose(2, 0, 1), taps=taps, delay=delay, iterations=iterations,
            statistics_mode="full").transpose(1, 2, 0)
    z = istft(Z, size=size, shift=shift)[0][: len(y)]
    sf.write(out, z.astype(np.float32), sr, subtype="FLOAT")


def deep_filter(bin_path, inp, out, atten=34, pf=False):
    outdir = out + ".d"
    os.makedirs(outdir, exist_ok=True)
    cmd = [bin_path, "-D", "-a", str(atten), "-o", outdir, inp]
    if pf:
        cmd.insert(1, "--pf")
    subprocess.run(cmd, check=True, capture_output=True)
    os.replace(os.path.join(outdir, os.path.basename(inp)), out)
    os.rmdir(outdir)


def build(chain, raw, outdir, df_bin, rnnn_dir):
    pre = os.path.join(outdir, "pre.wav")
    if not os.path.exists(pre):
        ff(raw, pre, PRE)
    mid = os.path.join(outdir, f"{chain}_mid.wav")
    wpe_out = os.path.join(outdir, "wpe.wav")
    if chain in "ADE" and not os.path.exists(wpe_out):
        wpe_dereverb(pre, wpe_out)
    post = POLISH
    if chain in "AD":
        if chain == "D" and os.path.exists(os.path.join(outdir, "A_mid.wav")):
            mid = os.path.join(outdir, "A_mid.wav")
        else:
            deep_filter(df_bin, wpe_out, mid)
        if chain == "D":
            post = POLISH + "," + EXPANDER
    elif chain == "B":
        deep_filter(df_bin, pre, mid)
    elif chain == "C":
        model = os.path.join(rnnn_dir, "cb.rnnn")
        ff(pre, mid, f"arnndn=m={model}:mix=0.9,afftdn=nr=12:nf=-42:tn=1,"
                     "agate=threshold=0.02:ratio=2:range=0.25:attack=5:release=220")
    elif chain == "E":
        deep_filter(df_bin, wpe_out, mid, atten=100, pf=True)
        post = POLISH + "," + EXPANDER
    else:
        raise ValueError(chain)
    final = os.path.join(outdir, f"{chain}.wav")
    ff(mid, final, post)
    return final


# ---------------------------------------------------------------- metrics
def frames_db(x, t0, t1, win=0.02):
    a, b = int(t0 * SR), int(t1 * SR)
    seg = x[a:b]
    n = max(1, len(seg) // int(win * SR))
    seg = seg[: n * int(win * SR)].reshape(n, -1)
    return 10 * np.log10((seg ** 2).mean(1) + 1e-12)


def band_db(x, spans, lo, hi):
    w = np.hanning(4096)
    f = np.fft.rfftfreq(4096, 1 / SR)
    acc = []
    for t0, t1 in spans:
        for k in range(int(t0 * SR), int(t1 * SR) - 4096, 2048):
            acc.append(np.abs(np.fft.rfft(x[k:k + 4096] * w)) ** 2)
    if not acc:
        return np.nan, None
    P = np.mean(acc, 0)
    return 10 * np.log10(P[(f >= lo) & (f < hi)].mean() + 1e-20), P


def phrases(words, gap=0.35):
    out, cur = [], [words[0]]
    for w in words[1:]:
        if w["start"] - cur[-1]["end"] >= gap:
            out.append((cur[0]["start"], cur[-1]["end"]))
            cur = [w]
        else:
            cur.append(w)
    out.append((cur[0]["start"], cur[-1]["end"]))
    return out


def metrics(path, words, ref=None):
    x, sr = sf.read(path, dtype="float64")
    assert sr == SR
    ph = phrases(words)
    speech = [(a + 0.05, b - 0.05) for a, b in ph if b - a > 0.3]
    sp_level = np.percentile(np.concatenate([frames_db(x, a, b) for a, b in speech]), 90)
    tails, pauses = [], []
    for (a, b), (c, _) in zip(ph, ph[1:]):
        if c - b >= 0.45:
            tails.append(frames_db(x, b + 0.06, min(b + 0.30, c - 0.05)).mean())
        if c - b >= 0.7:
            pauses.append((b + 0.35, c - 0.1))
    pause_floor = np.mean([frames_db(x, a, b).mean() for a, b in pauses])
    hp, _ = band_db(x, pauses, 4000, 16000)
    hs, _ = band_db(x, speech, 4000, 16000)
    out = {
        "speech_p90_db": round(sp_level, 1),
        "pause_floor": round(pause_floor - sp_level, 1),
        "tail_level": round(float(np.mean(tails)) - sp_level, 1),
        "hiss_4_16k": round(hp - hs, 1),
    }
    if ref is not None:
        f = np.fft.rfftfreq(4096, 1 / SR)
        sel = (f >= 150) & (f < 6000)
        _, P = band_db(x, speech, 0, 1)
        _, R = band_db(ref, speech, 0, 1)
        a = 10 * np.log10(P[sel] + 1e-20)
        b = 10 * np.log10(R[sel] + 1e-20)
        a -= a.mean()
        b -= b.mean()
        out["speech_lsd"] = round(float(np.sqrt(np.mean((a - b) ** 2))), 2)
    return out


def spectrogram(path, png, t0=12.0, dur=10.0):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t0), "-t", str(dur), "-i", path,
                    "-lavfi", "showspectrumpic=s=1000x360:legend=0:scale=log:color=intensity:fscale=lin:stop=16000",
                    png], check=True)


def main(raw, transcript, outdir, df_bin, rnnn_dir, chains="ABC"):
    os.makedirs(outdir, exist_ok=True)
    words = json.load(open(transcript))["words"]
    ref, _ = sf.read(raw, dtype="float64")
    results = {"raw": metrics(raw, words)}
    spectrogram(raw, os.path.join(outdir, "spec_raw.png"))
    for c in chains:
        path = build(c, raw, outdir, df_bin, rnnn_dir)
        results[c] = metrics(path, words, ref)
        spectrogram(path, os.path.join(outdir, f"spec_{c}.png"))
    json.dump(results, open(os.path.join(outdir, "metrics.json"), "w"), indent=1)
    print(f"{'':6}{'pause_floor':>12}{'tail_level':>12}{'hiss_4_16k':>12}{'speech_lsd':>12}")
    for k, m in results.items():
        print(f"{k:6}{m['pause_floor']:>12}{m['tail_level']:>12}{m['hiss_4_16k']:>12}{m.get('speech_lsd', '-'):>12}")


if __name__ == "__main__":
    main(*sys.argv[1:])
