#!/usr/bin/env python3
"""
scripts/fetch_assets.py - Pexels Asset Pipeline for Sleep & Ambience Channel

Fetches high-quality landscape 1080p/4K footage, trims it to the required
seamless-loop duration (e.g. 22s for 20s loop with 2s xfade), and updates
the compliance registry (licences/LICENCE_LOG.md).
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LICENCE_LOG = BASE_DIR / "licences" / "LICENCE_LOG.md"

CONCEPT_QUERIES = {
    "window": {
        "title": "Regen am Fenster",
        "queries": ["rain drops on window glass", "rain window night cozy", "rain water sliding down glass"],
        "default_duration": 22,
    },
    "thunder": {
        "title": "Regen mit fernem Gewitter",
        "queries": ["dark stormy sky rain", "rain clouds distant thunder", "dark rainy night trees"],
        "default_duration": 22,
    },
    "car": {
        "title": "Regen auf dem Autodach / Windschutzscheibe",
        "queries": ["rain on car windshield", "rain driving car window blur", "rain car night drops"],
        "default_duration": 22,
    },
    "tent": {
        "title": "Regen auf dem Zeltdach / Blechdach",
        "queries": ["rain on tent camping", "rain on roof metal cabin", "rain falling on roof"],
        "default_duration": 22,
    },
    "forest": {
        "title": "Regen im Schwarzwald / Natur",
        "queries": ["rain forest mist trees", "rain on leaves green forest", "rainy misty spruce forest"],
        "default_duration": 22,
    },
    "fire": {
        "title": "Kaminfeuer und Regen",
        "queries": ["fireplace flames cozy night", "burning fireplace window rain"],
        "default_duration": 22,
    },
    "city": {
        "title": "Stadtregen bei Nacht",
        "queries": ["rainy city street night blur", "wet city street lights rain", "rain tram street bokeh"],
        "default_duration": 22,
    },
    "drizzle": {
        "title": "Leichter Nieselregen",
        "queries": ["gentle drizzle rain leaves", "light rain fog mist nature", "soft rain calm garden"],
        "default_duration": 22,
    },
    "study": {
        "title": "Regengeräusche zum Lernen & Konzentrieren",
        "queries": ["rain window cozy study desk", "reading book window rain", "cozy room desk rain window"],
        "default_duration": 22,
    },
}


def load_api_key():
    key = os.environ.get("PEXELS_API_KEY")
    if key:
        return key

    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("PEXELS_API_KEY="):
                    return line.split("=", 1)[1].strip()

    # Sibling project fallback
    for sibling in ["shorts-forge", "zaitoon-studio"]:
        sibling_env = BASE_DIR.parent / sibling / ".env"
        if sibling_env.exists():
            with open(sibling_env, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PEXELS_API_KEY="):
                        return line.split("=", 1)[1].strip()

    raise RuntimeError("PEXELS_API_KEY not found in environment or .env file.")


def search_pexels(query, api_key, per_page=10):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({
        "query": query,
        "orientation": "landscape",
        "per_page": per_page,
    })
    req = urllib.request.Request(url, headers={
        "Authorization": api_key,
        "User-Agent": "AmbiencePipeline/1.0"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp).get("videos", [])


def pick_best_video_file(video):
    files = video.get("video_files", [])
    # Filter for mp4 files
    mp4_files = [f for f in files if f.get("file_type") == "video/mp4" and f.get("width")]
    if not mp4_files:
        return None
    # Prefer exact 1920x1080 (HD), then higher
    # Score: absolute difference from 1920
    mp4_files.sort(key=lambda f: (0 if f.get("width") == 1920 else 1, abs(f.get("width", 0) - 1920)))
    return mp4_files[0]


def download_file(url, target_path):
    req = urllib.request.Request(url, headers={"User-Agent": "AmbiencePipeline/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(target_path, "wb") as f:
        while chunk := resp.read(1 << 20):
            f.write(chunk)


def trim_and_normalize(input_path, output_path, duration=22):
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(input_path),
        "-t", str(duration),
        "-an",
        "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)


def record_licence(entry):
    LICENCE_LOG.parent.mkdir(parents=True, exist_ok=True)
    if not LICENCE_LOG.exists():
        with open(LICENCE_LOG, "w", encoding="utf-8") as f:
            f.write("# Stock & Media Compliance Registry\n\n")
            f.write("| Date | Output File | Concept | Source | ID | Creator | Target Duration | Source URL | Licence |\n")
            f.write("|---|---|---|---|---|---|---|---|---|\n")

    with open(LICENCE_LOG, "a", encoding="utf-8") as f:
        f.write(
            f"| {entry['date']} | `{entry['filename']}` | {entry['concept']} | {entry['source']} | "
            f"{entry['id']} | {entry['creator']} | {entry['duration']}s | [Link]({entry['url']}) | {entry['licence']} |\n"
        )


def main():
    parser = argparse.ArgumentParser(description="Fetch and normalize video assets for Ambience Channel.")
    parser.add_argument("--concept", choices=list(CONCEPT_QUERIES.keys()), help="Concept name (e.g. window, forest, car)")
    parser.add_argument("--search", help="Custom search query string")
    parser.add_argument("--duration", type=int, default=22, help="Target trimmed duration in seconds (default 22s for 20s loop)")
    parser.add_argument("--output", help="Destination path for normalized clip (e.g. clips/window_22s.mp4)")
    parser.add_argument("--list-concepts", action="store_true", help="List available concepts")

    args = parser.parse_args()

    if args.list_concepts:
        print("Available Concepts:")
        for k, v in CONCEPT_QUERIES.items():
            print(f"  - {k:10s} : {v['title']} (queries: {', '.join(v['queries'])})")
        return

    if not args.concept and not args.search:
        parser.error("Specify either --concept or --search.")

    api_key = load_api_key()

    if args.concept:
        queries = CONCEPT_QUERIES[args.concept]["queries"]
        concept_name = args.concept
    else:
        queries = [args.search]
        concept_name = "custom"

    videos = []
    chosen_query = ""
    for q in queries:
        print(f"Searching Pexels for: '{q}'...")
        results = search_pexels(q, api_key)
        # Filter for videos with duration >= requested duration
        viable = [v for v in results if v.get("duration", 0) >= args.duration]
        if viable:
            videos = viable
            chosen_query = q
            break

    if not videos:
        print("Error: No suitable videos found matching minimum duration criteria.")
        sys.exit(1)

    selected_video = videos[0]
    best_file = pick_best_video_file(selected_video)
    if not best_file:
        print("Error: Could not find valid mp4 stream.")
        sys.exit(1)

    print(f"Found match: ID {selected_video['id']} by {selected_video['user']['name']}")
    print(f"Original duration: {selected_video['duration']}s | Resolution: {best_file.get('width')}x{best_file.get('height')}")

    out_path = Path(args.output) if args.output else BASE_DIR / "clips" / f"{concept_name}_{args.duration}s.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_raw = BASE_DIR / "work" / f"raw_{selected_video['id']}.mp4"
    tmp_raw.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading stream from {best_file['link']}...")
    download_file(best_file["link"], tmp_raw)

    print(f"Trimming and normalizing to 1080p24 ({args.duration}s)...")
    trim_and_normalize(tmp_raw, out_path, duration=args.duration)

    if tmp_raw.exists():
        tmp_raw.unlink()

    # Record in licence log
    record_licence({
        "date": datetime.date.today().isoformat(),
        "filename": out_path.name,
        "concept": concept_name,
        "source": "Pexels",
        "id": selected_video["id"],
        "creator": selected_video["user"]["name"],
        "duration": args.duration,
        "url": selected_video["url"],
        "licence": "Pexels Free to Use",
    })

    print(f"SUCCESS: Saved normalized clip to {out_path}")
    print(f"Updated licence compliance log in {LICENCE_LOG}")


if __name__ == "__main__":
    main()
