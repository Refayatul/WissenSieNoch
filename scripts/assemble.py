"""Assemble the film: concat graphics segments, lay narration on top, add bed.

Steps, each verified:
  1. concat the per-scene MP4s losslessly (they share codec/params),
  2. concat the narration WAVs,
  3. mix narration with a quiet synthesised bed (no third-party music licence),
  4. mux, add a 1 s tail, and write the YouTube ingest metadata.

The audio bed is generated with ffmpeg: a low drone plus filtered noise, slowly
modulated. It is deliberately simple - royalty-free by construction - and sits
far below the voice so it never competes.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(" ".join(cmd[:6]) + "\n" + proc.stderr[-1200:])


def ffconcat_list(files: list[Path], out: Path) -> None:
    lines = ["ffconcat version 1.0"]
    for f in files:
        lines.append(f"file '{f.as_posix()}'")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_bed(path: Path, seconds: float) -> None:
    """Low, slow atmosphere under the narration; no licensed material."""
    expr_a = "0.5*sin(2*PI*55*t)+0.3*sin(2*PI*82.4*t)+0.18*sin(2*PI*110*t)"
    expr_b = "0.5*sin(2*PI*58.3*t)+0.3*sin(2*PI*87.3*t)+0.18*sin(2*PI*116.5*t)"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"aevalsrc='{expr_a}|{expr_b}':s=48000:d={seconds:.2f}",
         "-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.02:d={seconds:.2f}:s=48000",
         "-filter_complex",
         "[0:a]volume=0.045,tremolo=f=0.12:d=0.7[a0];"
         "[1:a]lowpass=f=520,highpass=f=90,volume=0.10[a1];"
         "[a0][a1]amix=inputs=2:duration=first:normalize=0,"
         f"afade=t=in:st=0:d=3,afade=t=out:st={max(0.0, seconds - 4):.2f}:d=4[out]",
         "-map", "[out]", "-c:a", "pcm_s16le", str(path)])


def main() -> int:
    manifest = json.loads((BUILD / "manifest.json").read_text(encoding="utf-8"))
    fps = manifest["fps"]
    total = manifest["duration"]

    segs = [BUILD / "segments" / f"scene_{s['id']:02d}.mp4" for s in manifest["scenes"]]
    missing = [s.name for s in segs if not s.exists()]
    if missing:
        raise SystemExit("missing segments: " + ", ".join(missing))

    # 1. video
    vlist = BUILD / "video_concat.txt"
    ffconcat_list(segs, vlist)
    video = BUILD / "video_only.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(vlist),
         "-c", "copy", str(video)])

    # 2. narration
    wavs = [ROOT / s["wav"] for s in manifest["scenes"]]
    alist = BUILD / "audio_concat.txt"
    ffconcat_list(wavs, alist)
    voice = BUILD / "voice.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(alist),
         "-ar", "48000", "-ac", "1", str(voice)])

    # 3. bed sized to the measured narration + 1 s tail
    bed = BUILD / "bed.wav"
    make_bed(bed, total + 1.0)

    # 4. mix + mux
    out = ROOT / "content/video2/out" / "video2_ddr_alltag.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(voice), "-i", str(bed),
         "-filter_complex",
         "[1:a]apad=pad_dur=1,asplit=2[v1][v2];"
         "[v1]loudnorm=I=-16:TP=-1.5:LRA=11[voice];"
         "[v2]highpass=f=90,lowpass=f=9000,agate=threshold=0.02:ratio=2[duck];"
         "[2:a][duck]sidechaincompress=threshold=0.05:ratio=6:attack=25:release=450[comp];"
         "[voice][comp]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.97[mix]",
         "-map", "0:v", "-map", "[mix]", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         "-shortest", "-movflags", "+faststart", str(out)])

    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration,size:stream=codec_name,width,height,r_frame_rate",
                            "-of", "json", str(out)], capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    summary = {
        "file": str(out.relative_to(ROOT)),
        "duration_s": round(float(info["format"]["duration"]), 2),
        "size_mb": round(int(info["format"]["size"]) / 1e6, 1),
        "streams": info["streams"],
        "scenes": len(manifest["scenes"]),
        "voice": manifest["voice"],
        "tts_models": manifest.get("tts_models", []),
    }
    (BUILD / "render_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
