"""Transcribe a long WAV in slices with retries.

Two bugs found by inspecting real output:
  * one request over 3.6 minutes returned no usable JSON, so every marker past
    ~60 s was "not found"
  * the transcriber writes numbers as digits ("27."), which markers.py handles

This module fixes the first: 30 s slices, two attempts per slice, and a report
for slices that produce nothing.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import post_json  # noqa: E402

SLICE = 30.0
OVERLAP = 1.0
PROMPT = ("Transkribiere das Audio wörtlich. Gib NUR eine JSON-Liste zurück, je Objekt "
          '{"word": "...", "start": <Sekunden seit Beginn dieses Audios>}. Keine Erklärung.')
MODELS = ("gemini-flash-lite-latest", "gemini-flash-latest")  # verified to accept audio, 2026-10-24


def dur(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                 "-of", "csv=p=0", str(p)], capture_output=True, text=True,
                                check=True).stdout.strip())


def parse(text: str) -> list[dict]:
    m = re.search(r"\[.*\]", text, re.S)
    if not m:
        return []
    try:
        raw = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for w in raw:
        if isinstance(w, dict) and "word" in w and "start" in w:
            try:
                out.append({"word": str(w["word"]), "start": float(w["start"])})
            except (TypeError, ValueError):
                continue
    return out


def slice_words(wav: Path, start: float, length: float, tmpdir: Path) -> list[dict]:
    seg = tmpdir / ("seg_" + str(int(start * 10)) + ".wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                    "-i", str(wav), "-ar", "16000", "-ac", "1", str(seg)], check=True)
    b64 = base64.b64encode(seg.read_bytes()).decode()
    body = {"contents": [{"parts": [{"text": PROMPT},
                                    {"inlineData": {"mimeType": "audio/wav", "data": b64}}]}],
            "generationConfig": {"temperature": 0}}
    for model in MODELS:
        for attempt in range(3):
            try:
                reply = post_json(model, body, timeout=180)
            except Exception:  # noqa: BLE001
                time.sleep(2 + attempt * 2)
                continue
            parts = reply["candidates"][0]["content"]["parts"]
            text = parts[0].get("text", "") if parts else ""
            words = parse(text)
            if words:
                return [{"word": w["word"], "start": w["start"] + start} for w in words]
            time.sleep(1)
    return []


def transcribe(wav: Path) -> list[dict]:
    total = dur(wav)
    words: list[dict] = []
    t = 0.0
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        while t < total - 1.0:
            chunk = slice_words(wav, t, min(SLICE, total - t), tmpdir)
            if not chunk:
                print(f"    slice at {t:.0f}s: no transcript", flush=True)
            if words and chunk:
                last = words[-1]["start"]
                chunk = [w for w in chunk if w["start"] > last + 0.05]
            words.extend(chunk)
            t += SLICE - OVERLAP
    print(f"    transcribed {len(words)} words over {total:.0f}s", flush=True)
    return words
