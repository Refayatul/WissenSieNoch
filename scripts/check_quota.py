"""Check remaining daily TTS quota per model BEFORE spending any of it.

Free tier is ~10 requests/day per model. A single tiny text still costs one
request, so this checks only the models that matter for the next render and
prints the reset delay the API reports. Use it before every render attempt.
"""
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import BASE, get_key, tail  # noqa: E402

MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts",
          "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]

key = get_key()
print("key", tail(key))
body = {"contents": [{"parts": [{"text": "Prüfung."}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Charon"}}}}}
for m in MODELS:
    req = urllib.request.Request(f"{BASE}/{m}:generateContent?key={key}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=60)
        print(f"  {m:32s} AVAILABLE")
    except urllib.error.HTTPError as exc:
        err = exc.read().decode(errors="replace")
        lim = re.search(r"limit: (\d+)", err)
        retry = re.search(r"retryDelay'?:?\s*'?(\d+)", err)
        print(f"  {m:32s} {exc.code} limit={lim.group(1) if lim else '?'} "
              f"retry_in={retry.group(1) + 's' if retry else '?'}")
    except Exception as exc:  # noqa: BLE001
        print(f"  {m:32s} network {type(exc).__name__}")
