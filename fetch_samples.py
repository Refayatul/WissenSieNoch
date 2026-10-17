#!/usr/bin/env python3
"""
Build samples/ for bench.py from Pexels portrait stock clips (the same source the two pipelines use).

  export PEXELS_API_KEY=...        # the key your pipelines already use
  python fetch_samples.py          # needs ffmpeg on PATH

Creates 1080x1920 JPEGs:
  zaitoon_<topic>_<n>.jpg / autopsy_<topic>_<n>.jpg   stills
  burst_<clipid>_NN.jpg                               4 consecutive frames (flicker test); <clipid> has no "_"

You can also just copy frames from your own repos (assets/curated_vault/*.jpg, data/broll_*.jpg) using the
same file-name prefixes: zaitoon_*, autopsy_*, burst_z*_NN, burst_a*_NN.
Note: Zaitoon never shows faces; the topic list below respects that (no people queries except hands).
"""
import json, os, subprocess, sys, tempfile, urllib.parse, urllib.request

TOPICS = {
    "zaitoon": ["ramadan lantern", "prayer beads", "quran stand", "mosque arch", "praying hands", "mosque interior"],
    "autopsy": ["server rack", "microchip", "circuit board", "smartphone", "silicon wafer", "network cables", "laboratory equipment"],
}
OUT = "samples"
UA = {"User-Agent": "seg-bench/1.0"}
VF = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"


def api(query, key):
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode(
        {"query": query, "orientation": "portrait", "size": "medium", "per_page": 6})
    req = urllib.request.Request(url, headers={**UA, "Authorization": key})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r).get("videos", [])


def pick_file(video):
    files = [f for f in video.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("width")]
    files.sort(key=lambda f: abs(f["width"] - 1080))
    return files[0]["link"] if files else None


def download(url, dest):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def ffmpeg(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def main():
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        sys.exit("set PEXELS_API_KEY first (or copy frames from your own repos, see the docstring)")
    os.makedirs(OUT, exist_ok=True)
    for system, topics in TOPICS.items():
        for ti, topic in enumerate(topics):
            try:
                vids = [v for v in api(topic, key) if v.get("duration", 0) >= 6 and pick_file(v)]
                if not vids:
                    print(f"[skip] no clip for '{topic}'")
                    continue
                v = vids[0]
                with tempfile.TemporaryDirectory() as td:
                    clip = os.path.join(td, "clip.mp4")
                    download(pick_file(v), clip)
                    for n, t in enumerate(("1.5", "4")):
                        ffmpeg("-ss", t, "-i", clip, "-frames:v", "1", "-vf", VF, "-q:v", "2",
                               os.path.join(OUT, f"{system}_{topic.replace(' ', '-')}_{n}.jpg"))
                    if ti < 2:  # two burst clips per system
                        clipid = f"{system[0]}{topic.split()[0][:8].replace('-', '')}"
                        ffmpeg("-ss", "2", "-i", clip, "-frames:v", "4", "-vf", VF, "-q:v", "2",
                               os.path.join(OUT, f"burst_{clipid}_%02d.jpg"))
                print(f"[ok]   {system}: {topic} (pexels id {v['id']})")
            except Exception as e:
                print(f"[fail] {topic}: {e}")
    n = len([f for f in os.listdir(OUT) if f.lower().endswith((".jpg", ".png"))])
    print(f"{n} images in {OUT}/")


if __name__ == "__main__":
    main()
