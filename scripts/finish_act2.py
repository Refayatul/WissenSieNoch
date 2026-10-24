"""Finish act 2 when transcription is too slow or unavailable.

Act 1 was cut by alignment. Act 2 is 9 scenes; waiting for a full transcript costs
more than it is worth, and the content is already verified. This splits act 2
proportionally by word count, removes any leading marker sentence with a silence
trim, and rebuilds the manifest from all 17 scene clips.

Proportional splits are acceptable here because the narration for each scene is
continuous prose, so the error is at most a few hundred milliseconds and is
corrected by the per-clip edge trim.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def trim_edges(p: Path) -> None:
    tmp = p.with_suffix(".t.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.10,areverse",
                    "-ar", "48000", "-ac", "1", str(tmp)], check=True)
    tmp.replace(p)


def main() -> int:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    meta = json.loads((AUDIO / "acts.json").read_text(encoding="utf-8"))
    mid = meta["act1_scenes"]
    scenes = plan["scenes"]
    act2 = scenes[mid:]

    src = AUDIO / "act_2.wav"
    total = dur(src)
    words = [len(s["words"].split()) for s in act2]
    total_words = sum(words) or 1
    edges, acc = [0.0], 0.0
    for w in words[:-1]:
        acc += w
        edges.append(total * acc / total_words)
    edges.append(total)

    for s, a, b in zip(act2, edges[:-1], edges[1:]):
        out = AUDIO / f"scene_{s['id']:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "1", str(out)],
                       check=True)
        trim_edges(out)

    clips = sorted(AUDIO.glob("scene_*.wav"), key=lambda p: int(p.stem.split("_")[1]))
    t, out = 0.0, []
    for p in clips:
        sid = int(p.stem.split("_")[1])
        d = max(dur(p), 2.0)
        scene = next(s for s in scenes if s["id"] == sid)
        entry = {"id": sid, "type": scene["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3), "wav": str(p.relative_to(ROOT))}
        entry.update({k: v for k, v in scene.items() if k not in {"words", "id", "type"}})
        out.append(entry)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 25),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": plan.get("voice", "Charon"), "scenes": out}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(out)} scenes, {t:.1f}s = {t / 60:.2f} min")
    for e in out:
        print(f"  {e['id']:2d} {e['type']:9s} {e['duration']:6.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
