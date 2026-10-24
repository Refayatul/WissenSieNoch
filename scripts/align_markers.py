"""Align the known script against the transcript to find markers by position.

Transcription is lossy (469 words kept of ~600), so counting words per scene and
hoping the markers survive is unreliable. But the script itself is known exactly.
Strategy:
  1. build the expected word sequence: each scene's words, then its marker word
  2. match expected markers to transcript positions by local text similarity
     (the words just before/after the marker in the script must appear near the
     candidate position in the transcript)
  3. fall back to proportional timing for any marker whose context is missing,
     which is still far better than "not found"
This is robust to dropped words, spelled-out years and numeric formatting.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

WORD_RE = re.compile(r"[0-9A-Za-zÄÖÜäöüß]+")


def tokens(text: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(text)]


def find_markers(script_scenes: list[dict], markers: list[str], words: list[dict], total: float):
    """Return (spans, missing) where spans are delete ranges for each marker."""
    heard = [w["word"].lower().strip(".,!?;:") for w in words]
    starts = [w["start"] for w in words]
    spans, missing = [], []

    # expected context around each marker: last 6 words of its scene, first 6 of next
    for i, mk in enumerate(markers):
        before = tokens(script_scenes[i]["words"])[-6:]
        after = tokens(script_scenes[i + 1]["words"])[:6]
        best, best_score = None, 0.0
        # a marker sits between the two contexts; scan candidates once
        for j in range(len(heard)):
            if j < 2 or j > len(heard) - 3:
                continue
            window_before = heard[max(0, j - 12): j]
            window_after = heard[j + 1: j + 13]
            score = (difflib.SequenceMatcher(None, before, window_before[-6:]).ratio() * 0.5
                     + difflib.SequenceMatcher(None, after, window_after[:6]).ratio() * 0.5)
            if score > best_score:
                best, best_score = j, score
        if best is None or best_score < 0.45:
            missing.append(mk)
            continue
        s = max(0.0, starts[best] - 0.25)
        e = min(total, s + 1.9)
        spans.append((s, e))
    return spans, missing


def expected_marker_share(script_scenes: list[dict], markers: list[str], total: float) -> list[float]:
    """Proportional estimate of each marker's start, used only as a fallback."""
    lengths, acc, out = [], 0, []
    for i, sc in enumerate(script_scenes):
        lengths.append(len(sc["words"]))
        acc += len(sc["words"])
        if i < len(markers):
            out.append(acc)
    chars_total = sum(lengths) or 1
    return [total * c / chars_total for c in out]
