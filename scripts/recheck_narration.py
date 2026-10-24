"""Test marker alignment on the real narration, then write the corrected manifest.

Run: python3 scripts/recheck_narration.py
- transcribes (or reuses) the raw narration
- aligns markers by context similarity, falls back to proportional timing
- cuts markers, splits into scene clips, writes build/video2/manifest.json
- prints per-scene durations so the result can be sanity-checked at a glance
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_markers import expected_marker_share, find_markers  # noqa: E402
from markers import clean_edges, strip_spans  # noqa: E402
from transcribe_words import transcribe  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"
RAW = AUDIO / "narration_raw.wav"
WORDS_CACHE = BUILD / "words.json"


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def main() -> int:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    scenes = plan["scenes"]
    from narrate_onetake import MARKERS  # reuse the same marker list
    markers = MARKERS[: len(scenes) - 1]
    total = dur(RAW)

    if WORDS_CACHE.exists():
        words = json.loads(WORDS_CACHE.read_text(encoding="utf-8"))
        print(f"reusing transcript: {len(words)} words")
    else:
        words = transcribe(RAW)
        WORDS_CACHE.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")

    spans, missing = find_markers(scenes, markers, words, total)
    print(f"aligned {len(spans)}/{len(markers)} markers; missing: {missing}")

    # fill gaps proportionally so every scene boundary exists
    share = expected_marker_share(scenes, markers, total)
    filled = sorted(set([round(s, 3) for s, _ in spans] +
                        [round(share[i], 2) for i, mk in enumerate(markers) if mk in missing]))
    # cut only real marker audio; place boundaries proportionally where unknown
    clean = AUDIO / "narration_clean.wav"
    if spans:
        strip_spans(RAW, spans, clean)
        print(f"removed {total - dur(clean):.1f}s of marker audio -> {dur(clean):.1f}s")
    else:
        clean = RAW

    # boundary times in the CLEAN track
    removed_before, bounds = 0.0, []
    for s, e in sorted(spans):
        removed_before += e - s
    for i, mk in enumerate(markers):
        if any(abs(s - share[i]) < 0.01 for s, _ in spans):
            bounds.append(share[i])
        else:
            # shift the proportional estimate by the audio removed before it
            cut_before = sum(e - s for s, e in spans if s < share[i])
            bounds.append(share[i] - cut_before)
    bounds = sorted(bounds)

    ids = [s["id"] for s in scenes]
    edges = [0.0] + bounds + [dur(clean)]
    out_scenes, t = [], 0.0
    for sid, a, b in zip(ids, edges[:-1], edges[1:]):
        out = AUDIO / f"scene_{sid:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-ar", "48000", "-ac", "1", str(out)], check=True)
        clean_edges(out)
        d = max(dur(out), 2.2)
        src = next(s for s in scenes if s["id"] == sid)
        entry = {"id": sid, "type": src["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3), "wav": str(out.relative_to(ROOT))}
        entry.update({k: v for k, v in src.items() if k not in {"words", "id", "type"}})
        out_scenes.append(entry)
        t += d
        print(f"  {sid:2d} {src['type']:9s} {d:6.2f}s")

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 30),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": plan.get("voice", "Charon"),
                "markers_aligned": len(spans), "scenes": out_scenes}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {len(out_scenes)} scenes, {t:.1f}s ({t / 60:.2f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
