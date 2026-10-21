#!/usr/bin/env python3
"""
scripts/fetch_freesound.py - Fetch CC0 rain/nature audio from Freesound.org

Claude's research (File 2, §0 and §4) strongly recommends:
  1. Recording your own rain audio (phone voice recorder, 44.1 kHz+, 20-40 min per take)
  2. Using Freesound with licence filter = CC0 (no attribution needed, no Content ID risk)

This script automates option 2: search Freesound for CC0-only rain recordings,
download them, and prepare them for the audio mixing pipeline.

Usage:
  # First get a free API key from https://freesound.org/apiv2/apply/
  export FREESOUND_API_KEY=your_key_here
  
  python scripts/fetch_freesound.py --query "rain window" --duration-min 30 --out audio/rain_take1.wav
  python scripts/fetch_freesound.py --query "rain tin roof" --duration-min 20 --out audio/rain_take2.wav
  python scripts/fetch_freesound.py --query "rain forest" --duration-min 30 --out audio/rain_take3.wav

Then mix them:
  python scripts/mix_user_audio.py --inputs audio/rain_take1.wav audio/rain_take2.wav --out audio/mix.wav
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_api_key():
    key = os.environ.get("FREESOUND_API_KEY")
    if key:
        return key

    for env_path in [BASE_DIR / ".env", Path("/mnt/programming/.env")]:
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FREESOUND_API_KEY="):
                        return line.split("=", 1)[1].strip()

    return None


def search_freesound(query, api_key, min_duration=30, max_duration=600):
    """Search Freesound for CC0 sounds matching query."""
    params = urllib.parse.urlencode({
        "query": query,
        "filter": f'license:"Creative Commons 0" duration:[{min_duration} TO {max_duration}]',
        "fields": "id,name,duration,url,license,previews,download,username,description",
        "sort": "rating_desc",
        "page_size": 15,
        "token": api_key,
    })
    url = f"https://freesound.org/apiv2/search/text/?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "AmbiencePipeline/1.0"})

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
        return data.get("results", [])


def download_sound(sound_id, api_key, output_path):
    """Download a sound from Freesound using the API."""
    # Get the download URL
    url = f"https://freesound.org/apiv2/sounds/{sound_id}/download/?token={api_key}"
    req = urllib.request.Request(url, headers={"User-Agent": "AmbiencePipeline/1.0"})

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Freesound download returns the raw file
    tmp_path = output_path.with_suffix(".tmp")
    try:
        with urllib.request.urlopen(req, timeout=300) as resp, open(tmp_path, "wb") as f:
            total = 0
            while chunk := resp.read(1 << 20):
                f.write(chunk)
                total += len(chunk)
                print(f"\r  Downloaded {total / (1024*1024):.1f} MB", end="", flush=True)
            print()
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("ERROR: Freesound API key is invalid or expired.")
            print("Get a free key at: https://freesound.org/apiv2/apply/")
            sys.exit(1)
        raise

    # Convert to 44100 Hz WAV (Claude spec: 44.1 kHz or higher)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-i", str(tmp_path),
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "1",
        # Limiter: peaks at or below -3 dBFS (Claude File 2, §0 + File 1, §3.1)
        "-af", "alimiter=limit=0.708:attack=5:release=50",
        str(output_path)
    ], check=True)

    tmp_path.unlink(missing_ok=True)


def log_licence(sound, output_path):
    """Append to licence log per Claude's recommendation (File 2, §4)."""
    log_path = BASE_DIR / "licences" / "LICENCE_LOG.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    import datetime
    if not log_path.exists():
        with open(log_path, "w") as f:
            f.write("# Stock & Media Compliance Registry\n\n")
            f.write("| Date | File | Source | ID | Creator | Duration | URL | Licence |\n")
            f.write("|---|---|---|---|---|---|---|---|\n")

    with open(log_path, "a") as f:
        f.write(
            f"| {datetime.date.today().isoformat()} "
            f"| `{Path(output_path).name}` "
            f"| Freesound "
            f"| {sound['id']} "
            f"| {sound.get('username', 'unknown')} "
            f"| {sound.get('duration', 0):.0f}s "
            f"| [{sound['id']}]({sound.get('url', '')}) "
            f"| CC0 (Public Domain) |\n"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Fetch CC0 rain audio from Freesound.org (Claude File 2 §0, §4)")
    parser.add_argument("--query", default="rain",
                        help="Search query (e.g. 'rain window', 'rain tin roof', 'thunderstorm distant')")
    parser.add_argument("--duration-min", type=int, default=30,
                        help="Minimum duration in seconds (default 30)")
    parser.add_argument("--duration-max", type=int, default=600,
                        help="Maximum duration in seconds (default 600)")
    parser.add_argument("--out", default=None,
                        help="Output WAV path (default: /mnt/programming/German/audio/<query>.wav)")
    parser.add_argument("--list-only", action="store_true",
                        help="List matching sounds without downloading")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        print("=" * 60)
        print("  Freesound API key not found!")
        print()
        print("  To get a free key:")
        print("  1. Create an account at https://freesound.org/")
        print("  2. Apply for an API key at https://freesound.org/apiv2/apply/")
        print("  3. Add to your .env file:")
        print("     FREESOUND_API_KEY=your_key_here")
        print()
        print("  Or export it:")
        print("     export FREESOUND_API_KEY=your_key_here")
        print("=" * 60)
        sys.exit(1)

    print(f"Searching Freesound for CC0 '{args.query}' (duration {args.duration_min}-{args.duration_max}s)...")
    results = search_freesound(args.query, api_key, args.duration_min, args.duration_max)

    if not results:
        print("No CC0 results found. Try a different query.")
        print("Suggestions: 'rain', 'rain window', 'heavy rain', 'rain roof',")
        print("             'thunderstorm', 'rain forest', 'drizzle'")
        sys.exit(1)

    print(f"\nFound {len(results)} CC0 results:\n")
    for i, s in enumerate(results):
        print(f"  [{i+1}] ID {s['id']:>7d} | {s.get('duration', 0):>5.0f}s | {s.get('username', '?'):>15s} | {s['name'][:60]}")

    if args.list_only:
        return

    # Auto-select the first result (longest duration preferred for sleep audio)
    selected = results[0]
    print(f"\nSelected: [{selected['id']}] {selected['name']} ({selected.get('duration', 0):.0f}s) by {selected.get('username', 'unknown')}")

    safe_query = args.query.replace(" ", "_").replace("/", "_")
    out_path = args.out or f"/mnt/programming/German/audio/freesound_{safe_query}_{selected['id']}.wav"

    print(f"Downloading to {out_path}...")
    download_sound(selected["id"], api_key, out_path)

    log_licence(selected, out_path)

    dur_cmd = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out_path],
        capture_output=True, text=True
    )
    dur = float(dur_cmd.stdout.strip()) if dur_cmd.returncode == 0 else 0

    print(f"\nSUCCESS: {out_path} ({dur:.1f}s, 44100 Hz, peaks limited to -3 dBFS)")
    print(f"Licence: CC0 (Public Domain) — no attribution required, no Content ID risk")
    print(f"\nNext step: mix into 1815s master track:")
    print(f"  python scripts/mix_user_audio.py --inputs {out_path} --duration 1815 --out /mnt/programming/German/audio/mix.wav")


if __name__ == "__main__":
    main()
