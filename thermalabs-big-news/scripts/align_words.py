"""Exact word timings by CTC forced alignment (torchaudio wav2vec2, English), on the cleaned voice.

Whisper's own word times drift up to ~0.3 s early at the start of a sentence, which is too loose for
captions and pop-ins timed to a word. The words come from the Whisper transcript; only the timing
is replaced.

Usage: python -I align_words.py <whisper.json> <voice.wav> <out transcript.json>
"""
import json
import re
import sys

import numpy as np
import soundfile as sf
import torch
import torchaudio
import torchaudio.functional as F
from scipy.signal import resample_poly


def main(whisper_p, voice_p, out_p):
    wj = json.load(open(whisper_p))
    words = [w["word"] for w in wj["words"]]
    x, sr = sf.read(voice_p, dtype="float32")
    if x.ndim > 1:
        x = x.mean(1)
    x = resample_poly(x, 16000, sr).astype(np.float32)
    bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
    model = bundle.get_model().eval()
    labels = bundle.get_labels()
    lut = {c: i for i, c in enumerate(labels)}
    with torch.inference_mode():
        em, _ = model(torch.from_numpy(x)[None])
        em = torch.log_softmax(em, dim=-1)
    sec_per_frame = len(x) / 16000 / em.shape[1]
    clean = [re.sub(r"[^A-Z']", "", w.upper()) for w in words]
    tokens = [lut[c] for c in "|".join(clean)]
    ali, scores = F.forced_align(em, torch.tensor([tokens], dtype=torch.int32), blank=0)
    spans = F.merge_tokens(ali[0], scores[0].exp())
    # spans are per character token (no blanks); '|' separators delimit words
    out, i = [], 0
    for wi, cw in enumerate(clean):
        chars = []
        for _ in cw:
            while labels[spans[i].token] == "|":
                i += 1
            chars.append(spans[i])
            i += 1
        s, e = chars[0].start * sec_per_frame, chars[-1].end * sec_per_frame
        conf = float(np.mean([c.score for c in chars]))
        out.append({"start": round(s, 3), "end": round(e, 3), "word": words[wi],
                    "whisper_start": wj["words"][wi]["start"], "conf": round(conf, 3)})
    json.dump({"duration": wj["duration"], "source": "align_words.py (wav2vec2 base 960h CTC)",
               "words": out}, open(out_p, "w"), indent=1)
    for w in out:
        print(f"{w['start']:6.2f}-{w['end']:6.2f}  (whisper {w['whisper_start']:5.2f})  conf {w['conf']:.2f}  {w['word']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
