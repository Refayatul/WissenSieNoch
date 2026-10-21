#!/usr/bin/env python3
"""
manage.py - Master CLI for the German Sleep & Ambience YouTube Channel

Usage:
  python manage.py status           # Check pipeline status & available assets
  python manage.py bench            # Test local encode speed on your machine
  python manage.py fetch <concept>  # Download & normalize clip from Pexels (e.g. window, thunder, car)
  python manage.py audio <concept>  # Generate 1815s original sleep audio mix
  python manage.py build <concept>  # Build complete 10-hour seamless video
  python manage.py build-black      # Build 10-hour ultra-lightweight black screen video (~0.6 GB)
  python manage.py verify <file>    # QA inspect audio/video sync, seams & faststart
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def run_sh(cmd):
    return subprocess.run(cmd, shell=True)

def cmd_status():
    print("==========================================================")
    print("  German Sleep/Ambience Channel - Workspace Status")
    print("==========================================================")
    
    # Check disk space
    total, used, free = shutil.disk_usage(BASE_DIR)
    print(f"Disk Space Available : {free / (1024**3):.2f} GB free of {total / (1024**3):.2f} GB")
    
    # Check clips
    clips_dir = BASE_DIR / "clips"
    clips = list(clips_dir.glob("*.mp4")) if clips_dir.exists() else []
    print(f"Prepared Clips ({len(clips)}):")
    for c in clips:
        size_mb = c.stat().st_size / (1024 * 1024)
        print(f"  - {c.name} ({size_mb:.1f} MB)")
        
    # Check audio
    audio_dir = BASE_DIR / "audio"
    audios = list(audio_dir.glob("*.wav")) if audio_dir.exists() else []
    print(f"Master Audio Tracks ({len(audios)}):")
    for a in audios:
        size_mb = a.stat().st_size / (1024 * 1024)
        print(f"  - {a.name} ({size_mb:.1f} MB)")
        
    # Check outputs
    out_dir = BASE_DIR / "out"
    outs = list(out_dir.glob("*.mp4")) if out_dir.exists() else []
    print(f"Rendered Output Videos ({len(outs)}):")
    for o in outs:
        size_gb = o.stat().st_size / (1024**3)
        print(f"  - {o.name} ({size_gb:.2f} GB)")

    print("\nNext Action on Calendar:")
    print("  - V1 (Sun 25 Oct): Regen am Fenster 10h (Concept #1)")
    print("  - V2 (Wed 28 Oct): Black Screen 10h (Concept #7)")
    print("==========================================================")

def cmd_bench():
    bench_script = BASE_DIR / "scripts" / "benchmark.sh"
    subprocess.run(["bash", str(bench_script)])

def cmd_fetch(concept, duration=22):
    fetch_script = BASE_DIR / "scripts" / "fetch_assets.py"
    subprocess.run([sys.executable, str(fetch_script), "--concept", concept, "--duration", str(duration)])

def cmd_audio(concept_type, duration=1815):
    audio_script = BASE_DIR / "scripts" / "generate_audio.sh"
    out_file = BASE_DIR / "audio" / f"{concept_type}_mix.wav"
    subprocess.run(["bash", str(audio_script), "--type", concept_type, "--duration", str(duration), "--out", str(out_file)])

def cmd_build(concept, copies=20, out_name=None):
    clip = BASE_DIR / "clips" / f"{concept}_22s.mp4"
    audio = BASE_DIR / "audio" / f"{concept}_mix.wav"
    
    if not clip.exists():
        print(f"Clip {clip} not found. Fetching from Pexels first...")
        cmd_fetch(concept, duration=22)
        
    if not audio.exists():
        print(f"Audio mix {audio} not found. Generating sleep audio first...")
        cmd_audio(concept, duration=1815)
        
    out = BASE_DIR / "out" / (out_name if out_name else f"regen_{concept}_10h.mp4")
    build_script = BASE_DIR / "scripts" / "build.sh"
    
    env = os.environ.copy()
    env.update({
        "CLIP": str(clip),
        "AUDIO": str(audio),
        "MODE": "xfade",
        "VXF": "2",
        "ACF": "15",
        "COPIES": str(copies),
        "OUT": str(out)
    })
    subprocess.run(["bash", str(build_script)], env=env)

def cmd_build_black(copies=20, out_name="regen_schwarz_10h.mp4"):
    audio = BASE_DIR / "audio" / "window_mix.wav"
    if not audio.exists():
        print(f"Audio mix {audio} not found. Generating master audio first...")
        cmd_audio("window", duration=1815)
        
    out = BASE_DIR / "out" / out_name
    build_script = BASE_DIR / "scripts" / "build.sh"
    
    env = os.environ.copy()
    env.update({
        "AUDIO": str(audio),
        "MODE": "black",
        "ACF": "15",
        "COPIES": str(copies),
        "OUT": str(out)
    })
    subprocess.run(["bash", str(build_script)], env=env)

def cmd_verify(file_path):
    verify_script = BASE_DIR / "scripts" / "verify.py"
    subprocess.run([sys.executable, str(verify_script), file_path])

def main():
    parser = argparse.ArgumentParser(description="Manage German Ambience Channel Pipeline")
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to run")
    
    subparsers.add_parser("status", help="Show workspace status and assets")
    subparsers.add_parser("bench", help="Benchmark local encoding speed")
    
    p_fetch = subparsers.add_parser("fetch", help="Fetch landscape clip from Pexels")
    p_fetch.add_argument("concept", choices=["window", "thunder", "car", "tent", "forest", "fire", "city", "drizzle", "study"])
    p_fetch.add_argument("--duration", type=int, default=22)
    
    p_audio = subparsers.add_parser("audio", help="Generate 1815s sleep audio")
    p_audio.add_argument("type", choices=["window", "thunder", "car", "forest", "drizzle"])
    p_audio.add_argument("--duration", type=int, default=1815)
    
    p_build = subparsers.add_parser("build", help="Build 10-hour seamless video")
    p_build.add_argument("concept", help="Concept name (e.g. window)")
    p_build.add_argument("--copies", type=int, default=20, help="Number of 1800s repeats (default 20 for 10h)")
    p_build.add_argument("--out", help="Output file name")
    
    p_black = subparsers.add_parser("build-black", help="Build 10-hour black screen video")
    p_black.add_argument("--copies", type=int, default=20)
    p_black.add_argument("--out", default="regen_schwarz_10h.mp4")
    
    p_ver = subparsers.add_parser("verify", help="Verify video file")
    p_ver.add_argument("file", help="Path to video file")
    
    args = parser.parse_args()
    
    if args.subcommand == "status" or not args.subcommand:
        cmd_status()
    elif args.subcommand == "bench":
        cmd_bench()
    elif args.subcommand == "fetch":
        cmd_fetch(args.concept, args.duration)
    elif args.subcommand == "audio":
        cmd_audio(args.type, args.duration)
    elif args.subcommand == "build":
        cmd_build(args.concept, args.copies, args.out)
    elif args.subcommand == "build-black":
        cmd_build_black(args.copies, args.out)
    elif args.subcommand == "verify":
        cmd_verify(args.file)

if __name__ == "__main__":
    main()
