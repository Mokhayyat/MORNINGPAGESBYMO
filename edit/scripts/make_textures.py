"""Generate the paper textures used by the overlays (deterministic).

Usage: python -I make_textures.py <overlays/img dir>

  paper.png    512x512 tileable grayscale paper grain (multiplied over card colours)
  creases.png  1080x1920 RGBA fold lines + wear for the "old photo" flashback
  dust_a.png   1080x1920 RGBA film dust/hairs (two variants, flickered at 12 fps)
  dust_b.png
"""
import os
import sys

import cv2
import numpy as np

rng = np.random.default_rng(7)


def periodic_noise(n, scale):
    """Tileable smooth noise via filtering white noise in the frequency domain."""
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.sqrt(fx ** 2 + fy ** 2)
    spec = np.fft.fft2(rng.standard_normal((n, n))) * np.exp(-(r * scale) ** 2)
    out = np.real(np.fft.ifft2(spec))
    return (out - out.mean()) / (out.std() + 1e-9)


def paper(n=512):
    base = 0.955 + 0.018 * periodic_noise(n, 40) + 0.010 * periodic_noise(n, 8)
    fibers = np.zeros((n * 3, n * 3), np.float32)        # draw on a 3x3 canvas, fold back for tiling
    for _ in range(900):
        x, y = rng.uniform(n, 2 * n, 2)
        ang = rng.uniform(0, np.pi)
        ln = rng.uniform(6, 26)
        dx, dy = np.cos(ang) * ln, np.sin(ang) * ln
        cv2.line(fibers, (int(x), int(y)), (int(x + dx), int(y + dy)), float(rng.uniform(0.3, 1.0)), 1, cv2.LINE_AA)
    folded = sum(fibers[i * n:(i + 1) * n, j * n:(j + 1) * n] for i in range(3) for j in range(3))
    speck = (rng.random((n, n)) > 0.9985).astype(np.float32)
    speck = cv2.GaussianBlur(speck, (3, 3), 0.7)
    img = base - 0.035 * folded - 0.25 * speck
    return np.clip(img * 255, 0, 255).astype(np.uint8)


def creases(w=1080, h=1920):
    rgba = np.zeros((h, w, 4), np.float32)
    lines = [((0, 640), (1080, 700)), ((380, 0), (300, 1920)), ((0, 1500), (1080, 1380)), ((760, 0), (840, 1920))]
    for (x0, y0), (x1, y1) in lines:
        dark = np.zeros((h, w), np.float32)
        lite = np.zeros((h, w), np.float32)
        cv2.line(dark, (x0, y0), (x1, y1), 1.0, 3, cv2.LINE_AA)
        cv2.line(lite, (x0 + 3, y0 + 3), (x1 + 3, y1 + 3), 1.0, 2, cv2.LINE_AA)
        dark = cv2.GaussianBlur(dark, (0, 0), 1.6)
        lite = cv2.GaussianBlur(lite, (0, 0), 1.2)
        rgba[..., :3] += lite[..., None] * 255
        rgba[..., 3] += lite * 0.22 + dark * 0.18
        rgba[..., :3] = np.where(dark[..., None] > lite[..., None], 60, rgba[..., :3])
    # soft edge wear
    wear = np.clip(periodic_noise(512, 30), -3, 3)
    wear = cv2.resize(wear.astype(np.float32), (w, h))
    edge = np.minimum.reduce([np.arange(w)[None, :].repeat(h, 0), np.arange(w)[::-1][None, :].repeat(h, 0),
                              np.arange(h)[:, None].repeat(w, 1), np.arange(h)[::-1][:, None].repeat(w, 1)]).astype(np.float32)
    ew = np.clip(1 - edge / 160, 0, 1) * np.clip(0.5 + 0.25 * wear, 0, 1)
    rgba[..., :3] = rgba[..., :3] * (1 - ew[..., None]) + np.array([235, 222, 196]) * ew[..., None]
    rgba[..., 3] = np.maximum(rgba[..., 3], ew * 0.35)
    return np.clip(rgba, 0, 255).astype(np.uint8)


def dust(w=1080, h=1920, seed=0):
    r = np.random.default_rng(100 + seed)
    a = np.zeros((h, w), np.float32)
    for _ in range(140):                                  # specks
        cv2.circle(a, (int(r.uniform(0, w)), int(r.uniform(0, h))), int(r.integers(1, 4)), float(r.uniform(0.3, 0.9)), -1, cv2.LINE_AA)
    for _ in range(9):                                    # hairs
        pts = np.cumsum(r.normal(0, 6, (14, 2)), 0) + r.uniform([0, 0], [w, h])
        cv2.polylines(a, [pts.astype(np.int32)], False, float(r.uniform(0.4, 0.8)), 1, cv2.LINE_AA)
    x = int(r.uniform(80, w - 80))                        # one vertical scratch
    cv2.line(a, (x, 0), (x + int(r.uniform(-30, 30)), h), 0.35, 1, cv2.LINE_AA)
    rgba = np.zeros((h, w, 4), np.uint8)
    rgba[..., :3] = 40
    rgba[..., 3] = np.clip(a * 200, 0, 255).astype(np.uint8)
    return rgba


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    cv2.imwrite(os.path.join(outdir, "paper.png"), paper())
    c = creases()
    cv2.imwrite(os.path.join(outdir, "creases.png"), cv2.cvtColor(c, cv2.COLOR_RGBA2BGRA))
    for i, name in enumerate(("dust_a.png", "dust_b.png")):
        cv2.imwrite(os.path.join(outdir, name), cv2.cvtColor(dust(seed=i), cv2.COLOR_RGBA2BGRA))
    print("textures ->", outdir)


if __name__ == "__main__":
    main(sys.argv[1])
