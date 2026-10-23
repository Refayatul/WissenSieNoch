"""Fetch a small, licensed photo set for video 2 from Wikimedia Commons.

The first video leaned on archive stills; this one leans on graphics, so photos
are used sparingly - as texture behind the narration, never as the main event.
Only Bundesarchiv (Bild 183) material under CC BY-SA 3.0 de is accepted, the
licence and author are recorded for the video description, and each image is
converted to a data URL so the headless renderer never needs network access.
"""
from __future__ import annotations

import base64
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/video2"
UA = {"User-Agent": "WissenSieNoch/1.0 (educational video pipeline; contact via repo)"}

# key -> (search query, minimum year, prefer these words anywhere in the title)
WANTED = {
    "kantine": ("Bundesarchiv Bild 183 Betriebskantine", 1950, ["kantine", "speisesaal", "gaststätte"]),
    "platte": ("Bundesarchiv Bild 183 Neubaugebiet Wohnungsbau", 1965, ["neubau", "platten", "wohnungsbau", "wohngebiet"]),
}


def clean_html(raw: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", "", raw or "").split()).strip()


def search_commons(query: str, limit: int = 20) -> list[dict]:
    params = {
        "action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": 6,
        "gsrlimit": limit, "prop": "imageinfo", "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": 1600, "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pages = json.load(resp).get("query", {}).get("pages", {})
            return list(pages.values())
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                time.sleep(4 * (attempt + 1))
                continue
            return []
        except Exception:  # noqa: BLE001 - network variance must not kill the build
            time.sleep(3)
    return []


def pick(pages: list[dict], prefer: list[str], min_year: int) -> dict | None:
    for page in pages:
        title = page.get("title", "")
        if "Bild 183" not in title:
            continue
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        meta = info.get("extmetadata", {})
        blob = " ".join([
            title,
            clean_html(meta.get("ImageDescription", {}).get("value", "")),
            clean_html(meta.get("Categories", {}).get("value", "")),
        ]).lower()
        years = [int(y) for y in re.findall(r"\b(19[4-9]\d)\b", blob)]
        year = max(years) if years else 0
        if year and year < min_year:
            continue
        if prefer and not any(w in blob for w in prefer):
            continue
        license_name = clean_html(meta.get("LicenseShortName", {}).get("value", ""))
        if "CC BY-SA 3.0 de" not in license_name and "CC BY-SA 3.0" not in license_name:
            continue
        return {
            "title": title,
            "url": info.get("thumburl") or info.get("url"),
            "artist": clean_html(meta.get("Artist", {}).get("value", "")) or "Bundesarchiv",
            "license": license_name,
            "year": year,
            "page": info.get("descriptionurl", ""),
        }
    return None


def download(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return resp.read()
        except Exception:  # noqa: BLE001
            time.sleep(2 + attempt * 3)
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    photo_dir = OUT / "photos"
    photo_dir.mkdir(exist_ok=True)
    registry: dict[str, str] = {}
    credits: list[dict] = []
    for key, (query, min_year, prefer) in WANTED.items():
        cache = OUT / f"image_{key}.dataurl"
        meta_path = OUT / f"image_{key}.json"
        if cache.exists() and meta_path.exists():
            registry[key] = cache.read_text()
            credits.append(json.loads(meta_path.read_text()))
            print(f"  {key}: cached")
            continue
        print(f"  {key}: searching '{query}'", flush=True)
        best = pick(search_commons(query), prefer, min_year)
        if not best:
            print(f"  {key}: no matching CC BY-SA Bundesarchiv image, skipping (graphics only)")
            continue
        raw = download(best["url"])
        if not raw:
            print(f"  {key}: download failed, skipping")
            continue
        (photo_dir / f"{key}.jpg").write_bytes(raw)
        mime = "image/png" if raw[:4] == b"\x89PNG" else "image/jpeg"
        cache.write_text(f"data:{mime};base64," + base64.b64encode(raw).decode())
        meta_path.write_text(json.dumps(best, ensure_ascii=False, indent=2), encoding="utf-8")
        registry[key] = cache.read_text()
        credits.append(best)
        print(f"  {key}: {best['title'][:60]} ({best['year']}) {best['license']}")
        time.sleep(1.5)

    (OUT / "images.json").write_text(json.dumps(registry), encoding="utf-8")
    (OUT / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"images ready: {len(registry)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
