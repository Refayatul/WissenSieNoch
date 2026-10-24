"""Narrate the whole film in ONE TTS call, with deterministic scene markers.

Why one call: the free tier allows ~10 requests/day per model, so per-scene calls
cannot survive iteration. Why numeric markers: the previous attempt used the
phrase "Achtung, nächster Abschnitt." and it leaked into the final video, because
TTS runs a marker straight into the next sentence. A bare number spoken alone is
short and unambiguous, so it can be found and removed reliably.

Marker format written into the text:

    ...text...  <newline> <newline> Äh, siebenundzwanzig. <newline> <newline> ...text...

Then, after rendering, the audio is transcribed once by a chat model that returns
the word timings it heard; the marker spans are cut with a short crossfade. If
the transcription cannot locate a marker, the cut is skipped and the run reports
it instead of shipping a wrong edit.

Output: build/video2/audio/scene_XX.wav + build/video2/manifest.json
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import post_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"

TTS_MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts",
              "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]

# German number words for boundaries. Each appears exactly once in the script,
# and never in the narration itself (verified by assert below).
MARKERS = [
    "siebenundzwanzig", "vierundvierzig", "dreiundsechzig", "einundachtzig",
    "sechsundneunzig", "zweiundfünfzig", "achtundsiebzig", "fünfundachtzig",
    "dreiundvierzig", "siebenundsechzig", "vierundneunzig", "sechzig",
    "einunddreißig", "dreiundsiebzig", "hundert", "sechsundvierzig",
    "achtundneunzig", "fünfundsiebzig",
]  # one per act boundary: scenes - 1

def to_wav(raw: bytes, out: Path) -> None:
    # Write Gemini audio (RIFF or raw s16le) as 48 kHz mono WAV.
    tmp = out.with_suffix(".raw")
    tmp.write_bytes(raw)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    cmd += ["-i", str(tmp)] if raw[:4] == b"RIFF" else ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(tmp)]
    subprocess.run([*cmd, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    tmp.unlink(missing_ok=True)


def normalize(path: Path) -> None:
    tmp = path.with_suffix(".norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=70", "-ar", "48000", "-ac", "1", str(tmp)], check=True)
    tmp.replace(path)


def render(text: str, out: Path, voice: str) -> str:
    for model in TTS_MODELS:
        body = {"contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
        t0 = time.time()
        try:
            reply = post_json(model, body, timeout=900)
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode(errors="replace")
            print(f"    {model}: HTTP {exc.code}{' daily' if 'PerDay' in msg or 'per day' in msg else ''}", flush=True)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"    {model}: {type(exc).__name__}", flush=True)
            continue
        parts = reply["candidates"][0]["content"]["parts"]
        part = next((p for p in parts if "inlineData" in p), None)
        if not part:
            continue
        to_wav(base64.b64decode(part["inlineData"]["data"]), out)
        normalize(out)
        print(f"    {model}: {dur(out):.1f}s audio in {time.time() - t0:.0f}s", flush=True)
        return model
    return ""


def build_text(scenes: list[dict]) -> tuple[str, list[dict]]:
    """Join scene text with spoken markers; return text + boundary plan."""
    parts, bounds = [], []
    mi = 0
    for i, sc in enumerate(scenes):
        parts.append(sc["words"].strip())
        if i < len(scenes) - 1:
            if mi >= len(MARKERS):
                raise SystemExit("not enough markers for the scene count")
            word = MARKERS[mi]
            mi += 1
            parts.append(f"\n\n{word}.\n\n")
            bounds.append({"scene": sc["id"], "marker": word})
    text = "".join(parts)
    # A marker must be unique in the whole batch, otherwise the cut point is
    # ambiguous. Count with word boundaries so "sechzig" does not match inside
    # another number word.
    for b in bounds:
        hits = re.findall(r"\b" + b["marker"] + r"\b", text.lower())
        if len(hits) != 1:
            raise SystemExit(f"marker {b['marker']} is ambiguous ({len(hits)} matches)")
    return text, bounds


def cut_at(spans: list[tuple[float, float]], src: Path, dst: Path) -> None:
    """Remove several spans in one pass, preserving the segments between them."""
    filters, labels = [], []
    cursor = 0.0
    total = dur(src)
    pieces = []
    for s, e in sorted(spans):
        if s > cursor:
            pieces.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < total:
        pieces.append((cursor, total))
    for i, (a, b) in enumerate(pieces):
        filters.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[p{i}]")
        labels.append(f"[p{i}]")
    graph = ";".join(filters) + f";{''.join(labels)}concat=n={len(pieces)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", graph,
                    "-map", "[out]", "-ar", "48000", "-ac", "1", str(dst)], check=True)


def transcribe_words(wav: Path) -> list[dict]:
    """Word timings for the whole narration (sliced). See transcribe_words.py."""
    from transcribe_words import transcribe
    return transcribe(wav)


def locate_markers(words: list[dict], markers: list[str], total: float):
    """Marker spans to delete; matches digits and words. See markers.py."""
    from markers import words_to_markers
    return words_to_markers(words, markers, total)


def main() -> int:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    AUDIO.mkdir(parents=True, exist_ok=True)
    voice = plan.get("voice", "Charon")
    scenes = plan["scenes"]

    text, bounds = build_text(scenes)
    print(f"narration: {len(scenes)} scenes, {len(text)} chars, {len(bounds)} markers")

    raw = AUDIO / "narration_raw.wav"
    if raw.exists() and raw.stat().st_size > 10000:
        print(f"  reusing rendered narration: {raw} ({dur(raw):.1f}s)")
        model = "cached"
    else:
        model = render(text, raw, voice)
        if not model:
            print("no TTS model available; keeping any cached audio")
            return 1

    total = dur(raw)
    words = transcribe_words(raw)
    if words:
        spans, missing = locate_markers(words, [b["marker"] for b in bounds], total)
        print(f"  located {len(spans)} of {len(bounds)} markers in transcript")
        if missing:
            print(f"  NOT located (audio kept, will be audible): {missing}")
    else:
        spans = []
        print("  transcription unavailable, no marker removal (markers will be audible!)")

    clean = AUDIO / "narration_clean.wav"
    if spans:
        from markers import strip_spans
        strip_spans(raw, spans, clean)
        print(f"  clean narration: {dur(clean):.1f}s (removed {total - dur(clean):.1f}s)")
    else:
        clean = raw

    # scene durations: cut the clean track at marker midpoints by proportion
    scene_ids = [s["id"] for s in scenes]
    markers_found = len(spans)
    if markers_found == len(scene_ids) - 1:
        # positions in the clean track: after each cut, boundaries shift
        bounds_clean, removed = [], 0.0
        for i, (s, e) in enumerate(sorted(spans)):
            bounds_clean.append(s - removed)
            removed += e - s
        edges = [0.0] + bounds_clean + [dur(clean)]
    else:
        c = dur(clean)
        edges = [c * i / len(scene_ids) for i in range(len(scene_ids) + 1)]

    out_scenes, t = [], 0.0
    for sid, a, b in zip(scene_ids, edges[:-1], edges[1:]):
        out = AUDIO / f"scene_{sid:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clean),
                        "-ss", f"{a:.3f}", "-to", f"{b:.3f}",
                        "-af", "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,"
                               "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.10,areverse",
                        "-ar", "48000", "-ac", "1", str(out)], check=True)
        d = max(dur(out), 2.2)
        src = next(s for s in scenes if s["id"] == sid)
        entry = {"id": sid, "type": src["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3), "wav": str(out.relative_to(ROOT))}
        entry.update({k: v for k, v in src.items() if k not in {"words", "id", "type"}})
        out_scenes.append(entry)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 30),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": voice, "tts_model": model,
                "markers_removed": markers_found, "scenes": out_scenes}
    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {len(out_scenes)} scenes, {t:.1f}s ({t / 60:.2f} min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
