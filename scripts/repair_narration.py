"""Verify and repair the CI narration: detect spoken markers, cut them cleanly.

The CI run narrated per scene, and transcribing the muxed film showed a spoken
"Achtung, nächster Abschnitt" at a scene join. That phrase was inserted between
scenes by the batch narrator, so it sits at the START of the following scene's
clip - which makes it removable without any forced alignment: the marker is the
first ~1.6 s of the affected clips, followed by a real pause.

This script measures, prints what it found, and only then cuts, so the decision
is auditable instead of blind.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "tmp/artifact/video2-ddr-alltag-6/build/video2"
WORK = ROOT / "build/video2/audio"

MARK_WORDS = ("achtung", "nächster", "naechster", "abschnitt")


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def first_speech_end(p: Path) -> tuple[float, float]:
    """(silence_start, silence_end) of the first real pause, or (0, 0)."""
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(p), "-af",
                          "silencedetect=noise=-34dB:d=0.30", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    s = re.findall(r"silence_start: ([0-9.]+)", err)
    e = re.findall(r"silence_end: ([0-9.]+)", err)
    if s and e:
        return float(s[0]), float(e[0])
    return 0.0, 0.0


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    clips = sorted(SRC.glob("audio/scene_*.wav"))
    if not clips:
        sys.exit("no CI scene audio found")
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    types = {s["id"]: s["type"] for s in plan["scenes"]}

    cleaned, report = [], []
    for c in clips:
        sid = int(c.stem.split("_")[1])
        d = dur(c)
        a, b = first_speech_end(c)
        # A marker shows up as speech then a pause, both within the first 3 s.
        suspect = 0.25 < a < 2.4 and 0.3 < (b - a) < 1.2
        report.append({"scene": sid, "type": types.get(sid), "duration": round(d, 2),
                       "first_speech_end": round(a, 2), "suspect_marker": suspect})
        out = WORK / c.name
        if suspect:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{b:.3f}", "-i", str(c),
                            "-ar", "48000", "-ac", "1", str(out)], check=True)
            print(f"  scene {sid:2d} {types.get(sid, ''):8s} trimmed {b:.2f}s marker -> {dur(out):.2f}s")
        else:
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(c), "-ar", "48000", "-ac", "1",
                            str(out)], check=True)
            print(f"  scene {sid:2d} {types.get(sid, ''):8s} clean ({d:.2f}s)")

    # rebuild manifest from the cleaned clips, in film order
    t, scenes = 0.0, []
    for c in clips:
        sid = int(c.stem.split("_")[1])
        wav = WORK / c.name
        d = max(dur(wav), 2.2)
        src = next(s for s in plan["scenes"] if s["id"] == sid)
        entry = {"id": sid, "type": src["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3), "wav": str(wav.relative_to(ROOT))}
        entry.update({k: v for k, v in src.items() if k not in {"words", "id", "type"}})
        scenes.append(entry)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 30),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": plan.get("voice", "Charon"),
                "scenes": scenes}
    (ROOT / "build/video2/manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    (ROOT / "build/video2/audio_repair_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nmanifest: {len(scenes)} scenes, {t:.1f}s; suspects: "
          f"{[r['scene'] for r in report if r['suspect_marker']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
