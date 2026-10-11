"""Transcribe the source video with word-level timestamps.

Usage: python -I transcribe.py <video> <whisper_model_dir> <out.json>

Audio is decoded with PyAV and passed to faster-whisper as a numpy array
(faster-whisper's own decoder doesn't work with PyAV 19).
"""
import json
import sys

import av
import numpy as np
from faster_whisper import WhisperModel

# Words Mo meant, used for captions (the audio itself is untouched).
CAPTION_FIXES = {28.88: "irrelevant", 40.16: "picking"}


def decode_16k_mono(path):
    container = av.open(path)
    resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
    chunks = []
    for frame in container.decode(container.streams.audio[0]):
        chunks += [o.to_ndarray().reshape(-1) for o in resampler.resample(frame)]
    chunks += [o.to_ndarray().reshape(-1) for o in resampler.resample(None)]
    container.close()
    return np.concatenate(chunks).astype(np.float32)


def main(video, model_dir, out_path):
    model = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=4)
    segments, info = model.transcribe(
        decode_16k_mono(video),
        word_timestamps=True,
        beam_size=5,
        vad_filter=False,
        condition_on_previous_text=False,
        initial_prompt="Morning Pages by Mo. Claude.",
    )
    words, segs = [], []
    for s in segments:
        segs.append({"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()})
        for w in s.words:
            heard = w.word.strip()
            fix = next((v for t, v in CAPTION_FIXES.items() if abs(w.start - t) < 0.05), None)
            words.append({
                "start": round(w.start, 2),
                "end": round(w.end, 2),
                "word": heard,
                "caption": fix + heard[len(heard.rstrip(".,!?")):] if fix else heard,
                "p": round(w.probability, 3),
            })
    with open(out_path, "w") as f:
        json.dump({"language": info.language, "duration": round(info.duration, 3),
                   "segments": segs, "words": words}, f, indent=1)
    print(f"{len(words)} words, {len(segs)} segments -> {out_path}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
