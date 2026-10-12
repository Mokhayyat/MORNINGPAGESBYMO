"""Hand anchors for the gesture-pinned graphics (ring on the fist, the Follow button at the pointing
finger, the heart from the hand on the chest). Skin pixels below the chin; the hand is taken as the
top 150 px of the biggest skin blob (the arm hangs below it).

Usage: python -I hand_track.py <video> <out.json> name:t0:t1 [name:t0:t1 ...]
Writes {name: [[t, x, y], ...]} in source px, lightly smoothed.
"""
import json
import subprocess
import sys

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

SW, SH = 720, 1280


def main(path, out, *wins):
    wins = [(w.split(":")[0], float(w.split(":")[1]), float(w.split(":")[2])) for w in wins]
    times = [float(f["pts_time"]) for f in json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "json", path],
        capture_output=True, text=True).stdout)["frames"]]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    res = {n: [] for n, _, _ in wins}
    i = 0
    while True:
        b = p.stdout.read(SW * SH * 3)
        if len(b) < SW * SH * 3:
            break
        t = times[i] if i < len(times) else i / 30
        i += 1
        act = [n for n, a, z in wins if a <= t <= z]
        if not act:
            continue
        fr = np.frombuffer(b, np.uint8).reshape(SH, SW, 3)
        ycc = cv2.cvtColor(fr, cv2.COLOR_BGR2YCrCb)
        m = cv2.inRange(ycc, (40, 138, 80), (245, 180, 128))
        m[:int(0.62 * SH)] = 0
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k), cv2.MORPH_CLOSE, k)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m)
        if n <= 1:
            continue
        j = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
        if st[j, cv2.CC_STAT_AREA] < 6000:
            continue
        ys, xs = np.nonzero(lab == j)
        top = ys.min()
        sel = ys < top + 150
        for name in act:
            res[name].append([round(t, 3), float(xs[sel].mean()), float(ys[sel].mean()), int(top)])
    out_d = {}
    for name, rows in res.items():
        a = np.array(rows)
        if len(a) > 3:
            a[:, 1] = gaussian_filter1d(a[:, 1], 1.5)
            a[:, 2] = gaussian_filter1d(a[:, 2], 1.5)
        out_d[name] = [[round(r[0], 3), round(r[1], 1), round(r[2], 1), int(r[3])] for r in a]
        print(name, " ".join(f"{r[0]:.2f}:({r[1]:.0f},{r[2]:.0f})" for r in out_d[name][::3]))
    json.dump(out_d, open(out, "w"))


if __name__ == "__main__":
    main(*sys.argv[1:])
