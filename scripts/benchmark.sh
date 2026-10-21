#!/usr/bin/env bash
# scripts/benchmark.sh - Test local encoding speed on 60 seconds of 1080p24 footage
set -euo pipefail

BENCH_CLIP=${1:-}
TMP_DIR="/tmp/rain_bench_$$"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

if [ -n "$BENCH_CLIP" ] && [ -f "$BENCH_CLIP" ]; then
  INPUT_OPT="-i $BENCH_CLIP -vf scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,format=yuv420p"
else
  echo "No clip provided; using synthetic 1080p24 test pattern."
  INPUT_OPT="-f lavfi -i testsrc=size=1920x1080:rate=24"
fi

echo "Running 60s x264 benchmark (preset=veryfast, crf=27, maxrate=1000k)..."
OUTPUT=$(ffmpeg -y $INPUT_OPT -t 60 -an \
  -c:v libx264 -preset veryfast -crf 27 -maxrate 1000k -bufsize 2000k -g 48 \
  "$TMP_DIR/bench.mp4" 2>&1)

SPEED=$(echo "$OUTPUT" | grep -o 'speed=[^ ]*' | tail -n 1 | cut -d= -f2)
ELAPSED=$(echo "$OUTPUT" | grep -o 'elapsed=[^ ]*' | tail -n 1 | cut -d= -f2)

echo "Benchmark Result:"
echo "  Encoding Speed: $SPEED (Elapsed time for 60s: $ELAPSED)"

SPEED_NUM=$(echo "$SPEED" | sed 's/x//')
if awk "BEGIN {exit !($SPEED_NUM >= 0.7)}"; then
  echo "  STATUS: EXCELLENT (>= 0.7x). A 30-minute base segment will take ~20-35 minutes locally."
  echo "  No remote GitHub Actions rendering needed!"
elif awk "BEGIN {exit !($SPEED_NUM >= 0.3)}"; then
  echo "  STATUS: ACCEPTABLE. 30-minute segment will take ~45-75 minutes locally."
  echo "  Can run locally overnight, or switch PRESET to 'superfast'."
else
  echo "  STATUS: SLOW (< 0.3x). Consider 720p fallback (W=1280 H=720) or GitHub Actions."
fi
