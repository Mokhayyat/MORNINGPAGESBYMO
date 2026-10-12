#!/usr/bin/env bash
# Final composite: graded picture + overlay layer (alpha) + mix, blended in 10-bit 4:4:4 (both layers
# BT.709 limited range), a whisper of grain so the upscaled footage and the flat graphics sit together,
# then H.264 for Reels / TikTok.
# Usage: [GRAIN=3 CRF=17 MAXRATE=14M PRESET=slow] compose_final.sh <picture.mov> <overlays.mov> <mix.wav> <out.mp4>
set -euo pipefail
PIC="$1"; OVER="$2"; MIX="$3"; OUT="$4"

ffmpeg -v error -stats -y \
  -i "$PIC" -i "$OVER" -i "$MIX" \
  -filter_complex "\
[0:v]format=yuv444p10le[bg];\
[1:v]format=yuva444p10le[fg];\
[bg][fg]overlay=format=yuv444p10:shortest=1,\
format=yuv420p,noise=c0s=${GRAIN:-3}:c0f=t[v]" \
  -map "[v]" -map 2:a \
  -c:v libx264 -preset "${PRESET:-slow}" -crf "${CRF:-17}" -maxrate "${MAXRATE:-14M}" -bufsize "${BUFSIZE:-28M}" \
  -profile:v high -pix_fmt yuv420p -r 30 -x264-params "aq-mode=3" \
  -colorspace bt709 -color_primaries bt709 -color_trc bt709 -color_range tv \
  -c:a aac -b:a 256k -ar 48000 -ac 2 \
  -movflags +faststart -shortest "$OUT"
