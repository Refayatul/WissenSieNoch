#!/usr/bin/env python3
"""Fetch historical Bundesarchiv Bild 183 images from Wikimedia Commons for Video 1.
Uses thumb.wikimedia.org 500px standard CDN to avoid rate limiting."""
import json, re, pathlib, time, urllib.parse, urllib.request, urllib.error

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://commons.wikimedia.org/"
}
img_dir = pathlib.Path("images")
img_dir.mkdir(exist_ok=True)

CATEGORIES = [
    ("Hook", "Bundesarchiv Bild 183 Alltag DDR", 5),
    ("Hook", "Bundesarchiv Bild 183 Berlin Hauptstadt", 4),
    ("Wohnen", "Bundesarchiv Bild 183 Plattenbau", 7),
    ("Wohnen", "Bundesarchiv Bild 183 Wohnungsbau", 5),
    ("Wohnen", "Bundesarchiv Bild 183 Neubauwohnung", 4),
    ("Arbeit", "Bundesarchiv Bild 183 Brigade sozialistische", 6),
    ("Arbeit", "Bundesarchiv Bild 183 Arbeiter VEB", 5),
    ("Arbeit", "Bundesarchiv Bild 183 Arbeiterin DDR", 5),
    ("Einkaufen", "Bundesarchiv Bild 183 Kaufhalle", 5),
    ("Einkaufen", "Bundesarchiv Bild 183 Konsum", 4),
    ("Einkaufen", "Bundesarchiv Bild 183 Trabant", 5),
    ("Einkaufen", "Bundesarchiv Bild 183 Zwickau Sachsenring", 3),
    ("Kinder", "Bundesarchiv Bild 183 Schule DDR", 5),
    ("Kinder", "Bundesarchiv Bild 183 Pionier", 5),
    ("Kinder", "Bundesarchiv Bild 183 Kindergarten DDR", 4),
    ("Kinder", "Bundesarchiv Bild 183 Kinderkrippe", 3),
    ("Freizeit", "Bundesarchiv Bild 183 Datsche", 4),
    ("Freizeit", "Bundesarchiv Bild 183 Kleingarten", 4),
    ("Freizeit", "Bundesarchiv Bild 183 Ostsee Urlaub", 5),
    ("Freizeit", "Bundesarchiv Bild 183 Thüringer Wald", 4),
    ("Freizeit", "Bundesarchiv Bild 183 Sandmännchen", 3),
    ("Ausklang", "Bundesarchiv Bild 183 Feierabend", 4),
    ("Ausklang", "Bundesarchiv Bild 183 Straße DDR", 4)
]

def clean_html(raw):
    if not raw: return ""
    clean = re.sub(r"<[^>]+>", "", raw)
    return " ".join(clean.split()).strip()

def search_commons(query, limit=15):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|size|extmetadata|mime",
        "iiurlwidth": 1440,
        "format": "json"
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "WissenSieNoch-query/0.1 (app@example.com)"})
    for attempt in range(5):
        try:
            time.sleep(1.0 + attempt * 2)
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.load(resp)
            pages = data.get("query", {}).get("pages", {})
            return list(pages.values())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(5.0 * (attempt + 1))
                continue
            return []
        except Exception:
            return []
    return []

def download_thumb(url, dest_path):
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(3):
        try:
            time.sleep(0.3)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            dest_path.write_bytes(data)
            return True
        except Exception as e:
            time.sleep(2.0 * (attempt + 1))
    return False

collected_shots = []
seen_titles = set()
shot_idx = 1

for chapter, query, target in CATEGORIES:
    print(f"Searching for {chapter} ({query})...")
    results = search_commons(query, limit=target * 3)
    count_for_cat = 0
    for p in results:
        title = p.get("title", "")
        if title in seen_titles:
            continue
        ii = p.get("imageinfo", [{}])[0]
        thumburl = ii.get("thumburl") or ii.get("url")
        if not thumburl:
            continue
        
        meta = ii.get("extmetadata", {})
        date_str = meta.get("DateTimeOriginal", {}).get("value", "")
        year_match = re.search(r"\b(19[4-9]\d|193\d|192\d|191\d|190\d)\b", date_str)
        if year_match:
            year = int(year_match.group(1))
            if year < 1949:
                continue
        elif any(k in title for k in ("193", "194", "Wehrmacht", "Krieg")):
            continue
            
        m = re.search(r"Bild 183-[A-Za-z0-9\-]+", title)
        bild_id = m.group(0) if m else "Bild 183"
        
        artist = clean_html(meta.get("Artist", {}).get("value", ""))
        credit = clean_html(meta.get("Credit", {}).get("value", ""))
        if not artist or "wikidata" in artist.lower():
            artist = credit
        photographer = artist if artist else "Bundesarchiv"
        if len(photographer) > 40:
            photographer = photographer.split(",")[0].strip()
        
        attr = f"Bundesarchiv, {bild_id} / {photographer} / CC-BY-SA 3.0"
        
        fname = f"shot_{shot_idx:03d}.jpg"
        target_path = img_dir / fname
        if not target_path.exists():
            print(f"  [{shot_idx}] Downloading {fname} ({chapter})...")
            if not download_thumb(thumburl, target_path):
                continue
        
        seen_titles.add(title)
        collected_shots.append(f"{fname}|8|{attr}")
        shot_idx += 1
        count_for_cat += 1
        if count_for_cat >= target:
            break

pathlib.Path("shots.txt").write_text("\n".join(collected_shots) + "\n", encoding="utf-8")
print(f"Done: {len(collected_shots)} shots written to shots.txt")
