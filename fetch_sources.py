#!/usr/bin/env python3
"""Fetch plain-text Wikipedia articles (en + de) into sources/.
Usage: python3 fetch_sources.py "East Germany" "Plattenbau" ...
Pages that don't exist are reported, never guessed."""
import json, sys, pathlib, time, urllib.parse, urllib.request, urllib.error

UA = {"User-Agent": "WissenSieNoch-research/0.1 (https://github.com/Refayatul/German; bot@example.com)"}
out = pathlib.Path("sources"); out.mkdir(exist_ok=True)

def fetch(lang, title):
    q = urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": 1,
        "redirects": 1, "format": "json", "titles": title})
    req = urllib.request.Request(f"https://{lang}.wikipedia.org/w/api.php?{q}", headers=UA)
    for attempt in range(3):
        try:
            time.sleep(1.0)
            with urllib.request.urlopen(req, timeout=30) as r:
                page = next(iter(json.load(r)["query"]["pages"].values()))
            if "missing" in page or not page.get("extract"):
                return None
            return page["title"], page["extract"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(3.0 * (attempt + 1))
                continue
            raise
    return None

for title in sys.argv[1:]:
    for lang in ("en", "de"):
        got = fetch(lang, title)
        if not got:
            print(f"[{lang}] NOT FOUND: {title}")
            continue
        name = f"{lang}_{got[0].replace(' ', '_').replace('/', '-')}.txt"
        url = f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(got[0].replace(' ', '_'))}"
        (out / name).write_text(f"SOURCE: {url}\n\n{got[1]}", encoding="utf-8")
        print(f"[{lang}] saved {name} ({len(got[1])} chars)")
