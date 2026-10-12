"""Shared timeline logic: source time <-> output time for each version, and the zoom curve.

Everything in timeline.json is written in seconds on the uncut source. A version keeps a list of
source segments; output time runs through them back to back, then the end card (meta.end_card) holds
the last source frame. A source time that falls in a removed gap snaps to the start of the next kept
segment.
"""
import json


def load(path):
    return json.load(open(path))


def per_version(value, version):
    """A cue value may be a plain number or {"tight": .., "onetake": ..}."""
    return value[version] if isinstance(value, dict) else value


class Version:
    def __init__(self, tl, name):
        self.tl, self.name = tl, name
        v = tl["versions"][name]
        self.segments = [tuple(s) for s in v["segments"]]
        self.starts = []
        acc = 0.0
        for a, b in self.segments:
            self.starts.append(acc)
            acc += b - a
        self.src_len = acc                       # output time at which the end card starts
        self.duration = acc + tl["meta"]["end_card"]
        self.fps = tl["meta"]["fps"]
        self.n_frames = int(round(self.duration * self.fps))

    def out(self, src):
        """Source time -> output time (gaps snap forward; past the end runs on into the end card)."""
        for (a, b), o in zip(self.segments, self.starts):
            if src < a:
                return o
            if src <= b:
                return o + (src - a)
        return self.src_len + (src - self.segments[-1][1])

    def kept(self, src):
        return any(a <= src <= b for a, b in self.segments)

    def src(self, out):
        """Output time -> source time (the end card holds the last source moment)."""
        for (a, b), o in zip(self.segments, self.starts):
            if out < o + (b - a):
                return a + (out - o)
        return self.segments[-1][1]

    def cue_out(self, cue):
        """A zoom / sfx entry: {"t": src} or {"out_end": seconds after the end card starts}."""
        if "out_end" in cue:
            return self.src_len + cue["out_end"]
        return self.out(cue["t"])

    def cuts(self):
        """Output times of the hard cuts (segment joins)."""
        return self.starts[1:]

    def zoom_curve(self):
        """Per output frame zoom (before base_zoom). Hard keys jump, eased keys glide from wherever the
        curve is; between keys a slow drift adds a gentle push-in."""
        drift = self.tl.get("drift_per_s", 0.0)
        keys = sorted(((self.cue_out(k), i, k) for i, k in enumerate(self.tl["versions"][self.name]["zoom"])),
                      key=lambda x: (x[0], x[1]))
        z_hold, hold_t, ease, cur = 1.0, 0.0, None, 1.0
        out, ki = [], 0
        for f in range(self.n_frames):
            t = f / self.fps
            while ki < len(keys) and keys[ki][0] <= t + 1e-6:
                t0, _, k = keys[ki]
                if "ease" in k:
                    ease = (t0, k["ease"], cur, k["z"])
                else:
                    ease, z_hold, hold_t, cur = None, k["z"], t0, k["z"]
                ki += 1
            if ease:
                t0, d, a, b = ease
                u = min(1.0, max(0.0, (t - t0) / d))
                e = 1 - (1 - u) ** 3 if d <= 0.3 else (4 * u ** 3 if u < 0.5 else 1 - (-2 * u + 2) ** 3 / 2)
                z = a + (b - a) * e
                if u >= 1.0:
                    ease, z_hold, hold_t = None, b, t0 + d
            else:
                z = z_hold * (1 + drift * (t - hold_t))
            out.append(z)
            cur = z
        return out


def ease_check():
    tl = load(__file__.rsplit("/scripts/", 1)[0] + "/timeline.json")
    for name in tl["versions"]:
        v = Version(tl, name)
        zc = v.zoom_curve()
        print(f"{name}: src {v.src_len:.2f}s + end card = {v.duration:.2f}s, {v.n_frames} frames, "
              f"cuts at {[round(c, 2) for c in v.cuts()]}, zoom {min(zc):.3f}-{max(zc):.3f}")
        for s in (0.40, 0.78, 3.98, 9.71, 13.31, 18.10, 20.75, 21.10):
            print(f"   src {s:5.2f} -> out {v.out(s):6.3f} -> src {v.src(v.out(s)):6.3f}")


if __name__ == "__main__":
    ease_check()
