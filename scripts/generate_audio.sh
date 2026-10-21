#!/usr/bin/env bash
# scripts/generate_audio.sh - Generate original ambient audio via ffmpeg synthesis
#
# This is a FALLBACK for when you don't have real recordings or CC0 Freesound files.
# Claude's research (File 2, §0 + §4) ranks audio sources:
#   1. BEST: Record your own rain (phone at window / tin roof, 44.1 kHz+, 20-40 min)
#   2. GOOD: Freesound with licence filter = CC0 (use fetch_freesound.py)
#   3. OK:   YouTube Audio Library (inside Studio)
#   4. LAST: Synthesized (this script) — no Content ID risk, but not "original recording"
#
# Usage:
#   bash scripts/generate_audio.sh --type window --duration 1815 --out /mnt/programming/German/audio/window_mix.wav

set -euo pipefail

TYPE="window"
DURATION=1815
OUT="/mnt/programming/German/audio/mix.wav"

while [[ $# -gt 0 ]]; do
  case $1 in
    --type)    TYPE="$2";     shift 2 ;;
    --duration) DURATION="$2"; shift 2 ;;
    --out)     OUT="$2";      shift 2 ;;
    *) echo "Unknown: $1" >&2; exit 1 ;;
  esac
done

mkdir -p "$(dirname "$OUT")"

echo "Generating ${TYPE} audio (${DURATION}s) -> $OUT"

# All filters use -filter_complex (NOT -f lavfi -i) to avoid output label issues.
# Peaks limited to -3 dBFS per Claude File 1, §3.1.
case "$TYPE" in
  window)
    FILTER="anoisesrc=c=brown:r=44100:a=0.35,lowpass=f=450,volume=1.2[sub]; \
      anoisesrc=c=pink:r=44100:a=0.28,bandpass=f=1600:w=1200[mid]; \
      anoisesrc=c=pink:r=44100:a=0.12,highpass=f=3800,lowpass=f=8000,volume=0.9[patter]; \
      [sub][mid][patter]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB:attack=5:release=50[out]"
    ;;
  thunder)
    FILTER="anoisesrc=c=brown:r=44100:a=0.45,lowpass=f=220,tremolo=f=0.08:d=0.7,volume=1.5[rumble]; \
      anoisesrc=c=pink:r=44100:a=0.25,bandpass=f=1500:w=1200[rain]; \
      anoisesrc=c=pink:r=44100:a=0.08,highpass=f=3500[drops]; \
      [rumble][rain][drops]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB:attack=5:release=80[out]"
    ;;
  car)
    FILTER="anoisesrc=c=brown:r=44100:a=0.40,lowpass=f=350,volume=1.3[cabin]; \
      anoisesrc=c=pink:r=44100:a=0.22,bandpass=f=1100:w=800,volume=1.1[roof]; \
      anoisesrc=c=pink:r=44100:a=0.10,bandpass=f=2800:w=1500[windshield]; \
      [cabin][roof][windshield]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  forest)
    FILTER="anoisesrc=c=brown:r=44100:a=0.30,lowpass=f=400[ground]; \
      anoisesrc=c=pink:r=44100:a=0.26,bandpass=f=1800:w=1400[canopy]; \
      anoisesrc=c=pink:r=44100:a=0.14,highpass=f=4200,volume=0.8[leaves]; \
      [ground][canopy][leaves]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  drizzle)
    FILTER="anoisesrc=c=brown:r=44100:a=0.18,lowpass=f=400[air]; \
      anoisesrc=c=pink:r=44100:a=0.18,bandpass=f=2200:w=1600[drizzle]; \
      anoisesrc=c=pink:r=44100:a=0.06,highpass=f=4500[mist]; \
      [air][drizzle][mist]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  *)
    echo "Unknown type: $TYPE (use: window, thunder, car, forest, drizzle)" >&2
    exit 1
    ;;
esac

ffmpeg -y -filter_complex "$FILTER" -map "[out]" -t "$DURATION" \
  -c:a pcm_s16le -ar 44100 -ac 2 "$OUT"

echo "Done: $OUT ($(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")s)"
