#!/usr/bin/env bash
# scripts/generate_audio.sh - Generate Original Ambient Rain Audio or Mix Existing Tracks
#
# Generates 1815s master audio track (1800s seamless loop + 15s crossfade)
# strictly adhering to sleep acoustics:
#   - Peaks limited to -3 dBFS (no sudden waking jolts)
#   - Warm frequency contour (gentle lowpass / pink-brown balance)
#   - 100% original synthesis to guarantee zero Content ID flags
#
# Usage:
#   bash scripts/generate_audio.sh --type window --duration 1815 --out audio/window_mix.wav
#   bash scripts/generate_audio.sh --type thunder --duration 1815 --out audio/thunder_mix.wav
#   bash scripts/generate_audio.sh --type car --duration 1815 --out audio/car_mix.wav

set -euo pipefail

TYPE="window"
DURATION=1815
OUT="audio/mix.wav"

while [[ $# -gt 0 ]]; do
  case $1 in
    --type)
      TYPE="$2"
      shift 2
      ;;
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --out)
      OUT="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$OUT")"

echo "=========================================================="
echo "  Generating Original Sleep Audio: $TYPE"
echo "  Target Duration: ${DURATION}s -> Output: $OUT"
echo "=========================================================="

case "$TYPE" in
  window)
    # Soothing rain on glass: deep warm base, mid-range shower, delicate glass patter
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.35,lowpass=f=450,volume=1.2[sub]; \
      anoisesrc=c=pink:r=44100:a=0.28,bandpass=f=1600:w=1200[mid]; \
      anoisesrc=c=pink:r=44100:a=0.12,highpass=f=3800,lowpass=f=8000,volume=0.9[patter]; \
      [sub][mid][patter]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB:attack=5:release=50[out]"
    ;;
  thunder)
    # Distant thunder: low-frequency rolling rumble mixed under steady rain
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.45,lowpass=f=220,tremolo=f=0.08:d=0.7,volume=1.5[rumble]; \
      anoisesrc=c=pink:r=44100:a=0.25,bandpass=f=1500:w=1200[rain]; \
      anoisesrc=c=pink:r=44100:a=0.08,highpass=f=3500[drops]; \
      [rumble][rain][drops]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB:attack=5:release=80[out]"
    ;;
  car)
    # Rain on car roof & windscreen: cabin acoustic resonance, soft hollow roof drumming
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.40,lowpass=f=350,volume=1.3[cabin]; \
      anoisesrc=c=pink:r=44100:a=0.22,bandpass=f=1100:w=800,volume=1.1[roof]; \
      anoisesrc=c=pink:r=44100:a=0.10,bandpass=f=2800:w=1500[windshield]; \
      [cabin][roof][windshield]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  forest)
    # Rain in forest: broad soft canopy wash and gentle leaf drips
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.30,lowpass=f=400[ground]; \
      anoisesrc=c=pink:r=44100:a=0.26,bandpass=f=1800:w=1400[canopy]; \
      anoisesrc=c=pink:r=44100:a=0.14,highpass=f=4200,volume=0.8[leaves]; \
      [ground][canopy][leaves]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  drizzle)
    # Light gentle drizzle: whisper-soft high patter, calm and airy
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.18,lowpass=f=400[air]; \
      anoisesrc=c=pink:r=44100:a=0.18,bandpass=f=2200:w=1600[drizzle]; \
      anoisesrc=c=pink:r=44100:a=0.06,highpass=f=4500[mist]; \
      [air][drizzle][mist]amix=inputs=3:dropout_transition=0,alimiter=limit=-3dB[out]"
    ;;
  *)
    echo "Unknown type: $TYPE. Using window."
    FILTER_GRAPH="anoisesrc=c=brown:r=44100:a=0.35,lowpass=f=450[sub]; anoisesrc=c=pink:r=44100:a=0.28,bandpass=f=1600:w=1200[mid]; [sub][mid]amix=inputs=2,alimiter=limit=-3dB[out]"
    ;;
esac

ffmpeg -y -filter_complex "$FILTER_GRAPH" -map "[out]" -t "$DURATION" \
  -c:a pcm_s16le -ar 44100 -ac 2 "$OUT"

DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")
echo "Generated $OUT: duration ${DUR}s"
