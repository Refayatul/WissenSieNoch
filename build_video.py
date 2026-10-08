#!/usr/bin/env python3
"""Render slideshow video: images + narration.wav + captions.srt -> video.mp4
shots.txt format, one per line:  image_filename|seconds|attribution (attribution optional)
Usage: python3 build_video.py"""
import pathlib, subprocess, sys

# Standard 1440p (2560x1440) - guarantees YouTube's premium VP9/AV01 high-bitrate codec
W, H, FPS = 2560, 1440, 25
root = pathlib.Path(".")
tmp = root / "tmp"; tmp.mkdir(exist_ok=True)

def run(cmd):
    subprocess.run(cmd, check=True)

def dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())

shots = []
for line in (root / "shots.txt").read_text(encoding="utf-8").splitlines():
    if not line.strip() or line.startswith("#"):
        continue
    p = [x.strip() for x in line.split("|")]
    shots.append((p[0], float(p[1]), p[2] if len(p) > 2 else ""))

audio_len = dur(root / "narration.wav")
total = sum(s[1] for s in shots)
if total < audio_len:  # hold last image until audio ends
    shots[-1] = (shots[-1][0], shots[-1][1] + (audio_len - total) + 1, shots[-1][2])
    print(f"extended last shot by {audio_len - total + 1:.1f}s")
elif total > audio_len + 1:
    print(f"WARNING: shots total {total:.0f}s > audio {audio_len:.0f}s; tail will be cut")

lines, credits = [], []
for i, (img, secs, attr) in enumerate(shots):
    src = root / "images" / img
    if not src.exists():
        sys.exit(f"missing image: {src}")
    norm = tmp / f"{i:03}.png"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf",
         f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black", str(norm)])
    lines += [f"file '{norm.resolve()}'", f"duration {secs}"]
    if attr and attr not in credits:
        credits.append(attr)
lines.append(f"file '{(tmp / f'{len(shots)-1:03}.png').resolve()}'")  # concat quirk
(tmp / "list.txt").write_text("\n".join(lines) + "\n")
(root / "credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")

font_size = int(34 * H / 1440)
margin_v = int(52 * H / 1440)
outline_w = max(2, int(3 * H / 1440))
style = f"FontName=DejaVu Sans,FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline={outline_w},Shadow=0,MarginV={margin_v}"
vf = f"fps={FPS},format=yuv420p"
if (root / "captions.srt").exists():
    vf += f",subtitles=captions.srt:force_style='{style}'"
run(["ffmpeg", "-y", "-loglevel", "error", "-stats",
     "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
     "-i", str(root / "narration.wav"), "-vf", vf,
     "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
     "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", "video.mp4"])
print(f"done: video.mp4 ({dur(root / 'video.mp4'):.0f}s), credits -> credits.txt")
