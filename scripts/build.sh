#!/usr/bin/env bash
# scripts/build.sh - Production Seamless-Loop Base Segment & Lossless Expansion
#
# Usage:
#   CLIP=clips/window_22s.mp4 AUDIO=audio/mix.wav MODE=xfade VXF=2 ACF=15 COPIES=20 \
#     OUT=out/regen_fenster_10h.mp4 bash scripts/build.sh
#
# Black screen mode (only ~0.6 GB for 10 hours):
#   AUDIO=audio/mix.wav MODE=black ACF=15 COPIES=20 OUT=out/regen_schwarz_10h.mp4 bash scripts/build.sh
#
# Rules enforced:
#   audio loop length = floor(AUDIO duration) - ACF
#   video loop length = 2*clip (pingpong) OR clip - VXF (xfade)
#   audio loop length must be an exact multiple of video loop length!
#   Example: AUDIO 1815s, ACF=15 -> 1800s audio loop
#            clip 22s, VXF=2     -> 20s video loop (1800 / 20 = 90 OK)

set -euo pipefail

MODE=${MODE:-xfade}             # xfade | pingpong | black
ACF=${ACF:-15}                  # audio crossfade seconds
VXF=${VXF:-2}                   # video crossfade seconds (for xfade mode)
COPIES=${COPIES:-20}            # 20 copies x 1800s = 10 hours (36,000s)
OUT=${OUT:-out/video.mp4}
W=${W:-1920}; H=${H:-1080}; FPS=${FPS:-24}
CRF=${CRF:-27}; MAXRATE=${MAXRATE:-1000k}; PRESET=${PRESET:-veryfast}
ABR=${ABR:-128k}
WORK=${WORK:-work}
VERIFY=${VERIFY:-1}

mkdir -p "$WORK" "$(dirname "$OUT")"

dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
floor() { printf '%.0f' "$(echo "$1" | awk '{printf "%d", $1}')"; }

echo "=========================================================="
echo "  German Sleep/Ambience Channel - Video Production Pipeline"
echo "  Mode: $MODE | Copies: $COPIES | Output: $OUT"
echo "=========================================================="

AUDIO=${AUDIO:?Error: Set AUDIO=path/to/mix.wav}
if [ ! -f "$AUDIO" ]; then
  echo "Error: Audio file not found: $AUDIO" >&2
  exit 1
fi

# 1. AUDIO: Seamless Crossfade Loop
echo "[1/4] Processing audio loop (ACF=${ACF}s)..."
L=$(floor "$(dur "$AUDIO")")
ALEN=$((L - ACF))

if [ "$ALEN" -le 0 ]; then
  echo "Error: Audio duration (${L}s) must be greater than ACF (${ACF}s)" >&2
  exit 1
fi

ffmpeg -y -v error -i "$AUDIO" -t "$L" -c:a pcm_s16le "$WORK/src.wav"
ffmpeg -y -v error -ss "$ACF" -i "$WORK/src.wav" -t $((ACF + 2)) -i "$WORK/src.wav" \
  -filter_complex "[0:a][1:a]acrossfade=d=${ACF}:c1=tri:c2=tri[o]" \
  -map "[o]" -t "$ALEN" -c:a pcm_s16le "$WORK/loop.wav"

TOTAL_SECONDS=$((ALEN * COPIES))
echo "  Audio loop built: ${ALEN}s (${L}s source with ${ACF}s crossfade)"

# 2. BLACK SCREEN MODE SHORTCUT
if [ "$MODE" = "black" ]; then
  echo "[2/4] Generating black-screen master (1 fps, tune stillimage, CRF 35)..."
  ffmpeg -y -v error \
    -f lavfi -i "color=c=black:s=${W}x${H}:r=1" \
    -stream_loop -1 -i "$WORK/loop.wav" \
    -t "$TOTAL_SECONDS" \
    -map 0:v -map 1:a \
    -c:v libx264 -preset veryfast -tune stillimage -crf 35 -g 60 -pix_fmt yuv420p \
    -c:a aac -b:a "$ABR" -ar 44100 -shortest -movflags +faststart "$OUT"
  
  echo "[3/4] Render completed successfully!"
  ls -lh "$OUT"
  
  if [ "$VERIFY" = "1" ]; then
    echo "[4/4] Verifying file integrity..."
    ffprobe -v error -show_entries format=duration,size -of default=nw=1 "$OUT"
  fi
  echo "DONE: $OUT"
  exit 0
fi

# 3. VIDEO: Normalisation & Loop Construction
CLIP=${CLIP:?Error: Set CLIP=path/to/clip.mp4 for video modes}
if [ ! -f "$CLIP" ]; then
  echo "Error: Clip file not found: $CLIP" >&2
  exit 1
fi

echo "[2/4] Normalising and looping video clip..."
CL=$(floor "$(dur "$CLIP")")
VF="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},fps=${FPS},format=yuv420p"
ffmpeg -y -v error -i "$CLIP" -t "$CL" -an -vf "$VF" -c:v libx264 -preset veryfast -crf 12 "$WORK/base.mp4"

if [ "$MODE" = "pingpong" ]; then
  VLEN=$((CL * 2))
else
  VLEN=$((CL - VXF))
fi

if [ $((ALEN % VLEN)) -ne 0 ]; then
  echo "ERROR: audio loop (${ALEN}s) is not an exact multiple of video loop (${VLEN}s)!" >&2
  echo "  Calculated remainder: $((ALEN % VLEN)) seconds." >&2
  echo "  Recommendation: adjust clip length to divide ${ALEN}s evenly." >&2
  echo "  Example for 1800s audio loop with VXF=2s: use 22s clip (loop 20s -> 1800/20=90)." >&2
  exit 1
fi

echo "  Video loop length: ${VLEN}s (Divides audio loop ${ALEN}s exactly into $((ALEN / VLEN)) iterations)"

if [ "$MODE" = "pingpong" ]; then
  # Warning: reversed rain falls upwards; use only for fog, candles, lamps
  ffmpeg -y -v error -i "$WORK/base.mp4" \
    -filter_complex "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0[o]" \
    -map "[o]" -c:v libx264 -preset veryfast -crf 12 -pix_fmt yuv420p "$WORK/vloop.mp4"
else
  # Crossfade transition
  ffmpeg -y -v error -ss "$VXF" -i "$WORK/base.mp4" -t $((VXF + 1)) -i "$WORK/base.mp4" \
    -filter_complex "[0:v][1:v]xfade=transition=fade:duration=${VXF}:offset=$((CL - 2 * VXF))[o]" \
    -map "[o]" -t "$VLEN" -c:v libx264 -preset veryfast -crf 12 -pix_fmt yuv420p "$WORK/vloop.mp4"
fi

# 4. BASE SEGMENT ENCODE (Closed GOPs for clean stream-copy concat)
echo "[3/4] Encoding base segment (${ALEN}s)..."
BUFSIZE=$((${MAXRATE%k} * 2))k
GOP=$((FPS * 2))

ffmpeg -y -v error -stream_loop -1 -i "$WORK/vloop.mp4" -stream_loop -1 -i "$WORK/loop.wav" \
  -t "$ALEN" -map 0:v -map 1:a \
  -c:v libx264 -preset "$PRESET" -crf "$CRF" -maxrate "$MAXRATE" -bufsize "$BUFSIZE" \
  -r "$FPS" -g "$GOP" -keyint_min "$GOP" -sc_threshold 0 -pix_fmt yuv420p \
  -c:a aac -b:a "$ABR" -ar 44100 -movflags +faststart "$WORK/segment.mp4"

# 5. LOSSLESS EXPANSION VIA CONCAT DEMUXER
echo "[4/4] Losslessly expanding $COPIES copies -> $TOTAL_SECONDS seconds total..."
: > "$WORK/list.txt"
for _ in $(seq "$COPIES"); do echo "file 'segment.mp4'" >> "$WORK/list.txt"; done
ffmpeg -y -v error -f concat -safe 0 -i "$WORK/list.txt" -c copy -movflags +faststart "$OUT"

echo "=========================================================="
echo "  BUILD COMPLETE!"
echo "  Segment: ${ALEN}s | Copies: ${COPIES} | Total Duration: ${TOTAL_SECONDS}s"
ls -lh "$OUT"
echo "=========================================================="

if [ "$VERIFY" = "1" ]; then
  echo "Verifying output streams..."
  ffprobe -v error -show_entries stream=codec_type,duration,bit_rate -show_entries format=duration,size -of default=nw=1 "$OUT"
fi
