"""Render the narration EXACTLY ONCE, spending a single TTS request.

Quota discipline (each model allows ~10 requests/day; debugging burned them):
  1. refuses to run if narration_raw.wav already exists (--force overrides)
  2. picks the first model the quota probe says is free
  3. --wait sleeps until the API-reported reset instead of retrying
  4. makes exactly one request, with no retry loop
  5. writes only narration_raw.wav; cutting and timing live in recheck_narration.py
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import BASE, get_key, post_json, tail  # noqa: E402
from narrate_onetake import build_text, normalize, to_wav  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "build/video2/audio/narration_raw.wav"
MODELS = ["gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts",
          "gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"]

PROBE_BODY = {"contents": [{"parts": [{"text": "Prüfung."}]}],
              "generationConfig": {"responseModalities": ["AUDIO"],
                                   "speechConfig": {"voiceConfig": {
                                       "prebuiltVoiceConfig": {"voiceName": "Charon"}}}}}


def _post(model: str, key: str) -> tuple[int, str]:
    req = urllib.request.Request(f"{BASE}/{model}:generateContent?key={key}",
                                 data=json.dumps(PROBE_BODY).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=60)
        return 200, ""
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")
    except Exception as exc:  # noqa: BLE001
        return 0, type(exc).__name__


def available(model: str, key: str) -> bool:
    code, _ = _post(model, key)
    return code == 200 or code not in (429,)


def seconds_until_reset(key: str) -> int:
    code, body = _post(MODELS[-1], key)
    if code != 429:
        return 0
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 0
    for d in payload.get("error", {}).get("details", []):
        delay = str(d.get("retryDelay", ""))
        if delay.endswith("s"):
            try:
                return int(float(delay[:-1]))
            except ValueError:
                return 0
    return 0


def main() -> int:
    force = "--force" in sys.argv
    if RAW.exists() and RAW.stat().st_size > 10000 and not force:
        print(f"refusing to spend a request: {RAW.name} already exists. --force to re-render.")
        return 0

    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    text, bounds = build_text(plan["scenes"])
    print(f"script: {len(plan['scenes'])} scenes, {len(bounds)} markers, {len(text)} chars")

    key = get_key()
    model = next((m for m in MODELS if available(m, key)), None)
    if model is None and "--wait" in sys.argv:
        wait = seconds_until_reset(key) + 45
        print(f"all models exhausted; sleeping {wait}s until reset")
        time.sleep(max(0, wait))
        model = next((m for m in MODELS if available(m, key)), None)
    if model is None:
        print("no TTS model available; nothing spent")
        return 2
    print(f"using {model} (key {tail(key)})")

    body = {"contents": [{"parts": [{"text": text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {
                                     "prebuiltVoiceConfig": {"voiceName": plan.get("voice", "Charon")}}}}}
    t0 = time.time()
    reply = post_json(model, body, timeout=900, key=key)   # exactly one call
    parts = reply["candidates"][0]["content"]["parts"]
    part = next((p for p in parts if "inlineData" in p), None)
    if not part:
        print("no audio returned; not retrying (would spend another request)")
        return 3
    RAW.parent.mkdir(parents=True, exist_ok=True)
    to_wav(base64.b64decode(part["inlineData"]["data"]), RAW)
    normalize(RAW)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(RAW)], capture_output=True, text=True,
                             check=True).stdout.strip())
    print(f"rendered {d:.1f}s ({d / 60:.2f} min) in {time.time() - t0:.0f}s -> {RAW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
