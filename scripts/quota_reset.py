"""Report the exact quota reset time for each TTS model.

The API returns retryDelay with RetryInfo on 429. Free-tier daily quotas reset at
midnight Pacific Time; this prints the reported delay so a render can be
scheduled instead of retried blind.
"""
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import BASE, get_key  # noqa: E402

MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts",
          "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
key = get_key()
body = {"contents": [{"parts": [{"text": "Prüfung."}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Charon"}}}}}
now = datetime.now(timezone.utc)
print("now UTC:", now.strftime("%H:%M"))
pt = now - timedelta(hours=7)
print("Pacific (PDT):", pt.strftime("%H:%M"))
for m in MODELS:
    req = urllib.request.Request(f"{BASE}/{m}:generateContent?key={key}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=60)
        print(f"  {m:32s} AVAILABLE now")
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode(errors="replace") or "{}")
        details = payload.get("error", {}).get("details", [])
        retry = next((d.get("retryDelay") for d in details if "retryDelay" in d), "?")
        quota_id = ""
        for d in details:
            if "violations" in d:
                quota_id = ", ".join(v.get("quotaId", "") for v in d["violations"])
        print(f"  {m:32s} 429 retryDelay={retry} {quota_id}")
