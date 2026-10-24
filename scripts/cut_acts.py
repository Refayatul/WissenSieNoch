"""Cut the marker out of each act and derive scene timings from the audio.

Input:  build/video2/audio/act_1.wav, act_2.wav, acts.json
Output: build/video2/audio/scene_XX.wav + build/video2/manifest.json

Method: each act contains scene texts separated by one known marker sentence.
The marker's position is found by transcript alignment (fallback: proportional),
then removed with a one-pass ffmpeg cut. Scene durations come from the measured
audio, never from an estimate.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_markers import find_markers  # noqa: E402
from markers import clean_edges, strip_spans  # noqa: E402
from transcribe_words import transcribe  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def split_act(act_path: Path, scenes: list[dict], marker: str, words_cache: Path) -> list[Path]:
    """Remove the marker(s), then split the act into one WAV per scene."""
    total = dur(act_path)
    if words_cache.exists():
        words = json.loads(words_cache.read_text(encoding="utf-8"))
    else:
        words = transcribe(act_path)
        words_cache.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")

    markers = [marker] * (len(scenes) - 1)
    # reuse the alignment heuristic with the act's own scene texts
    pairs = [[s] for s in scenes]
    spans, missing = find_markers([{"words": s["words"]} for s in scenes], markers, words, total)
    print(f"  {act_path.name}: {len(scenes)} scenes, {len(spans)} boundaries "
          f"({'ok' if not missing else 'proportional fallback ' + str(len(missing))})")

    clean = act_path.with_name(act_path.stem + "_clean.wav")
    if spans:
        strip_spans(act_path, spans, clean)
    else:
        clean = act_path
    clean_dur = dur(clean)

    if spans:
        bounds, removed = [], 0.0
        for s, e in sorted(spans):
            bounds.append(s - removed)
            removed += e - s
        # the proportional share of the marker free track, anchored by the cuts
        acc, total_words, shares = 0.0, sum(len(s["words"].split()) for s in scenes), []
        for s in scenes[:-1]:
            acc += len(s["words"].split())
            shares.append(clean_dur * acc / total_words)
        # blend measured cut position with the proportional estimate
        bounds = [0.6 * b + 0.4 * p for b, p in zip(bounds, shares)]
    else:
        acc, total_words, out = 0.0, sum(len(s["words"].split()) for s in scenes), []
        for s in scenes[:-1]:
            acc += len(s["words"].split())
            out.append(clean_dur * acc / total_words)
        bounds = out

    edges = [0.0] + sorted(bounds) + [clean_dur]
    out_paths = []
    for s, a, b in zip(scenes, edges[:-1], edges[1:]):
        out = AUDIO / f"scene_{s['id']:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "1", str(out)],
                       check=True)
        clean_edges(out)
        out_paths.append(out)
    clean.unlink(missing_ok=True) if clean != act_path else None
    return out_paths


def main() -> int:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    meta = json.loads((AUDIO / "acts.json").read_text(encoding="utf-8"))
    mid = meta["act1_scenes"]
    scenes = plan["scenes"]

    clips = []
    clips += split_act(AUDIO / "act_1.wav", scenes[:mid], meta["marker"], BUILD / "words_act1.json")
    clips += split_act(AUDIO / "act_2.wav", scenes[mid:], meta["marker"], BUILD / "words_act2.json")

    order = {s["id"]: s for s in scenes}
    clips.sort(key=lambda p: int(p.stem.split("_")[1]))
    t, out = 0.0, []
    for p in clips:
        sid = int(p.stem.split("_")[1])
        d = max(dur(p), 2.0)
        src = order[sid]
        entry = {"id": sid, "type": src["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3), "wav": str(p.relative_to(ROOT))}
        entry.update({k: v for k, v in src.items() if k not in {"words", "id", "type"}})
        out.append(entry)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 25),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": plan.get("voice", "Charon"), "scenes": out}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    for e in out:
        print(f"  {e['id']:2d} {e['type']:9s} {e['duration']:6.2f}s")
    print(f"total {t:.1f}s = {t / 60:.2f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
