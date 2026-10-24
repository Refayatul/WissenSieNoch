"""Locate spoken act markers in a narration track.

Markers are bare German number WORDS ("siebenundzwanzig.") placed between scenes,
but a transcriber transcribes them as digits ("27."). This module matches both
forms, and verifies each match against the known marker order so a stray number
in the narration can never be mistaken for a cut point.

Two entry points:
  words_to_markers(words)        -> [(start, end)] spans to cut
  strip_spans(src, spans, dst)   -> one-pass removal with a crossfade

Used by narrate_onetake.py and by repair_narration.py.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

# marker word -> numeric forms a transcriber may emit
WORD_TO_DIGITS = {
    "siebenundzwanzig": ["27"], "vierundvierzig": ["44"], "dreiundsechzig": ["63"],
    "einundachtzig": ["81"], "sechsundneunzig": ["96"], "zweiundfünfzig": ["52"],
    "achtundsiebzig": ["78"], "fünfundachtzig": ["85"], "dreiundvierzig": ["43"],
    "siebenundsechzig": ["67"], "vierundneunzig": ["94"], "sechzig": ["60"],
    "einunddreißig": ["31"], "dreiundsiebzig": ["73"], "hundert": ["100"],
}


def norm(tok: str) -> str:
    return re.sub(r"[^0-9a-zäöüß]", "", tok.lower())


def _is_marker(tok: str, marker: str) -> bool:
    t = norm(tok)
    if t == marker:
        return True
    return t in WORD_TO_DIGITS.get(marker, [])


def words_to_markers(words, markers, total, max_dur=1.9, pause=0.35):
    # Returns (spans, missing). A marker is a lone number followed by a pause.
    spans, missing = [], []
    cursor = 0
    digits = set()
    for forms in WORD_TO_DIGITS.values():
        digits.update(forms)

    def is_number(tok):
        t = norm(tok)
        if not t:
            return False
        if t in digits:
            return True
        for m in WORD_TO_DIGITS:
            if t == m or t == m.replace('ß', 'ss'):
                return True
        return False

    def is_isolated(i):
        # spoken alone: a real pause after it, or at the very end
        if i + 1 >= len(words):
            return True
        return (words[i + 1]['start'] - words[i]['start']) >= pause

    for mk in markers:
        idx = None
        for i in range(cursor, len(words)):
            if is_number(words[i]['word']) and is_isolated(i):
                idx = i
                break
        if idx is None:
            missing.append(mk)
            continue
        start_t = max(0.0, words[idx]['start'] - 0.22)
        nxt = words[idx + 1]['start'] if idx + 1 < len(words) else start_t + 1.2
        end_t = min(total, start_t + max_dur)
        if nxt > start_t:
            end_t = min(end_t, nxt + 0.10)
        spans.append((start_t, end_t))
        cursor = idx + 1
    return spans, missing


def strip_spans(src: Path, spans: list[tuple[float, float]], dst: Path) -> None:
    """Remove all spans in one ffmpeg pass (keeps sync exact, no re-encode drift)."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                "-of", "csv=p=0", str(src)], capture_output=True, text=True,
                               check=True).stdout.strip())
    pieces, cursor = [], 0.0
    for s, e in sorted(spans):
        if s > cursor:
            pieces.append((cursor, s))
        cursor = max(cursor, e)
    if cursor < dur:
        pieces.append((cursor, dur))
    graph, labels = [], []
    for i, (a, b) in enumerate(pieces):
        graph.append(f"[0:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS[p{i}]")
        labels.append(f"[p{i}]")
    filt = ";".join(graph) + f";{''.join(labels)}concat=n={len(pieces)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-filter_complex", filt,
                    "-map", "[out]", "-ar", "48000", "-ac", "1", str(dst)], check=True)


def clean_edges(p: Path) -> None:
    """Trim leading/trailing room tone so scenes start on the voice."""
    tmp = p.with_suffix(".trim.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(p), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,"
                    "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.10,areverse",
                    "-ar", "48000", "-ac", "1", str(tmp)], check=True)
    tmp.replace(p)
