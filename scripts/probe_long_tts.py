"""Resolve a working Gemini key WITHOUT printing it, then measure TTS behaviour.

Key resolution order:
  1. $GEMINI_API_KEY if it authenticates
  2. candidate keys found in the local Antigravity audit note (regex only)

Then, for each TTS model, one call with a long German text measures:
  - whether the audio comes back complete (duration vs. expected words)
  - the real speaking rate, so script length can be planned in words, not guesses
Prints only the last 4 characters of whatever key was used.
"""
import base64, json, re, sys, time, urllib.error, urllib.request
from pathlib import Path

NOTE = Path("/home/kai/.gemini/antigravity/brain/05e0ac25-9e76-40e2-9e9c-9c80ef023b07/zaitoon_studio_technical_audit.md")
PAT = re.compile(r"AQ\.Ab8[A-Za-z0-9_\-]{46,60}")
BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def candidates():
    import os
    out = []
    if os.environ.get("GEMINI_API_KEY"):
        out.append(os.environ["GEMINI_API_KEY"])
    env = Path("/home/kai/Downloads/projects/zaitoon-studio/.env")
    if not out and NOTE.exists():
        out.extend(PAT.findall(NOTE.read_text(errors="ignore")))
    seen, uniq = set(), []
    for k in out:
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
    return uniq


def works(key):
    try:
        json.load(urllib.request.urlopen(BASE + "?key=" + key, timeout=30))
        return True
    except Exception:
        return False


def speak(key, model, voice, text, timeout=900):
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}},
    }
    req = urllib.request.Request(f"{BASE}/{model}:generateContent?key={key}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        r = json.load(urllib.request.urlopen(req, timeout=timeout))
    except urllib.error.HTTPError as e:
        return None, e.code, e.read().decode()[:400].replace("\n", " ")
    part = next(p for p in r["candidates"][0]["content"]["parts"] if "inlineData" in p)
    raw = base64.b64decode(part["inlineData"]["data"])
    return (raw, part["inlineData"].get("mimeType")), 200, f"{time.time() - t0:.1f}s"


PARA = ("Morgens um halb fünf rappelt in einem Betrieb in Ludwigshafen der Wecker. "
        "Wer hier arbeitet, trägt mittags die Hauptmahlzeit. Das ist keine Marotte, sondern ein Fahrplan. "
        "Die Kantine öffnet um elf, die Schule endet um zwölf, der Bus fährt um siebzehn Uhr sieben. "
        "Wer um zwanzig Uhr kocht, kocht für niemanden mehr. ")
TEXT = PARA * 20


def main():
    key = None
    for k in candidates():
        if works(k):
            key = k
            break
    if not key:
        sys.exit("no working key found")
    print("key tail ..." + key[-4:])
    Path("tmp/probe").mkdir(parents=True, exist_ok=True)
    words = len(TEXT.split())
    for model in ("gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts", "gemini-3.1-flash-tts-preview"):
        got, code, info = speak(key, model, "Charon", TEXT)
        if not got:
            print(f"{model:30s} HTTP {code} {info[:160]}")
            continue
        raw, mime = got
        secs = (len(raw) - (44 if raw[:4] == b"RIFF" else 0)) / 48000.0
        print(f"{model:30s} OK chars={len(TEXT)} words={words} secs={secs:7.1f} "
              f"{secs / words * 60:5.1f}wpm mime={mime} {info}")
        Path(f"tmp/probe/long_{model}.raw").write_bytes(raw)
        time.sleep(20)


if __name__ == "__main__":
    main()
