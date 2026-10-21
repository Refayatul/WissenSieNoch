#!/usr/bin/env bash
# build.sh - seamless-loop base segment + lossless expansion to N copies.
#
# Usage (all values are env vars):
#   CLIP=clip.mp4 AUDIO=mix.wav MODE=pingpong ACF=15 COPIES=20 OUT=out/rain_10h.mp4 bash build.sh
#
# Rules the script enforces:
#   audio loop length  = floor(AUDIO duration) - ACF            (seamless crossfade loop)
#   video loop length  = 2*clip (pingpong)  or  clip - VXF (xfade)
#   audio loop length must be an exact multiple of the video loop length,
#   so the base segment repeats seamlessly in BOTH streams.
#   Example: AUDIO 1815 s, ACF=15 -> 1800 s loop; clip 20 s, MODE=pingpong -> 40 s loop (1800/40=45 OK)
#            or clip 22 s, MODE=xfade, VXF=2 -> 20 s loop (1800/20=90 OK)
set -euo pipefail

CLIP=${CLIP:?set CLIP=path/to/clip.mp4}
AUDIO=${AUDIO:?set AUDIO=path/to/mix.wav}
MODE=${MODE:-pingpong}          # pingpong | xfade
ACF=${ACF:-15}                  # audio crossfade seconds
VXF=${VXF:-2}                   # video crossfade seconds (xfade mode)
COPIES=${COPIES:-20}            # 20 x 1800 s = 10 h
OUT=${OUT:-out/rain.mp4}
W=${W:-1920}; H=${H:-1080}; FPS=${FPS:-24}
CRF=${CRF:-27}; MAXRATE=${MAXRATE:-1000k}; PRESET=${PRESET:-veryfast}
ABR=${ABR:-128k}
WORK=${WORK:-work}

mkdir -p "$WORK" "$(dirname "$OUT")"
dur() { ffprobe -v error -show_entries format=duration -of csv=p=0 "$1"; }
floor() { printf '%.0f' "$(echo "$1" | awk '{printf "%d", $1}')"; }

# ---- audio: trim to whole seconds, then crossfade tail into head -> loop.wav
L=$(floor "$(dur "$AUDIO")")
ALEN=$((L - ACF))
ffmpeg -y -v error -i "$AUDIO" -t "$L" -c:a pcm_s16le "$WORK/src.wav"
ffmpeg -y -v error -ss "$ACF" -i "$WORK/src.wav" -t $((ACF + 2)) -i "$WORK/src.wav" \
  -filter_complex "[0:a][1:a]acrossfade=d=${ACF}:c1=tri:c2=tri[o]" \
  -map "[o]" -t "$ALEN" -c:a pcm_s16le "$WORK/loop.wav"

# ---- video: normalise clip to exact whole seconds, then build loopable clip
CL=$(floor "$(dur "$CLIP")")
VF="scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},fps=${FPS},format=yuv420p"
ffmpeg -y -v error -i "$CLIP" -t "$CL" -an -vf "$VF" -c:v libx264 -preset veryfast -crf 12 "$WORK/base.mp4"

if [ "$MODE" = pingpong ]; then
  VLEN=$((CL * 2))
else
  VLEN=$((CL - VXF))
fi
if [ $((ALEN % VLEN)) -ne 0 ]; then
  echo "ERROR: audio loop (${ALEN}s) is not a multiple of video loop (${VLEN}s). Adjust clip length / ACF." >&2
  exit 1
fi

if [ "$MODE" = pingpong ]; then
  # NOTE: reversed rain streaks fall upwards. Use only for fog, trees, candles, lamps. Use MODE=xfade for visible rain.
  ffmpeg -y -v error -i "$WORK/base.mp4" \
    -filter_complex "[0:v]split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0[o]" \
    -map "[o]" -c:v libx264 -preset veryfast -crf 12 -pix_fmt yuv420p "$WORK/vloop.mp4"
else
  ffmpeg -y -v error -ss "$VXF" -i "$WORK/base.mp4" -t $((VXF + 1)) -i "$WORK/base.mp4" \
    -filter_complex "[0:v][1:v]xfade=transition=fade:duration=${VXF}:offset=$((CL - 2 * VXF))[o]" \
    -map "[o]" -t "$VLEN" -c:v libx264 -preset veryfast -crf 12 -pix_fmt yuv420p "$WORK/vloop.mp4"
fi

# ---- base segment (the only slow step). closed GOPs so stream-copy joins are clean
ffmpeg -y -v error -stream_loop -1 -i "$WORK/vloop.mp4" -stream_loop -1 -i "$WORK/loop.wav" \
  -t "$ALEN" -map 0:v -map 1:a \
  -c:v libx264 -preset "$PRESET" -crf "$CRF" -maxrate "$MAXRATE" -bufsize $((${MAXRATE%k} * 2))k \
  -r "$FPS" -g $((FPS * 2)) -keyint_min $((FPS * 2)) -sc_threshold 0 -pix_fmt yuv420p \
  -c:a aac -b:a "$ABR" -ar 44100 -movflags +faststart "$WORK/segment.mp4"

# ---- lossless expansion (no re-encode)
: > "$WORK/list.txt"
for _ in $(seq "$COPIES"); do echo "file 'segment.mp4'" >> "$WORK/list.txt"; done
ffmpeg -y -v error -f concat -safe 0 -i "$WORK/list.txt" -c copy -movflags +faststart "$OUT"

echo "segment: ${ALEN}s  copies: ${COPIES}  total: $((ALEN * COPIES))s"
ffprobe -v error -show_entries stream=codec_type,duration -show_entries format=duration,size -of default=nw=1 "$OUT"
