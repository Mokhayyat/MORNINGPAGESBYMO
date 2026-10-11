"""Picture pass: exposure stabilisation, blind-moire fix, warm grade, sepia flashback, light leak,
glow, smooth sub-pixel push-ins and a single Lanczos upscale 720x1280 -> 1080x1920.

Usage:
  python -I grade_upscale.py <src.mov> <beats.json> <out.mov> [--from S] [--to S] [--workers N] [--stills t1,t2 --outdir D]

Frames are decoded by ffmpeg at a constant 30 fps (BT.709, full range, as tagged by the phone), processed in
float32 RGB and written as ProRes 422 HQ (BT.709, limited range). Grain and vignette are added later, after
the overlays, so the doodles share the same film texture.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

W0, H0, W1, H1, FPS = 720, 1280, 1080, 1920, 30


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


# ------------------------------------------------------------------ helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ease(kind, p):
    p = min(max(p, 0.0), 1.0)
    if kind == "back":
        c1, c3 = 1.70158, 2.70158
        return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
    return -(math.cos(math.pi * p) - 1) / 2            # sine in-out


def zoom_at(t, segs):
    z = 1.0
    for s in segs:
        if t >= s["t1"]:
            z = s["to"]
        elif t >= s["t0"]:
            z = s["from"] + (s["to"] - s["from"]) * ease(s.get("ease", "sine"), (t - s["t0"]) / (s["t1"] - s["t0"]))
    return z


def window(t, t_in, t_out):
    """0->1 over [t_in[0], t_in[1]], 1->0 over [t_out[0], t_out[1]]."""
    a = (t - t_in[0]) / (t_in[1] - t_in[0])
    b = 1 - (t - t_out[0]) / (t_out[1] - t_out[0])
    return float(np.clip(min(a, b), 0, 1))


def to_lin(x):
    return np.power(np.clip(x, 0, 1), 2.2)


def to_gam(x):
    return np.power(np.clip(x, 0, 1), 1 / 2.2)


def luma(x):
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


# ------------------------------------------------------------------ passes
def beam_series(src, region):
    """Mean luma of the never-occluded beam for every CFR frame (fast, tiny decode)."""
    x, y, w, h = region[0], region[1], region[2] - region[0], region[3] - region[1]
    cmd = ["ffmpeg", "-v", "error", "-i", src, "-vf",
           f"fps={FPS},crop={w}:{h}:{x}:{y},scale=90:32,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, 32 * 90).mean(1).astype(np.float64)


def exposure_gains(series, cfg):
    k = int(cfg["smooth_frames"]) | 1
    pad = np.pad(series, (k // 2, k // 2), mode="edge")
    smooth = np.convolve(pad, np.ones(k) / k, mode="valid")
    target = np.median(series)
    gain = np.power(target / smooth, 2.2 * cfg["strength"])   # linear-light gain
    return np.clip(gain, 0.75, 1.4)


TONE_SH = np.array([0.014, 0.004, -0.012], np.float32)   # warm shadows
TONE_HI = np.array([0.016, 0.009, -0.012], np.float32)   # creamy highlights


def tone_luts(ae_gain):
    """Per-channel 1D LUTs (uint8 in -> float out): exposure gain + warm WB in linear light,
    highlight roll-off, gentle S-curve and matte blacks."""
    v = np.arange(256, dtype=np.float64) / 255
    lin = np.power(v, 2.2) * ae_gain
    luts = []
    for wb in (1.035, 1.0, 0.945):
        x = np.power(np.clip(lin * wb, 0, 1), 1 / 2.2)
        knee = 0.80
        x = np.where(x > knee, knee + (1 - knee) * np.tanh((x - knee) / (1 - knee) * 1.15) / np.tanh(1.15), x)
        x = x + 0.07 * (x - 0.5) * (1 - np.abs(2 * x - 1))
        luts.append((0.032 + x * (1 - 0.032)).astype(np.float32))
    return luts


def grade(src, t, g, ae_gain, band):
    """src: uint8 HxWx3 RGB at source size -> float32 graded RGB 0..1."""
    luts = tone_luts(ae_gain)
    x = np.empty(src.shape, np.float32)
    for c in range(3):
        x[..., c] = np.take(luts[c], src[..., c])

    # blind moire: neutralise chroma on the bright blind band only (rows r0:r1)
    r0, r1, wts = band
    sub = x[r0:r1]
    y = luma(sub)
    m = wts * smoothstep(0.50, 0.68, y)[..., None]
    x[r0:r1] = sub * (1 - 0.85 * m) + y[..., None] * (0.85 * m)

    # vibrance (+ more for muted pixels), split-tone warm shadows / creamy highlights
    y = luma(x)[..., None]
    sat = x.max(-1, keepdims=True) - x.min(-1, keepdims=True)
    x = y + (x - y) * (1 + 0.18 * (1 - np.clip(sat * 2.2, 0, 1)))
    x += TONE_SH * (1 - y) ** 2 + TONE_HI * y ** 2

    # sepia flashback ("growing up…")
    w = window(t, g["flashback"]["in"], g["flashback"]["out"])
    if w > 0:
        yy = luma(np.clip(x, 0, 1))[..., None]
        sep = np.concatenate([yy * 1.06 + 0.035, yy * 0.95 + 0.02, yy * 0.76 + 0.01], -1)
        sep = 0.07 + sep * 0.84                                # faded, lower contrast
        sep = cv2.GaussianBlur(sep, (0, 0), 0.7)
        x = x * (1 - w) + sep * w

    # golden light leak sweeping in as warmth returns (screen blend)
    lk = g["lightleak"]
    if lk["t0"] <= t <= lk["t1"]:
        p = (t - lk["t0"]) / (lk["t1"] - lk["t0"])
        amp = math.sin(math.pi * min(p * 1.35, 1.0)) * (1 - max(0, p - 0.74) / 0.26 if p > 0.74 else 1)
        yy, xx = np.mgrid[0:H0, 0:W0].astype(np.float32)
        cx1, cy1 = -120 + p * 980, 220 + p * 380
        cx2, cy2 = 860 - p * 520, 1180 - p * 300
        b1 = np.exp(-(((xx - cx1) / 380) ** 2 + ((yy - cy1) / 520) ** 2))[..., None] * np.array([1.0, 0.62, 0.24], np.float32)
        b2 = np.exp(-(((xx - cx2) / 300) ** 2 + ((yy - cy2) / 420) ** 2))[..., None] * np.array([1.0, 0.84, 0.46], np.float32)
        leak = np.clip((b1 * 0.62 + b2 * 0.4) * amp, 0, 1)
        x = 1 - (1 - np.clip(x, 0, 1)) * (1 - leak)

    # warm glow ("so much value")
    gl = g["glow"]
    wg = window(t, [gl["t0"], gl["t0"] + 0.45], [gl["t1"] - 0.45, gl["t1"]]) * gl["amount"]
    if wg > 0:
        bright = np.clip(x - 0.55, 0, 1) * np.array([1.0, 0.85, 0.6], np.float32)
        bloom = cv2.GaussianBlur(bright, (0, 0), 22)
        x = 1 - (1 - np.clip(x, 0, 1)) * (1 - np.clip(bloom * wg * 2.4, 0, 1))
    return np.clip(x, 0, 1)


def upscale(x, z, center):
    """Single Lanczos resample (zoom + 1.5x) in 16-bit, then a gentle unsharp mask. Returns uint16 RGB."""
    cx, cy = center
    s = 1.5 * z
    M = np.array([[1 / s, 0, cx * (1 - 1 / z)], [0, 1 / s, cy * (1 - 1 / z)]], np.float32)
    u16 = (np.clip(x, 0, 1) * 65535 + 0.5).astype(np.uint16)
    out = cv2.warpAffine(u16, M, (W1, H1), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    blur = cv2.GaussianBlur(out, (0, 0), 1.1)
    return cv2.addWeighted(out, 1.38, blur, -0.38, 0)


def moire_band(cfg):
    f = cfg["feather"]
    r0, r1 = max(0, cfg["y0"] - f), min(H0, cfg["y1"] + f)
    yy = np.arange(r0, r1, dtype=np.float32)[:, None]
    w = smoothstep(cfg["y0"] - f, cfg["y0"] + f, yy) * (1 - smoothstep(cfg["y1"] - f, cfg["y1"] + f, yy))
    return r0, r1, w[..., None].astype(np.float32)


def run_range(src, beats, out, t_from, t_to, stills, outdir):
    g = beats["grade"]
    gains = exposure_gains(beam_series(src, g["ae_stabilize"]["region"]), g["ae_stabilize"])
    band = moire_band(g["moire_fix"])
    center = (beats["zoom_center"][0] * W0, beats["zoom_center"][1] * H0)
    n_total = len(gains)
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf",
                            f"fps={FPS},hqdn3d=1.2:1.0:3:3,scale=in_color_matrix=bt709:in_range=full:out_range=full,format=rgb24",
                            "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
    enc = None
    if not stills:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W1}x{H1}",
                                "-framerate", str(FPS), "-i", "-",
                                "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le",
                                "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0",
                                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
                                out], stdin=subprocess.PIPE)
    want = {round(s_ * FPS) for s_ in stills}
    i0, i1 = round(t_from * FPS), math.ceil(t_to * FPS - 1e-6)
    frame_bytes = W0 * H0 * 3
    i = 0
    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        take = (i in want) if stills else (i0 <= i < i1)
        if take:
            t = i / FPS
            src_px = np.frombuffer(buf, np.uint8).reshape(H0, W0, 3)
            x = grade(src_px, t, g, gains[min(i, n_total - 1)], band)
            y = upscale(x, zoom_at(t, beats["zoom"]), center)
            if stills:
                cv2.imwrite(f"{outdir}/g_{t:.2f}.png", cv2.cvtColor((y >> 8).astype(np.uint8), cv2.COLOR_RGB2BGR))
            else:
                enc.stdin.write(y.tobytes())
            if i % 150 == 0:
                print(f"frame {i} t={t:.2f}s gain={gains[min(i, n_total - 1)]:.3f} z={zoom_at(t, beats['zoom']):.3f}", flush=True)
        elif not stills and i >= i1:
            break
        i += 1
    dec.stdout.close()
    dec.kill()
    if enc:
        enc.stdin.close()
        enc.wait()


def main():
    src, beats_path, out = sys.argv[1:4]
    beats = json.load(open(beats_path))
    t_from, t_to = float(arg("--from", 0)), float(arg("--to", beats["meta"]["duration"]))
    stills = [float(v) for v in arg("--stills", "").split(",") if v]
    workers = int(arg("--workers", 1))
    if stills or workers <= 1:
        run_range(src, beats, out, t_from, t_to, stills, arg("--outdir", "."))
        print(f"done -> {out if not stills else arg('--outdir', '.')}")
        return
    # split into contiguous frame ranges, render in parallel, then stitch losslessly
    i0, i1 = round(t_from * FPS), math.ceil(t_to * FPS - 1e-6)
    edges = [i0 + (i1 - i0) * k // workers for k in range(workers + 1)]
    segs, procs = [], []
    for k in range(workers):
        seg = f"{out}.part{k}.mov"
        segs.append(seg)
        procs.append(subprocess.Popen([sys.executable, "-I", __file__, src, beats_path, seg,
                                       "--from", f"{edges[k] / FPS:.6f}", "--to", f"{edges[k + 1] / FPS:.6f}"]))
    if any(p.wait() for p in procs):
        sys.exit("a worker failed")
    lst = out + ".txt"
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(sg)}'\n" for sg in segs)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    for sg in segs + [lst]:
        os.remove(sg)
    print(f"done: frames {i0}-{i1} with {workers} workers -> {out}")


if __name__ == "__main__":
    main()
