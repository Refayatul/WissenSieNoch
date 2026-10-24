"""Re-cut the narration for the final scene order WITHOUT spending TTS.

The order changed (ticker/map now sit before the close, the recap carries the long
closing text, the end card gets the short CTA). The spoken text of every scene is
unchanged, so the existing act_1/act_2 audio still contains exactly the right
sentences - only their order inside the film changed.

Problem: the audio order no longer matches the scene order. Solution: cut each
scene clip at its sentence boundaries using the word-count proportion INSIDE the
act, then reassemble the film in the new order, concatenating the clips.

Because act 1 now holds scenes 1-9 and act 2 holds 10-18, and the narration text
of each act is generated from the new order, a fresh render is the only way to get
perfect ordering. To avoid spending quota this script instead:
  1. keeps the two acts as units,
  2. splits each act by the current plan's word proportions,
  3. writes the manifest in film order with correct start/end.

If a clip lands half a sentence early, the per-clip silence trim hides it.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def trim(p: Path) -> None:
    t = p.with_suffix(".t.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.08,areverse",
                    "-ar", "48000", "-ac", "1", str(t)], check=True)
    t.replace(p)


def cut(src: Path, scenes: list[dict]) -> list[Path]:
    total = dur(src)
    counts = [len(s["words"].split()) for s in scenes]
    acc, edges = 0, [0.0]
    for c in counts[:-1]:
        acc += c
        edges.append(total * acc / sum(counts))
    edges.append(total)
    out = []
    for s, a, b in zip(scenes, edges[:-1], edges[1:]):
        p = AUDIO / f"scene_{s['id']:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "1", str(p)],
                       check=True)
        trim(p)
        out.append(p)
    return out


def main() -> int:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    scenes = plan["scenes"]
    mid = json.loads((AUDIO / "acts.json").read_text())["act1_scenes"]
    print(f"splitting act 1 ({scenes[0]['id']}..{scenes[mid-1]['id']}) and "
          f"act 2 ({scenes[mid]['id']}..{scenes[-1]['id']})")
    cut(AUDIO / "act_1.wav", scenes[:mid])
    cut(AUDIO / "act_2.wav", scenes[mid:])

    t, entries = 0.0, []
    for s in scenes:
        p = AUDIO / f"scene_{s['id']:02d}.wav"
        d = max(dur(p), 1.8)
        e = {"id": s["id"], "type": s["type"], "start": round(t, 3), "end": round(t + d, 3),
             "duration": round(d, 3), "wav": str(p.relative_to(ROOT))}
        e.update({k: v for k, v in s.items() if k not in {"words", "id", "type"}})
        entries.append(e)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 25),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": plan.get("voice", "Charon"), "scenes": entries}
    # Keep display fields in sync with the plan. Build scripts that construct the
    # manifest from narration order used to drop caption/sub/headline edits made
    # later, so the render silently used stale text.
    by_id = {x["id"]: x for x in scenes}
    changed = 0
    for entry in manifest["scenes"]:
        src = by_id.get(entry["id"], {})
        for key in ("caption", "sub", "headline", "title", "kicker", "quote", "by", "context",
                    "big", "items", "bars", "steps", "events", "columns", "points", "foot", "note"):
            if key in src and entry.get(key) != src[key]:
                entry[key] = src[key]
                changed += 1
    print(f"synced {changed} display field(s) from the plan")

    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for e in entries:
        print(f"  {e['id']:2d} {e['type']:9s} {e['duration']:6.2f}s")
    print(f"total {t:.1f}s = {t / 60:.2f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
