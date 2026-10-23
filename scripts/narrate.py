"""Narration for video 2: render speech, then derive exact scene timings.

Gemini TTS returns no timestamps, so the timing contract is:
  1. render each scene's narration separately (one call per scene: a retry only
     costs that scene, and a failed scene can fall back to another model),
  2. measure each WAV,
  3. hand the measured durations to the renderer.

Splitting per scene also keeps every request far below the input limit and makes
the visual cut points follow the audio instead of a guess.
"""
from __future__ import annotations

import base64
import json

import subprocess
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gemini_client import get_key, post_json  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# TTS cascade. Each free-tier model allows ~10 requests/day, so the cascade is
# also the retry budget: 15 scenes must fit, hence several models.
TTS_MODELS = [
    "gemini-3.8-flash-lite-tts",
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
]

STYLE = ""  # measured: Gemini TTS reads a style prefix ALOUD, so the voice is
# steered by the text alone (short sentences, question marks, spelled-out
# numbers). Kept as a named empty constant so the call site stays obvious.


def wav_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def pcm_to_wav(raw: bytes, out: Path) -> None:
    """Gemini returns either RIFF WAV or headerless 24 kHz s16le PCM."""
    tmp = out.with_suffix(".raw")
    tmp.write_bytes(raw)
    if raw[:4] == b"RIFF":
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp)]
    else:
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", "24000", "-ac", "1", "-i", str(tmp)]
    subprocess.run([*cmd, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(out)], check=True)
    tmp.unlink(missing_ok=True)


def normalize(path: Path) -> None:
    """Loudness-normalise to a broadcast-ish target, then tidy the edges.

    Two-pass loudnorm keeps the level consistent between scenes rendered in
    different calls; the trailing fade removes clicks at the cut.
    """
    tmp = path.with_suffix(".norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path),
                    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,highpass=f=70,"
                           "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
                           "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.08,areverse",
                    "-ar", "48000", "-ac", "1", str(tmp)], check=True)
    tmp.replace(path)


def speak_scene(text: str, voice: str, out: Path) -> tuple[bool, str]:
    """Render one scene. Tries the cascade; returns (ok, model_used)."""
    key = get_key()
    for model in TTS_MODELS:
        for attempt in range(2):
            body = {
                "contents": [{"parts": [{"text": (STYLE + "\n\n" + text) if STYLE else text}]}],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
                },
            }
            t0 = time.time()
            try:
                reply = post_json(model, body, timeout=600, key=key)
            except urllib.error.HTTPError as exc:
                msg = exc.read().decode()[:300]
                if exc.code == 429:
                    print(f"    429 on {model} (attempt {attempt + 1})", flush=True)
                    time.sleep(20 + attempt * 20)
                    continue
                print(f"    HTTP {exc.code} on {model}: {msg[:160]}", flush=True)
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                print(f"    network {type(exc).__name__} on {model}", flush=True)
                time.sleep(10)
                continue
            part = next((p for p in reply["candidates"][0]["content"]["parts"] if "inlineData" in p), None)
            if not part:
                print(f"    no audio from {model}", flush=True)
                break
            pcm_to_wav(base64.b64decode(part["inlineData"]["data"]), out)
            normalize(out)
            print(f"    ok {model} in {time.time() - t0:.0f}s -> {wav_duration(out):.1f}s", flush=True)
            return True, model
    return False, ""


def build(plan_path: Path, audio_dir: Path, out_manifest: Path, cache: bool = True) -> dict:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice = plan.get("voice", "Charon")
    models_used: set[str] = set()
    scenes = []
    t = 0.0
    t_started = time.time()
    # Wall-clock budget: CI must never hang on a provider having a bad day.
    # Whatever is unfinished is reported and skipped so the render still ships.
    import os
    budget = float(os.environ.get("NARRATION_BUDGET_S", "1500"))
    skipped: list[int] = []
    for sc in plan["scenes"]:
        if time.time() - t_started > budget:
            print(f"  budget exhausted, skipping scene {sc['id']}", flush=True)
            skipped.append(sc["id"])
            continue
        wav = audio_dir / f"scene_{sc['id']:02d}.wav"
        if cache and wav.exists() and wav.stat().st_size > 1000:
            print(f"  scene {sc['id']:2d} cached ({wav_duration(wav):.1f}s)")
        else:
            print(f"  scene {sc['id']:2d} {sc['type']:9s} {len(sc['words'])} chars", flush=True)
            ok, model = speak_scene(sc["words"], voice, wav)
            if not ok:
                raise SystemExit(f"scene {sc['id']} failed on every TTS model")
            models_used.add(model)
        dur = wav_duration(wav)
        # a per-scene floor keeps the shortest lines on screen long enough to read
        dur = max(dur, 2.2)
        scenes.append({
            "id": sc["id"], "type": sc["type"], "start": round(t, 3), "end": round(t + dur, 3),
            "duration": round(dur, 3), "wav": str(wav.resolve().relative_to(ROOT)) if wav.resolve().is_relative_to(ROOT) else str(wav),
            **{k: v for k, v in sc.items() if k not in {"words", "id", "type"}},
        })
        t += dur

    manifest = {
        "id": plan["id"], "title": plan["title"], "fps": plan.get("fps", 30),
        "width": plan.get("width", 2560), "height": plan.get("height", 1440),
        "duration": round(t, 3), "voice": voice, "tts_models": sorted(models_used),
        "skipped_scenes": skipped,
        "scenes": scenes,
    }
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nmanifest: {len(scenes)} scenes, {t:.1f}s ({t / 60:.2f} min) -> {out_manifest}")
    return manifest


def main() -> int:
    build(ROOT / "content/video2/plan.json",
          ROOT / "build/video2/audio",
          ROOT / "build/video2/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
