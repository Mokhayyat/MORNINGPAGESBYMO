"""Write the music spec in output time for compose_lofi.py.

beats.json keeps every cue on the source timeline. The output adds a pre-roll (the opening cover turns while
the first frame is held) and a post-roll (the pages and cover close over the last frame). This shifts the
music sections by the pre-roll and stretches the last one to the end, so the music plays under both.

Usage: python -I output_timeline.py <beats.json> <beats_music.json>
"""
import json
import sys


def main(src, out):
    b = json.load(open(src))
    pre, post, dur = b["meta"].get("preroll", 0), b["meta"].get("postroll", 0), b["meta"]["duration"]
    m = b["music"]
    m["grid_anchor"] += pre
    secs = sorted(m["sections"], key=lambda s: s["t0"])
    for i, s in enumerate(secs):
        s["t0"] = 0.0 if i == 0 else round(s["t0"] + pre, 6)
        s["t1"] = round(s["t1"] + pre, 6)
        for key in ("glock_sting", "final_chord"):
            if s.get(key) is not None:
                s[key] = round(s[key] + pre, 6)
    secs[-1]["t1"] = round(pre + dur + post, 6)
    m["sections"] = secs
    b["meta"]["duration"] = round(pre + dur + post, 6)
    b["meta"]["preroll"] = b["meta"]["postroll"] = 0
    json.dump(b, open(out, "w"), indent=1)
    print(f"music spec in output time: {b['meta']['duration']} s (pre-roll {pre}, post-roll {post}) -> {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
