"""Batch narration: few TTS calls, many scenes.

Free tier allows 10 requests/day per model, so one call per scene (15 calls)
cannot survive a day of iteration. This renders the whole script in N calls,
one per act, separated by a marker word that is then cut out:

  <mark> <<S07>> <mark>

The marker is spoken as an isolated utterance, so the audio contains a clear
pause plus a short distinctive sound; ffmpeg finds it, and scene boundaries land
inside real silence. A tiny leading beep-free gap keeps cuts clean.

Usage: python3 scripts/narrate_batch.py [--batch 1|2|3]
Writes build/video2/audio/scene_XX.wav and build/video2/manifest.json.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import post_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build/video2"
AUDIO = BUILD / "audio"

MODELS = ["gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts",
          "gemini-3.1-flash-tts-preview", "gemini-2.5-flash-preview-tts"]
MARK = "Achtung, nächster Abschnitt."


def duration(p: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def to_wav(raw: bytes, out: Path) -> None:
    tmp = out.with_suffix(".raw")
    tmp.write_bytes(raw)
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    cmd += ["-i", str(tmp)] if raw[:4] == b"RIFF" else ["-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(tmp)]
    subprocess.run([*cmd, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    tmp.unlink(missing_ok=True)


def normalize(path: Path) -> None:
    tmp = path.with_suffix(".norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-af",
                    "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=70", "-ar", "48000", "-ac", "1", str(tmp)],
                   check=True)
    tmp.replace(path)


def render_batch(text: str, out: Path, voice: str) -> bool:
    """One request, with the same retire-on-daily-quota logic as narrate.py."""
    for model in MODELS:
        body = {"contents": [{"parts": [{"text": text}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
        t0 = time.time()
        try:
            reply = post_json(model, body, timeout=900)
        except urllib.error.HTTPError as exc:
            msg = exc.read().decode(errors="replace")
            daily = any(k in msg for k in ("PerDay", "per day", "PerProject"))
            print(f"    {model}: HTTP {exc.code}{' (daily quota)' if daily else ''}", flush=True)
            if exc.code == 429 and not daily:
                time.sleep(35)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"    {model}: {type(exc).__name__}", flush=True)
            continue
        parts = reply["candidates"][0]["content"]["parts"]
        part = next((p for p in parts if "inlineData" in p), None)
        if not part:
            continue
        to_wav(base64.b64decode(part["inlineData"]["data"]), out)
        normalize(out)
        print(f"    {model}: {duration(out):.1f}s in {time.time() - t0:.0f}s", flush=True)
        return True
    return False


def silences(path: Path) -> list[tuple[float, float]]:
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                          "silencedetect=noise=-36dB:d=0.45", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", err)]
    return list(zip(starts, ends))


def cut_batch(wav: Path, scene_ids: list[int]) -> list[Path]:
    """Split a batch at its N-1 longest pauses, which are the marker breaks."""
    total = duration(wav)
    gaps = [g for g in silences(wav) if 0.8 < g[0] < total - 0.8]
    need = len(scene_ids) - 1
    if not need:
        return [wav]
    # longest pauses are the marker separations; keep them in time order
    chosen = sorted(sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:need], key=lambda g: g[0])
    if len(chosen) < need:
        print(f"    ! only {len(chosen)} of {need} marker pauses found; cutting proportionally")
        cuts = [total * i / len(scene_ids) for i in range(1, len(scene_ids))]
    else:
        cuts = [(s + e) / 2 for s, e in chosen]
    bounds = [0.0] + cuts + [total]
    outs = []
    for i, sid in enumerate(scene_ids):
        out = AUDIO / f"scene_{sid:02d}.wav"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                        "-ss", f"{bounds[i]:.3f}", "-to", f"{bounds[i + 1]:.3f}",
                        "-af", "silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.05,"
                               "areverse,silenceremove=start_periods=1:start_threshold=-46dB:start_silence=0.12,areverse",
                        "-ar", "48000", "-ac", "1", str(out)], check=True)
        outs.append(out)
    wav.unlink(missing_ok=True)
    return outs


def build(batch_count: int = 1) -> dict:
    plan = json.loads((ROOT / "content/video2/plan.json").read_text(encoding="utf-8"))
    AUDIO.mkdir(parents=True, exist_ok=True)
    voice = plan.get("voice", "Charon")
    scenes = plan["scenes"]
    per = max(1, round(len(scenes) / batch_count))
    groups = [scenes[i:i + per] for i in range(0, len(scenes), per)]

    done: dict[int, Path] = {}
    for gi, group in enumerate(groups, 1):
        ids = [s["id"] for s in group]
        missing = [s for s in group if not (AUDIO / f"scene_{s['id']:02d}.wav").exists()]
        if not missing:
            for s in group:
                done[s["id"]] = AUDIO / f"scene_{s['id']:02d}.wav"
            print(f"  act {gi}: cached ({len(group)} scenes)")
            continue
        text = ("\n\n" + MARK + "\n\n").join(s["words"].strip() for s in missing)
        raw_wav = AUDIO / f"batch_{gi}.wav"
        print(f"  act {gi}: {len(missing)} scenes, {len(text)} chars", flush=True)
        if not render_batch(text, raw_wav, voice):
            print(f"  act {gi}: FAILED (no model available) - scenes {ids} dropped")
            continue
        outs = cut_batch(raw_wav, [s["id"] for s in missing])
        for s, p in zip(missing, outs):
            done[s["id"]] = p

    t, out_scenes, skipped = 0.0, [], []
    for s in scenes:
        wav = done.get(s["id"])
        if not wav or not wav.exists():
            skipped.append(s["id"])
            continue
        d = max(duration(wav), 2.2)
        entry = {"id": s["id"], "type": s["type"], "start": round(t, 3), "end": round(t + d, 3),
                 "duration": round(d, 3),
                 "wav": str(wav.relative_to(ROOT))}
        entry.update({k: v for k, v in s.items() if k not in {"words", "id", "type"}})
        out_scenes.append(entry)
        t += d

    manifest = {"id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 30),
                "width": plan.get("width", 2560), "height": plan.get("height", 1440),
                "duration": round(t, 3), "voice": voice, "skipped_scenes": skipped,
                "scenes": out_scenes}
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest: {len(out_scenes)} scenes, {t:.1f}s ({t / 60:.2f} min), skipped={skipped}")
    return manifest


if __name__ == "__main__":
    count = 1
    if "--batch" in sys.argv:
        count = int(sys.argv[sys.argv.index("--batch") + 1])
    build(count)
