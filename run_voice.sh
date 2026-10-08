#!/usr/bin/env bash
set -e
echo "Starting Piper TTS synthesis on script.txt..."
cat script.txt | /home/kai/Downloads/projects/German/.venv/bin/piper -m de_DE-thorsten-high.onnx -f raw.wav
echo "Piper synthesis complete. Adjusting tempo with ffmpeg atempo=0.93..."
ffmpeg -y -i raw.wav -filter:a "atempo=0.93" narration.wav
echo "Narration complete! Duration:"
ffprobe -v error -show_entries format=duration -of csv=p=0 narration.wav
