"""Write the YouTube upload package: description, chapters, tags, credits.

Chapters must start at 0:00 and be at least 10 s apart, so the cut points come
from the measured manifest rather than from guessing where a section feels long.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
OUT = ROOT / "content/video2/out"

CHAPTERS = [
    (1, "Der Wecker"),
    (2, "Die Frage"),
    (5, "Das Tagesdiagramm"),
    (6, "Die Wohnung"),
    (8, "Altbau und Neubau"),
    (9, "Die Warteliste"),
    (11, "Eine Rechnung"),
    (12, "Drei Läden"),
    (13, "Vierzig Jahre"),
    (15, "Der Befund"),
]


def mmss(sec: float) -> str:
    m, s = divmod(int(round(sec)), 60)
    return f"{m}:{s:02d}"


def main() -> int:
    manifest = json.loads((BUILD / "manifest.json").read_text(encoding="utf-8"))
    credits_path = BUILD / "credits.json"
    credits = json.loads(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else []
    scenes = {s["id"]: s for s in manifest["scenes"]}

    chapters = [(0.0, "Intro")]
    for sid, label in CHAPTERS:
        if sid in scenes and scenes[sid]["start"] > 12:
            chapters.append((scenes[sid]["start"], label))
    # YouTube requires >= 10 s between chapters and >= 3 chapters
    cleaned: list[tuple[float, str]] = []
    for start, label in chapters:
        if not cleaned or start - cleaned[-1][0] >= 10:
            cleaned.append((start, label))
        else:
            cleaned[-1] = (cleaned[-1][0], cleaned[-1][1] + " & " + label)

    chapter_block = "\n".join(f"{mmss(t)} {label}" for t, label in cleaned)
    photo_block = "\n".join(
        f"– {c['title']} · {c.get('artist', 'Bundesarchiv')} · {c['license']} · Wikimedia Commons"
        for c in credits
    ) or "– Grafiken: eigenes Motion-Design (Canvas), keine Stockfootage"

    description = f"""Um 11:30 aß eine ganze Republik zu Mittag – der unsichtbare Fahrplan der DDR

Kein Mythos, sondern ein Stundenplan: Betriebskantine, Kindergarten, Kaufhalle, Feierabend. Dieses Video zeigt, wie Uhrzeiten den Alltag in der DDR prägten – und warum viele Menschen bis heute mittags warm essen.

Kapitel:
{chapter_block}

Bild- und Quellennachweis:
{photo_block}
– Fakten: Wikipedia (Betriebskantine, Plattenbau, WBS 70, Handelsorganisation, Konsum, Intershop, Trabant 601, Polytechnische Oberschule, Aufstand vom 17. Juni 1953)

Wie ist es bei Ihnen? Essen Sie mittags oder abends warm? Schreiben Sie es in die Kommentare."""
    (OUT / "video2_description.txt").write_text(description, encoding="utf-8")

    tags = [
        "DDR Alltag", "DDR Geschichte", "Plattenbau", "WBS 70", "Betriebskantine",
        "DDR Erinnerungen", "Ostdeutschland", "deutsche Geschichte", "Alltagsgeschichte",
        "Intershop", "Trabant", "17. Juni 1953", "Konsum HO", "WissenSieNoch",
    ]
    (OUT / "video2_tags.txt").write_text(", ".join(tags), encoding="utf-8")
    print(f"description: {len(description)} chars, {len(cleaned)} chapters")
    print(chapter_block)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
