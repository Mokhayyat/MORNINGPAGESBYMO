"""Face track for steadying the walk: Lucas-Kanade flow on features inside the face, re-seeded from a
Haar detection every 15 frames, accumulated into a per-frame face position (source px).

Only the fast wobble is removed later (raw track minus its smoothed self), so slow drift in the
accumulated flow does not matter.

Usage: python -I face_track.py <video> <out.json>
"""
import json
import subprocess
import sys

import cv2
import numpy as np


def frames(path):
    W, H = 720, 1280
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         stdout=subprocess.PIPE)
    while True:
        b = p.stdout.read(W * H)
        if len(b) < W * H:
            break
        yield np.frombuffer(b, np.uint8).reshape(H, W)


def main(path, out):
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    pts_t = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=pts_time", "-of", "json", path],
        capture_output=True, text=True).stdout)["frames"]
    times = [float(f["pts_time"]) for f in pts_t]
    prev, pts, pos, track, box, haar = None, None, np.zeros(2), [], None, []
    for i, g in enumerate(frames(path)):
        fs = casc.detectMultiScale(cv2.resize(g, (360, 640)), 1.1, 6, minSize=(100, 100))
        det = None
        if len(fs):
            det = max(fs, key=lambda f: f[2] * f[3]) * 2
            haar.append([i, round(float(det[0] + det[2] / 2), 1), round(float(det[1] + det[3] / 2), 1), int(det[2])])
        if i % 15 == 0 or pts is None or len(pts) < 12:
            if det is not None:
                box = det
                if i == 0:
                    pos = np.array([box[0] + box[2] / 2, box[1] + box[3] / 2], float)
            if box is not None:
                x, y, w, h = box
                m = np.zeros_like(g)
                m[y + h // 6:y + h * 2 // 3, x + w // 6:x + w * 5 // 6] = 255   # brows, eyes, nose; not the mouth
                pts = cv2.goodFeaturesToTrack(g, 120, 0.01, 6, mask=m)
        if prev is not None and pts is not None and len(pts):
            nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, winSize=(25, 25), maxLevel=3)
            ok = st.ravel() == 1
            if ok.sum() >= 8:
                d = (nxt[ok] - pts[ok]).reshape(-1, 2)
                pos = pos + np.median(d, axis=0)
                pts = nxt[ok].reshape(-1, 1, 2)
        track.append([round(times[i] if i < len(times) else i / 30, 4), round(float(pos[0]), 2), round(float(pos[1]), 2)])
        prev = g
    json.dump({"note": "track: t, face x, face y (source px, accumulated LK flow); haar: frame, cx, cy, width",
               "track": track, "haar": haar}, open(out, "w"))
    a = np.array(track)
    from scipy.ndimage import gaussian_filter1d
    for sig in (3, 5, 8):
        dx = a[:, 1] - gaussian_filter1d(a[:, 1], sig)
        dy = a[:, 2] - gaussian_filter1d(a[:, 2], sig)
        print(f"sigma {sig}: wobble x p95 {np.percentile(np.abs(dx), 95):5.1f} max {np.abs(dx).max():5.1f} | "
              f"y p95 {np.percentile(np.abs(dy), 95):5.1f} max {np.abs(dy).max():5.1f}  (source px)")
    print(f"{len(track)} frames, x range {a[:,1].min():.0f}-{a[:,1].max():.0f}, y range {a[:,2].min():.0f}-{a[:,2].max():.0f}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
