"""Probe which Gemini TTS models actually respond with the zaitoon key.

Written to a file on purpose: quoting a JSON payload inline in a shell command
corrupts it. Prints status + mime + duration per case so the pipeline config can
be built from measured behaviour instead of memory.

Usage: python3 scripts/pro_tts.py [--voice Charon] [--models m1,m2]
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
PROBE_TEXT = ("Sechzehn Uhr dreißig, ein Plattenbau in Halle-Neustadt. "
              "Warum essen hier alle mittags warm?")


def load_key() -> str:
    import os
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    env = Path("/home/kai/Downloads/projects/zaitoon-studio/.env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                return line.split("=", 1)[1].strip()
    sys.exit("GEMINI_API_KEY not set and zaitoon .env not found")


def speak(key: str, model: str, voice: str, text: str, timeout: int = 240) -> dict:
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    req = urllib.request.Request(
        ENDPOINT.format(model=model, key=key),
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": exc.read().decode()[:1200].replace(chr(10), chr(32))}
    except Exception as exc:  # noqa: BLE001 - report anything, never crash the probe
        return {"ok": False, "status": 0, "error": str(exc)[:1200]}
    try:
        cand = resp["candidates"][0]
        part = next(p for p in cand["content"]["parts"] if "inlineData" in p)
    except (KeyError, IndexError, StopIteration):
        return {"ok": False, "status": 200, "error": "no inlineData: " + json.dumps(resp)[:300]}
    raw = base64.b64decode(part["inlineData"]["data"])
    mime = part["inlineData"].get("mimeType", "")
    # L16 PCM 24 kHz mono -> seconds. RIFF keeps its 44-byte header.
    pcm = len(raw) - (44 if raw[:4] == b"RIFF" else 0)
    return {
        "ok": True,
        "status": 200,
        "mime": mime,
        "bytes": len(raw),
        "head": raw[:4],
        "seconds": round(pcm / 48000.0, 2),
        "elapsed": round(time.time() - t0, 1),
        "raw": raw,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Charon")
    ap.add_argument("--models", default="gemini-2.5-flash-preview-tts,gemini-3.8-flash-tts,"
                                        "gemini-3.8-flash-lite-tts,gemini-3.1-flash-tts-preview,"
                                        "gemini-2.5-pro-preview-tts")
    ap.add_argument("--out", default="tmp/probe")
    args = ap.parse_args()

    key = load_key()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for model in args.models.split(","):
        model = model.strip()
        if not model:
            continue
        r = speak(key, model, args.voice, PROBE_TEXT)
        if r["ok"]:
            print(f"OK   {model:34s} {args.voice:10s} {r['mime']:24s} {r['seconds']:6.2f}s "
                  f"{r['bytes']:>8}B head={r['head']!r} {r['elapsed']}s")
            (out / f"probe_{model}_{args.voice}.bin").write_bytes(r["raw"])
        else:
            print(f"FAIL {model:34s} {args.voice:10s} HTTP {r["status"]} {r["error"][:1200]}")
        time.sleep(3)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
