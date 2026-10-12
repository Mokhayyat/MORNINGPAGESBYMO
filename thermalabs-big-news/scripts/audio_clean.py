"""Voice cleanup for the walking clip: wind/footstep rumble out, street noise down, voice polished.

Usage:
  python -I audio_clean.py <raw48.wav> <deep-filter-bin> <out.wav> [atten_db=28]

Chain: 4th-order high-pass at 85 Hz + rumble shelf -> DeepFilterNet3 (attenuation limited, so a little
outdoor air stays and nothing sounds underwater) -> presence/de-ess/compression polish -> gentle
expander so the pauses are clean -> limiter. Prints the noise floor in the pauses before and after.
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
PRE = ("highpass=f=85:poles=2,highpass=f=85:poles=2,"
       "equalizer=f=110:t=q:w=1.2:g=-3,"            # leftover handling thump
       "lowshelf=f=140:g=-2")
POLISH = ("equalizer=f=320:t=q:w=1.0:g=-1.5,"       # a touch less chesty (phone held low)
          "equalizer=f=3600:t=q:w=0.9:g=2.5,"      # presence
          "equalizer=f=9500:t=q:w=0.8:g=1.5,"      # air after denoising
          "deesser=i=0.4:m=0.5:f=0.5,"
          "acompressor=threshold=-20dB:ratio=2.8:attack=6:release=140:makeup=2:knee=4,"
          "agate=threshold=0.012:ratio=2:range=0.25:attack=4:release=220:knee=3:detection=rms,"
          "alimiter=limit=0.89:attack=3:release=60:level=false")


def ff(inp, out, af):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", inp, "-af", af, "-ar", str(SR), "-ac", "1",
                    "-c:a", "pcm_f32le", out], check=True)


def floor_db(path):
    """Median speech-band level of the quietest 15% of 20 ms frames (the pauses), and of the loudest 50%."""
    x, sr = sf.read(path)
    y = sosfilt(butter(4, [150, 6000], "band", fs=sr, output="sos"), x)
    hop = int(0.02 * sr)
    e = np.array([np.sqrt(np.mean(y[i:i + hop] ** 2)) for i in range(int(0.45 * sr), len(y) - hop, hop)])
    d = 20 * np.log10(e + 1e-9)
    q = np.sort(d)
    return np.median(q[: len(q) * 15 // 100]), np.median(q[len(q) // 2:])


def main(raw, df_bin, out, atten="28"):
    with tempfile.TemporaryDirectory() as tmp:
        pre = os.path.join(tmp, "pre.wav")
        ff(raw, pre, PRE)
        subprocess.run([df_bin, "-D", "-a", str(atten), "-o", tmp + "/df", pre], check=True, capture_output=True)
        ff(os.path.join(tmp, "df", "pre.wav"), out, POLISH)
    for name, p in (("raw", raw), ("clean", out)):
        f, s = floor_db(p)
        print(f"{name:5s} pause floor {f:6.1f} dB   speech {s:6.1f} dB   gap {s - f:5.1f} dB")


if __name__ == "__main__":
    main(*sys.argv[1:])
