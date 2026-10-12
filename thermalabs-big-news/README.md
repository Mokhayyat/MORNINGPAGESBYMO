# ThermaLabs: "big news" Reel edit

Source for the edit of `F1A1961F-CB49-4EF0-9575-991474E12649.mp4` (21.1 s, 720×1280, Mo walking and
announcing a new technical expert) into a 1080×1920 Reel in the house style of the BREEZE challenge
reels. There are two versions from the same timeline:

| Version | What's different | Length |
|---|---|---|
| `tight` | pauses and "Other than that," removed, hard punch-in cuts | 20.2 s |
| `onetake` | no cuts at all, smooth push-ins instead of punch-ins | 22.4 s |

Both open on a red edge glow, a **BIG NEWS.** sticker and hazard tape; then an upgrade bar that sticks at
99 %, the ThermaLabs ID badge with the name blacked out and a SIGNING SOON stamp, three credential
chips with the hologram jacket, the Follow button tapped at Mo's pointing finger, "Guess who? Comment
below", the challenge URL pill, polaroids from the earlier reels, a heart, the cyan ring on the fist,
frost, the ice crack on "icy", and the frosted BREEZE end card.

Raw footage and renders are **not** in git (see `.gitignore`); everything here rebuilds them.

## What's where

| Path | What it does |
|---|---|
| `timeline.json` | The single timeline: each version's kept segments and zoom moves, caption chunks, every graphic cue and sound effect, in seconds on the uncut source. |
| `transcript.json` | Word timings by forced alignment (`scripts/align_words.py`); Whisper's own times ran up to 0.3 s early. |
| `scripts/edl.py` | Source ↔ output time for a version, and the zoom curve. Shared by the picture, pad and mix scripts. |
| `scripts/face_track.py` | Optical-flow face track used to steady the walk (only the fast wobble is removed). |
| `scripts/hand_track.py` | Hand anchors: the pointing finger (Follow button), hand on chest (heart), fist (ring, ice crack). |
| `scripts/picture.py` | Steadying, one Lanczos upscale with the zoom moves folded in, gentle grade, cold frost and blurred end-card backdrop. Writes per-frame mapping + frost progress for the overlays. |
| `overlays/` | The graphics layer: one paused GSAP timeline (`scenes.js`, `captions.js`), frost and ice crack (`frost.js`). Open `overlays/index.html?v=tight&t=4.3&preview` through a local server to scrub. |
| `scripts/render_overlays.mjs` | Frame-by-frame transparent render of the overlays (Playwright/Chromium) → ProRes 4444. |
| `scripts/audio_clean.py` | Wind/footstep rumble out, DeepFilterNet3 noise reduction, voice polish. |
| `scripts/build_sfx.py` | Synthesises every sound effect (no samples). |
| `scripts/compose_pad.py` | Original quiet pad in F# major, in each version's output time. |
| `scripts/mix_audio.py` | Voice cut to the version + ducked pad + SFX → −14 LUFS, ≤ −1.5 dBTP. |
| `scripts/compose_final.sh` | Picture + overlays + mix → H.264 MP4. |

## Rebuild

```bash
npm install                                    # gsap, playwright, @fontsource/inter, @fontsource/unbounded
PY="python -I"                                 # venv with faster-whisper, torch+torchaudio, opencv<5, scipy, soundfile, pyloudnorm
SRC=path/to/F1A1961F-CB49-4EF0-9575-991474E12649.mp4
mkdir -p build/sfx build/tight build/onetake
ffmpeg -i $SRC -vn -ac 1 -ar 48000 -c:a pcm_f32le build/raw48.wav
$PY scripts/audio_clean.py build/raw48.wav DEEP_FILTER_BIN build/voice_clean.wav 28
# transcript.json: Whisper large-v3-turbo words, then
$PY scripts/align_words.py whisper.json build/voice_clean.wav transcript.json
$PY scripts/face_track.py $SRC build/face_track.json
$PY scripts/hand_track.py $SRC build/hands.json point:9.75:10.75 chest:18.25:19.05 fist:19.30:21.11
$PY scripts/build_sfx.py timeline.json build/sfx
for v in tight onetake; do
  $PY scripts/picture.py timeline.json $v $SRC build/face_track.json build/$v/picture.mov
  $PY scripts/compose_pad.py timeline.json $v build/$v/pad.wav
  $PY scripts/mix_audio.py timeline.json $v build/voice_clean.wav build/$v/pad.wav build/sfx build/$v/mix.wav
  node scripts/render_overlays.mjs --v $v --out build/$v/overlays.mov
  scripts/compose_final.sh build/$v/picture.mov build/$v/overlays.mov build/$v/mix.wav build/thermalabs-big-news-$v.mp4
done
```

DEEP_FILTER_BIN is the DeepFilterNet 0.5.6 command-line build from its GitHub releases.

## Credits

Fonts: Inter and Unbounded (OFL, via Fontsource). Line icons follow Lucide (ISC). The BREEZE mark and the
garment wireframe are from thermalabs.io. Sound effects and the pad are generated in code. The polaroid
stills come from Mo's earlier reels.
