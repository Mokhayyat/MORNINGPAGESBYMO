# Morning Pages by Mo — intro Reel edit

Source for the edit of `MORNING PAGES INTRO VID.mov` (64.95 s, 720×1280, no cuts) into a warm, hand-made
1080×1920 Reel (67.65 s with the opening cover and the closing pages): cleaned-up voice, warm grade, hand-drawn animated doodles, burned-in handwritten captions,
an original lo-fi bed, sound effects, and a little Claude cameo.

Raw footage and renders are **not** in git (see `.gitignore`); everything here rebuilds them.

## What's where

| Path | What it does |
|---|---|
| `beats.json` | The single timeline: every doodle cue, sound effect, zoom, grade section and music section, in seconds on the uncut source. `meta.preroll` / `meta.postroll` add the opening-cover and closing-pages time around it (`cues.intro` is in output time). |
| `transcript.json` | Word-level transcript (Whisper large-v3-turbo). `caption` holds the word shown on screen ("irrelevant", "picking"). |
| `overlays/` | The doodle layer: one paused GSAP timeline (`scenes.js`, `captions.js`), drawn with Rough.js (`draw.js`). Open `overlays/index.html?t=48.9&preview` through a local server to scrub. |
| `scripts/transcribe.py` | Writes `transcript.json`. |
| `scripts/audio_clean.py` | Voice cleanup shoot-out. Chain **E** won: high-pass + hum notches → WPE dereverb → DeepFilterNet3 → EQ/de-ess/compression → expander. |
| `music/compose_lofi.py` | Generates the original lo-fi bed from code (76 BPM, follows the story sections in `beats.json`). |
| `scripts/output_timeline.py` | Shifts the music spec into output time (pre-roll + post-roll) for `compose_lofi.py`. |
| `scripts/build_sfx.py` | Synthesises the cartoon sound effects named `synth:*` in `beats.json`. Kenney CC0 packs supply the `k:*` ones. |
| `scripts/mix_audio.py` | Voice + ducked music + timed SFX → −14 LUFS, −1.5 dBTP. |
| `scripts/grade_upscale.py` | Exposure steadying, blind-moiré fix, warm grade, sepia flashback, light leak, glow, sub-pixel push-ins, one Lanczos upscale to 1080×1920. |
| `scripts/render_overlays.mjs` | Frame-by-frame transparent render of the doodle layer (Playwright/Chromium) → ProRes 4444. |
| `scripts/compose_final.sh` | Picture + doodles + mix → H.264 MP4 with light grain and vignette. |
| `scripts/make_textures.py` | Paper grain, old-photo creases and film dust textures in `overlays/img/`. |

## Rebuild

```bash
npm install                                   # gsap, roughjs, playwright (Chromium already present)
PY="python -I"                                # venv with faster-whisper, nara_wpe, opencv, soundfile, pyloudnorm
$PY scripts/transcribe.py SRC.mov WHISPER_MODEL_DIR transcript.json
ffmpeg -i SRC.mov -vn -ac 1 -ar 48000 -c:a pcm_f32le build/voice_raw48.wav
$PY scripts/audio_clean.py build/voice_raw48.wav transcript.json build/shootout deep-filter rnnn-models E
$PY scripts/output_timeline.py beats.json build/beats_music.json
$PY music/compose_lofi.py build/beats_music.json build/music.wav
$PY scripts/build_sfx.py beats.json build/sfx
$PY scripts/mix_audio.py beats.json build/shootout/E.wav build/music.wav build/sfx KENNEY_DIR build/mix.wav
$PY scripts/grade_upscale.py SRC.mov beats.json build/graded.mov --workers 3
node scripts/render_overlays.mjs --out build/overlays.mov
PREROLL=0.9 POSTROLL=1.8 scripts/compose_final.sh build/graded.mov build/overlays.mov build/mix.wav build/morning-pages-intro.mp4
# a <30 MB copy for sharing: PREROLL=0.9 POSTROLL=1.8 GRAIN=2 MAXRATE=3300k BUFSIZE=6600k scripts/compose_final.sh ... out.mp4 21
```

Sound effects: [Kenney](https://kenney.nl) RPG Audio, Impact Sounds and Interface Sounds (CC0), plus synthesised ones.
Fonts (OFL / Apache): Kalam, Caveat, Caveat Brush, Patrick Hand, Special Elite, Permanent Marker, Gochi Hand.
