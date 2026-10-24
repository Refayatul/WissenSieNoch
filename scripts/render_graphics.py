"""Render the graphics timeline to silent MP4 segments, one per scene.

Transfer strategy, chosen from measurement (tmp/probe/perf2.py):
  renderFrame            74 ms   (2K canvas, all motion)
  toDataURL PNG @2K    2600 ms   too slow
  full raw RGBA @2K     680 ms
  downscale + PNG @1080p 750 ms  used here: lossless, half the bytes

So each frame is downscaled inside the page to the delivery size and sent as a
PNG; ffmpeg only has to encode. Segments are per scene so a crash costs one
scene, and a rerun resumes from whatever is already on disk.
"""
from __future__ import annotations

import base64
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRAMES_HTML = ROOT / "content/video2/renderer/frames.html"

# Downscale + PNG inside the page: one round trip per frame, small payload.
EVAL_FRAME = """([t, w, h]) => {
  window.renderFrame(t);
  const src = document.getElementById('c');
  const c = window.__out || (window.__out = document.createElement('canvas'));
  c.width = w; c.height = h;
  const x = c.getContext('2d');
  x.imageSmoothingEnabled = true;
  x.imageSmoothingQuality = 'high';
  x.drawImage(src, 0, 0, w, h);
  return c.toDataURL('image/png').split(',')[1];
}"""


def build_page(manifest: dict, images: dict[str, str]) -> tuple[str, str]:
    html = FRAMES_HTML.read_text(encoding="utf-8")
    scenes = [{k: v for k, v in s.items() if k != "wav"} for s in manifest["scenes"]]
    plan = {
        "scenes": scenes,
        "duration": manifest["duration"],
        "width": manifest["width"],
        "height": manifest["height"],
        "fps": manifest["fps"],
        "images": images,
    }
    return html, json.dumps(plan, ensure_ascii=False)


def render_scene(page, scene: dict, out_mp4: Path, fps: int, out_w: int, out_h: int) -> None:
    n_frames = max(1, int(round(scene["duration"] * fps)))
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "image2pipe", "-framerate", str(fps), "-i", "-",
        "-vf", f"scale={out_w}:{out_h}:flags=lanczos,format=yuv420p",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-g", str(fps * 2), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    # Drain stderr on a thread. A full stderr pipe blocks ffmpeg, which then
    # stops reading stdin while we are still writing - a real deadlock that
    # produced a 48-byte file and looked like "ffmpeg is broken".
    err_chunks: list[bytes] = []

    def drain() -> None:
        err_chunks.append(proc.stderr.read())

    threading.Thread(target=drain, daemon=True).start()

    t0 = time.time()
    for i in range(n_frames):
        t = scene["start"] + i / fps
        b64 = page.evaluate(EVAL_FRAME, [t, out_w, out_h])
        proc.stdin.write(base64.b64decode(b64))
        if i and i % (fps * 2) == 0:
            rate = i / max(0.001, time.time() - t0)
            print(f"      {i}/{n_frames} frames  {rate:.2f} fps", flush=True)
    proc.stdin.close()
    proc.wait()
    err = (err_chunks[0] if err_chunks else b"").decode(errors="replace")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for scene {scene['id']}: {err[-800:]}")


def main() -> int:
    from playwright.sync_api import sync_playwright

    manifest = json.loads((ROOT / "build/video2/manifest.json").read_text(encoding="utf-8"))
    images_path = ROOT / "build/video2/images.json"
    images = json.loads(images_path.read_text(encoding="utf-8")) if images_path.exists() else {}
    html, plan_json = build_page(manifest, images)

    out_w = int(sys.argv[1]) if len(sys.argv) > 1 else 1920
    out_h = out_w * 9 // 16
    # --act K --acts N renders only the K-th slice of the scene list, so CI can
    # split the work across runners and a failure costs one act, not the film.
    only = None
    if "--act" in sys.argv:
        act = int(sys.argv[sys.argv.index("--act") + 1])
        acts = int(sys.argv[sys.argv.index("--acts") + 1]) if "--acts" in sys.argv else 1
        ids = [s["id"] for s in manifest["scenes"]]
        per = max(1, round(len(ids) / acts))
        chunk = ids[(act - 1) * per: act * per] if act < acts else ids[(act - 1) * per:]
        only = set(chunk)
        print(f"act {act}/{acts}: scenes {sorted(only)}")
    elif len(sys.argv) > 2 and sys.argv[2] not in ("", "-"):
        only = {int(x) for x in sys.argv[2].split(",")}
    fps = manifest["fps"]
    outdir = ROOT / "build/video2/segments"

    with sync_playwright() as pw:
        import os
        exe = os.environ.get("CHROME_PATH")  # CI installs Playwright's own browser
        browser = pw.chromium.launch(executable_path=exe,
                                     args=["--disable-gpu", "--font-render-hinting=none"])
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.on("pageerror", lambda e: print("  PAGE ERROR:", e, flush=True))
        page.set_content(html, wait_until="load")
        page.evaluate("(p) => window.setPlan(p)", json.loads(plan_json))
        page.wait_for_timeout(300)
        for key, data_url in images.items():
            page.evaluate("([k, u]) => window.loadImage(k, u)", [key, data_url])
        page.wait_for_timeout(600)

        for scene in manifest["scenes"]:
            if only and scene["id"] not in only:
                continue
            out = outdir / f"scene_{scene['id']:02d}.mp4"
            if only is not None and scene["id"] not in only:
                continue
            if out.exists() and out.stat().st_size > 20000:
                print(f"  scene {scene['id']:2d} cached")
                continue
            print(f"  scene {scene['id']:2d} {scene['type']:9s} {scene['duration']:6.2f}s", flush=True)
            render_scene(page, scene, out, fps, out_w, out_h)
        browser.close()
    print("segments written to", outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
