#!/usr/bin/env python3
"""
manage.py - Master CLI for German Rain/Sleep Ambience YouTube Channel

Channel pivot: WissenSieNoch (DDR history documentaries) -> Rain/Sleep Ambience
Based on Claude's research (Files 1-3, 21 Oct 2026).

All heavy assets (audio, clips, work, output) live on /mnt/programming/German/
to preserve space on the 97 GB /home partition.

Usage:
  python manage.py status             Show workspace status
  python manage.py bench              Benchmark local encoding speed
  python manage.py fetch <concept>    Download & normalize clip from Pexels
  python manage.py audio <type>       Generate original sleep audio (ffmpeg synthesis)
  python manage.py build <concept>    Build complete 10-hour seamless video
  python manage.py black              Build 10-hour black screen (~0.59 GB)
  python manage.py verify <file>      QA verify video integrity
  python manage.py freesound <query>  Search Freesound for CC0 rain audio
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent         # /home/kai/Downloads/projects/German
STORAGE = Path("/mnt/programming/German")         # 147 GB free — heavy assets go here
SCRIPTS = PROJECT / "scripts"


def ensure_storage():
    """Create storage dirs on the big drive if they don't exist."""
    for d in ["audio", "clips", "work", "out"]:
        (STORAGE / d).mkdir(parents=True, exist_ok=True)


def cmd_status():
    ensure_storage()
    print("=" * 60)
    print("  German Rain/Sleep Ambience Channel — Workspace Status")
    print("=" * 60)

    # Disk
    for label, path in [("Project (/home)", PROJECT), ("Storage (/mnt)", STORAGE)]:
        try:
            t, u, f = shutil.disk_usage(path)
            print(f"  {label}: {f/(1024**3):.1f} GB free / {t/(1024**3):.1f} GB total")
        except Exception:
            print(f"  {label}: unavailable")

    # Assets
    for label, d, ext in [
        ("Clips", STORAGE / "clips", "*.mp4"),
        ("Audio", STORAGE / "audio", "*.wav"),
        ("Output", STORAGE / "out", "*.mp4"),
    ]:
        files = sorted(d.glob(ext)) if d.exists() else []
        print(f"\n  {label} ({len(files)}):")
        for f in files:
            sz = f.stat().st_size
            unit = "GB" if sz > 500_000_000 else "MB"
            val = sz / (1024**3) if unit == "GB" else sz / (1024**2)
            print(f"    {f.name:40s} {val:>7.1f} {unit}")
        if not files:
            print("    (none)")

    print("\n" + "=" * 60)


def cmd_bench():
    subprocess.run(["bash", str(SCRIPTS / "benchmark.sh")])


def cmd_fetch(concept, duration=22):
    ensure_storage()
    out = STORAGE / "clips" / f"{concept}_{duration}s.mp4"
    subprocess.run([
        sys.executable, str(SCRIPTS / "fetch_assets.py"),
        "--concept", concept,
        "--duration", str(duration),
        "--output", str(out),
    ])


def cmd_audio(audio_type, duration=1815):
    ensure_storage()
    out = STORAGE / "audio" / f"{audio_type}_mix.wav"
    subprocess.run([
        "bash", str(SCRIPTS / "generate_audio.sh"),
        "--type", audio_type,
        "--duration", str(duration),
        "--out", str(out),
    ])


def cmd_build(concept, copies=20, out_name=None):
    ensure_storage()
    clip = STORAGE / "clips" / f"{concept}_22s.mp4"
    audio = STORAGE / "audio" / f"{concept}_mix.wav"

    if not clip.exists():
        print(f"Clip not found at {clip}. Fetching from Pexels...")
        cmd_fetch(concept, 22)

    if not audio.exists():
        print(f"Audio not found at {audio}. Generating synthesized audio...")
        cmd_audio(concept, 1815)

    out = STORAGE / "out" / (out_name or f"regen_{concept}_10h.mp4")

    env = os.environ.copy()
    env.update({
        "CLIP": str(clip),
        "AUDIO": str(audio),
        "MODE": "xfade",
        "VXF": "2",
        "ACF": "15",
        "COPIES": str(copies),
        "OUT": str(out),
        "WORK": str(STORAGE / "work"),
    })
    subprocess.run(["bash", str(SCRIPTS / "build.sh")], env=env)


def cmd_black(copies=20, out_name="regen_schwarz_10h.mp4"):
    ensure_storage()

    # Need SOME audio — use whatever's available or generate window type
    audio = None
    audio_dir = STORAGE / "audio"
    wavs = list(audio_dir.glob("*.wav")) if audio_dir.exists() else []
    if wavs:
        audio = wavs[0]
    else:
        print("No audio found. Generating window-type sleep audio...")
        cmd_audio("window", 1815)
        audio = audio_dir / "window_mix.wav"

    out = STORAGE / "out" / out_name
    env = os.environ.copy()
    env.update({
        "AUDIO": str(audio),
        "MODE": "black",
        "ACF": "15",
        "COPIES": str(copies),
        "OUT": str(out),
        "WORK": str(STORAGE / "work"),
    })
    subprocess.run(["bash", str(SCRIPTS / "build.sh")], env=env)


def cmd_verify(filepath):
    subprocess.run([sys.executable, str(SCRIPTS / "verify.py"), filepath])


def cmd_freesound(query):
    subprocess.run([sys.executable, str(SCRIPTS / "fetch_freesound.py"), "--query", query])


def main():
    parser = argparse.ArgumentParser(description="German Rain/Sleep Ambience Channel CLI")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("status")
    sub.add_parser("bench")

    p = sub.add_parser("fetch")
    p.add_argument("concept", choices=["window", "thunder", "car", "tent", "forest", "fire", "city", "drizzle", "study"])
    p.add_argument("--duration", type=int, default=22)

    p = sub.add_parser("audio")
    p.add_argument("type", choices=["window", "thunder", "car", "forest", "drizzle"])
    p.add_argument("--duration", type=int, default=1815)

    p = sub.add_parser("build")
    p.add_argument("concept")
    p.add_argument("--copies", type=int, default=20)
    p.add_argument("--out", default=None)

    p = sub.add_parser("black")
    p.add_argument("--copies", type=int, default=20)
    p.add_argument("--out", default="regen_schwarz_10h.mp4")

    p = sub.add_parser("verify")
    p.add_argument("file")

    p = sub.add_parser("freesound")
    p.add_argument("query")

    args = parser.parse_args()

    if not args.cmd or args.cmd == "status":
        cmd_status()
    elif args.cmd == "bench":
        cmd_bench()
    elif args.cmd == "fetch":
        cmd_fetch(args.concept, args.duration)
    elif args.cmd == "audio":
        cmd_audio(args.type, args.duration)
    elif args.cmd == "build":
        cmd_build(args.concept, args.copies, args.out)
    elif args.cmd == "black":
        cmd_black(args.copies, args.out)
    elif args.cmd == "verify":
        cmd_verify(args.file)
    elif args.cmd == "freesound":
        cmd_freesound(args.query)


if __name__ == "__main__":
    main()
