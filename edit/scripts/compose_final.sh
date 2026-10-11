#!/usr/bin/env bash
# Final composite: graded picture + hand-drawn overlays (alpha) + mixed audio,
# blended in 10-bit YUV 4:4:4 (both layers are BT.709 limited range), then a light film grain + soft vignette over everything so the doodles share the same texture.
#
# PREROLL / POSTROLL (seconds, from beats.json meta) hold the first / last graded frame under the opening cover
# and the closing pages.
# Usage: [PREROLL=0.9 POSTROLL=1.8 PRESET=slow GRAIN=4 MAXRATE=10M] compose_final.sh <graded.mov> <overlays.mov> <mix.wav> <out.mp4> [crf=18] [scale=1080]
set -euo pipefail
GRADED="$1"; OVER="$2"; MIX="$3"; OUT="$4"; CRF="${5:-18}"; WIDTH="${6:-1080}"
HEIGHT=$(( WIDTH * 16 / 9 ))

ffmpeg -v error -stats -y \
  -i "$GRADED" -i "$OVER" -i "$MIX" \
  -filter_complex "\
[0:v]tpad=start_duration=${PREROLL:-0}:start_mode=clone:stop_duration=${POSTROLL:-0}:stop_mode=clone,format=yuv444p10le[bg];\
[1:v]format=yuva444p10le[fg];\
[bg][fg]overlay=format=yuv444p10:shortest=1,\
scale=${WIDTH}:${HEIGHT}:flags=lanczos,format=yuv420p,\
noise=c0s=${GRAIN:-4}:c0f=t,vignette=angle=PI/5.5[v]" \
  -map "[v]" -map 2:a \
  -c:v libx264 -preset "${PRESET:-slow}" -crf "$CRF" -maxrate "${MAXRATE:-10M}" -bufsize "${BUFSIZE:-20M}" -profile:v high -pix_fmt yuv420p -r 30 \
  -x264-params "aq-mode=3:deblock=-1,-1" \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 256k -ar 48000 -ac 2 \
  -movflags +faststart -shortest "$OUT"
