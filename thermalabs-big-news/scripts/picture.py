"""Picture pass for one version: steady the walk, one Lanczos upscale to 1080x1920 (with the zoom moves
folded into the same resample), gentle grade, and the cold frosted ending under the end card.

Usage: python -I picture.py <timeline.json> <version> <source.mp4> <face_track.json> <out.mov>

Writes <out.mov> (ProRes 422 HQ, BT.709) and <out>_frames.json with, for every output frame, the
source frame used, the source->output mapping (out = (src - [tx, ty]) * k) and the frost progress,
so the overlay layer can pin things to a hand and grow its frost in step with the grade.

Steadying: the face is followed with optical flow; only the fast wobble (track minus a 4-frame
Gaussian of itself) is removed, so the walk keeps its sway. Zoom moves pivot on the smoothed face,
so punch-ins never push the face out of the upper middle of the frame.
"""
import json
import os
import subprocess
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, os.path.dirname(__file__))
from edl import Version, load  # noqa: E402

OW, OH = 1080, 1920
SW, SH = 720, 1280
C0 = np.array([360.0, 640.0])          # source point that sits at the output centre at zoom 1
O = np.array([OW / 2, OH / 2])


def decode(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-fps_mode", "passthrough",
                          "-vf", "scale=in_color_matrix=bt709:in_range=full,format=rgb24",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        b = p.stdout.read(SW * SH * 3)
        if len(b) < SW * SH * 3:
            break
        out.append(np.frombuffer(b, np.uint8).reshape(SH, SW, 3))
    return out


def smoothstep(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def grade(img):
    """img float32 RGB 0..1 (display-referred). Gentle: protect the sky, a little contrast, cool highs."""
    luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    # highlight roll-off on luminance (keeps hue), knee at 0.78
    knee = 0.78
    over = np.maximum(luma - knee, 0)
    new_l = np.where(luma > knee, knee + over / (1 + over / (1.02 - knee)) * 0.98, luma)
    img = img * ((new_l + 1e-4) / (luma + 1e-4))[..., None]
    # soft S-curve
    s = img * img * (3 - 2 * img)
    img = img + (s - img) * 0.16
    # saturation +6 %
    luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    img = luma[..., None] + (img - luma[..., None]) * 1.06
    # cool the highlights a touch (the brand is icy), leave skin and shadows alone
    hl = smoothstep(0.55, 1.0, luma)[..., None]
    img = img * (1 + hl * np.array([-0.025, 0.0, 0.02], np.float32))
    return np.clip(img, 0, 1)


def sharpen(img, amount):
    luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    detail = luma - cv2.GaussianBlur(luma, (0, 0), 1.1)
    detail = np.clip(detail, -0.08, 0.08)
    return np.clip(img + amount * detail[..., None], 0, 1)


def main(tl_path, name, src_path, track_path, out_path):
    tl = load(tl_path)
    v = Version(tl, name)
    meta = tl["meta"]
    base = meta["base_zoom"]
    s0 = 1.5 * base

    tr = json.load(open(track_path))
    track = np.array(tr["track"])                         # t, x, y (accumulated flow)
    times = track[:, 0]
    F = track[:, 1:3]
    sig = meta.get("steady_sigma_frames", 4)
    D = F - np.stack([gaussian_filter1d(F[:, 0], sig), gaussian_filter1d(F[:, 1], sig)], 1)
    haar = np.array(tr["haar"])                           # frame, cx, cy, w
    hx = np.interp(np.arange(len(times)), haar[:, 0], haar[:, 1])
    hy = np.interp(np.arange(len(times)), haar[:, 0], haar[:, 2])
    Pv = np.stack([gaussian_filter1d(hx, 15), gaussian_filter1d(hy, 15)], 1)   # slow face position

    frames = decode(src_path)
    n_src = min(len(frames), len(times))
    zc = v.zoom_curve()

    # frost: progress 0 -> 1 from the frost cue to 0.6 s into the end card; blur from the crack
    t_frost = v.out(tl["cues"]["frost"]["in"])
    t_crack = v.out(tl["cues"]["crack"]["at"])
    t_full = v.src_len + 0.6
    yy, xx = np.mgrid[0:OH, 0:OW].astype(np.float32)
    # rounded, slightly uneven edge distance (1 at the edges, 0 in the middle) so the cold creeps in
    # like frost on glass rather than as a rectangle
    u, w = (xx - OW / 2) / (OW / 2), (yy - OH * 0.46) / (OH * 0.54)
    sup = (np.abs(u) ** 3.2 + np.abs(w) ** 3.2) ** (1 / 3.2)
    noise = cv2.GaussianBlur(np.random.default_rng(3).random((OH, OW)).astype(np.float32), (0, 0), 70)
    noise = (noise - noise.mean()) / (noise.std() + 1e-6)
    edge_n = sup + 0.07 * noise

    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb48le",
                           "-s", f"{OW}x{OH}", "-r", str(v.fps), "-i", "-",
                           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv422p10le",
                           "-c:v", "prores_ks", "-profile:v", "3", "-vendor", "apl0",
                           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                           "-color_range", "tv", out_path], stdin=subprocess.PIPE)
    info = []
    for i in range(v.n_frames):
        t = i / v.fps
        ts = v.src(t)
        f = int(np.clip(np.searchsorted(times, ts + 0.5 / v.fps) - 1, 0, n_src - 1))
        z = zc[i]
        k = s0 * z
        Pf, Df = Pv[f], D[f]
        Q = (Pf - C0) * s0 + O                              # where the slow face position sits on screen
        tvec = Pf + Df - Q / k                              # out = (src - tvec) * k
        # keep the crop inside the source
        lo = tvec
        hi = tvec + np.array([OW, OH]) / k
        shift = np.where(lo < 0, -lo, 0) + np.where(hi > [SW, SH], [SW, SH] - hi, 0)
        tvec = tvec + shift
        M = np.array([[1 / k, 0, tvec[0]], [0, 1 / k, tvec[1]]], np.float32)
        img = cv2.warpAffine(frames[f], M, (OW, OH), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REFLECT)
        img = img.astype(np.float32) / 255.0
        img = grade(img)
        img = sharpen(img, 0.30 + 0.9 * (k / 1.5 - 1))      # more detail recovery the further we zoom

        # cold frosted ending
        p = float(np.clip((t - t_frost) / max(t_full - t_frost, 1e-3), 0, 1) ** 1.15) if t >= t_frost else 0.0
        if p > 0:
            m = np.clip((edge_n - (1 - p * 1.15)) / 0.30, 0, 1)[..., None] * 0.85
            luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            cold = luma[..., None] * np.array([0.72, 0.86, 1.0], np.float32) * 0.80
            img = img * (1 - m) + cold * m
        b = float(np.clip((t - t_crack) / max(v.src_len + 0.3 - t_crack, 1e-3), 0, 1)) if t >= t_crack else 0.0
        if b > 0:
            sigma = 1 + 21 * b * b
            if sigma > 6:      # big blurs at quarter size: same look, far faster
                small = cv2.resize(img, (OW // 4, OH // 4), interpolation=cv2.INTER_AREA)
                img = cv2.resize(cv2.GaussianBlur(small, (0, 0), sigma / 4), (OW, OH), interpolation=cv2.INTER_CUBIC)
            else:
                img = cv2.GaussianBlur(img, (0, 0), sigma)
            # end card backdrop: darker, cold, so white and cyan type read on a bright sky
            dark = smoothstep(0.35, 1.0, b)
            luma = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
            tint = luma[..., None] * np.array([0.55, 0.68, 0.82], np.float32) * 0.62 + np.array([0.01, 0.03, 0.05], np.float32)
            img = img * (1 - dark) + tint * dark

        ff.stdin.write((np.clip(img, 0, 1) * 65535 + 0.5).astype("<u2").tobytes())
        info.append({"f": f, "ts": round(float(ts), 4), "k": round(float(k), 5),
                     "tx": round(float(tvec[0]), 3), "ty": round(float(tvec[1]), 3),
                     "frost": round(p, 4), "blur": round(b, 4)})
        if i % 120 == 0:
            print(f"{name}: frame {i}/{v.n_frames}  src {ts:5.2f}s  zoom {z:.3f}  shift {shift.round(1).tolist()}", flush=True)
    ff.stdin.close()
    ff.wait()
    json.dump({"version": name, "fps": v.fps, "duration": v.duration, "src_len": v.src_len,
               "cuts": v.cuts(), "frames": info}, open(os.path.splitext(out_path)[0] + "_frames.json", "w"))
    print(f"{name}: {v.n_frames} frames -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:6])
