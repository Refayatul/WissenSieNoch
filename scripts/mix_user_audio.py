#!/usr/bin/env python3
"""
scripts/mix_user_audio.py - Mix and crossfade multiple user audio recordings
into the exact 1815s master mix required by build.sh.
"""

import argparse
import subprocess
import sys
from pathlib import Path

def get_duration(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(res.stdout.strip())

def main():
    parser = argparse.ArgumentParser(description="Crossfade user recordings into 1815s master mix.")
    parser.add_argument("--inputs", nargs="+", required=True, help="List of input audio files (e.g. take1.wav take2.wav)")
    parser.add_argument("--crossfade", type=int, default=15, help="Crossfade duration between tracks in seconds")
    parser.add_argument("--duration", type=int, default=1815, help="Target total duration in seconds (default 1815)")
    parser.add_argument("--out", default="audio/mix.wav", help="Output file path")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    inputs = [Path(p) for p in args.inputs]
    for p in inputs:
        if not p.exists():
            print(f"Error: Input file {p} does not exist.")
            sys.exit(1)

    if len(inputs) == 1:
        # Loop single input to target duration with acrossfade
        print(f"Looping single track {inputs[0]} to {args.duration}s...")
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-stream_loop", "-1", "-i", str(inputs[0]),
            "-t", str(args.duration),
            "-c:a", "pcm_s16le", "-ar", "44100", "-af", "alimiter=limit=-3dB",
            str(out_path)
        ]
        subprocess.run(cmd, check=True)
    else:
        # Crossfade two or more inputs
        print(f"Crossfading {len(inputs)} tracks with d={args.crossfade}s...")
        filter_str = ""
        last_stream = "[0:a]"
        for i in range(1, len(inputs)):
            curr_stream = f"[{i}:a]"
            out_stream = f"[m{i}]" if i < len(inputs) - 1 else "[out]"
            filter_str += f"{last_stream}{curr_stream}acrossfade=d={args.crossfade}:c1=tri:c2=tri{out_stream};"
            last_stream = out_stream

        cmd = ["ffmpeg", "-y", "-v", "error"]
        for p in inputs:
            cmd.extend(["-i", str(p)])
        cmd.extend([
            "-filter_complex", filter_str.rstrip(";"),
            "-map", "[out]",
            "-t", str(args.duration),
            "-af", "alimiter=limit=-3dB",
            "-c:a", "pcm_s16le", "-ar", "44100",
            str(out_path)
        ])
        subprocess.run(cmd, check=True)

    dur = get_duration(out_path)
    print(f"SUCCESS: Created master audio {out_path} ({dur:.2f}s)")

if __name__ == "__main__":
    main()
