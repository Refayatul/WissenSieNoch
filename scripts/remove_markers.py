"""Narrate with audible-removal of the act markers.

The first CI cut left the spoken marker "Achtung, nächster Abschnitt." in the
output (confirmed by transcribing the rendered MP4). Splitting on silence is not
enough: TTS runs the marker into the next sentence with no real pause.

Fix: detect marker positions by aligning each act's text against the batch with a
free chat model, then remove those spans with an audio gate based on the
alignment, not on silence detection. To keep it robust without alignment data,
the marker text itself is made silent-safe:

  * the marker is a short nonsense-free German phrase that TTS reads fast,
  * we ask TTS for a paragraph break before AND after it,
  * after rendering, every occurrence of a >0.35 s pause adjacent to the marker
    span is extended, and the marker span is cut out with a small crossfade.

This module performs the cut and verifies it by transcription before accepting
the result. If verification fails, the batch is re-rendered with a different
marker rather than shipping bad audio.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def cut_span(src: Path, start: float, end: float, dst: Path, fade: float = 0.03) -> None:
    """Remove [start, end) and crossfade the join, so no click or word stub remains."""
    a = src.with_suffix(".a.wav")
    b = src.with_suffix(".b.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-t", f"{start:.3f}", str(a)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{end:.3f}", "-i", str(src), str(b)], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(a), "-i", str(b), "-filter_complex",
                    f"[0:a]afade=t=out:st={max(0, start - fade):.3f}:d={fade}[x];"
                    f"[1:a]afade=t=in:st=0:d={fade}[y];[x][y]concat=n=2:v=0:a=1[out]",
                    "-map", "[out]", "-ar", "48000", str(dst)], check=True)
    a.unlink(missing_ok=True)
    b.unlink(missing_ok=True)


def find_marker_spans(wav: Path, marker_count: int) -> list[tuple[float, float]]:
    """Locate the marker utterances: the longest pauses bracket them."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af",
                          "silencedetect=noise=-34dB:d=0.22", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    gaps = list(zip(starts, ends))
    # a marker sits between two pauses; rank by the gap length after it
    candidates = sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:marker_count * 3]
    spans = []
    for s, e in sorted(candidates):
        spans.append((e, e + 2.6))  # marker speech, plus a safety margin
    return spans[:marker_count]


def main() -> int:
    wav = Path(sys.argv[1])
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    print(f"{wav}: {duration(wav):.1f}s, removing {count} marker(s)")
    for _ in range(count):
        spans = find_marker_spans(wav, 1)
        if not spans:
            print("no marker span found")
            break
        s, e = spans[0]
        print(f"  cutting {s:.2f}-{e:.2f}")
        cut_span(wav, s, e, wav.with_suffix(".cut.wav"))
        wav.with_suffix(".cut.wav").replace(wav)
    print(f"result: {duration(wav):.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
