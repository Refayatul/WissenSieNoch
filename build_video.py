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
    
    norm = tmp / f"{i:03}.mp4"
    frames = int(secs * FPS)
    
    import math
    # yt-winter ProfitDecoded 2.5D Sinusoidal Camera Engine & Cinematic Teal/Orange Grade
    SW, SH = 2800, 1575 # Oversample buffer to prevent black edges during curved panning
    
    zin = (i % 2 == 0)
    yon = 1 if zin else -1
    
    # 2.5D Cinematic: yavas zoom + capraz kaydirma (sine wave drift)
    if zin:
        z = f"min(1+0.12*on/{frames},1.13)"
    else:
        z = f"max(1.13-0.12*on/{frames},1.0)"
        
    x = f"iw/2-(iw/zoom/2)+({yon})*(iw-iw/zoom)*0.34*sin(PI*on/{frames})"
    y = f"ih/2-(ih/zoom/2)-({yon})*(ih-ih/zoom)*0.30*(on/{frames}-0.5)"

    # yt-winter Teal/Orange Grade: brightness=-0.10, contrast=1.10, sat=0.82, colorbalance for teal mids/shadows
    sinematik_grade = "eq=brightness=-0.10:contrast=1.10:saturation=0.82,colorbalance=bs=0.10:bm=0.05:rh=-0.03,vignette=angle=PI/5"
    
    vf = f"scale={SW}:{SH}:force_original_aspect_ratio=increase,crop={SW}:{SH},{sinematik_grade},zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p"
    
    if not norm.exists():
        print(f"Rendering shot {i:03}/{len(shots)}: {img} with Ken Burns...")
        run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), 
             "-vf", vf, "-t", str(secs), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", str(norm)])
             
    lines.append(f"file '{norm.resolve()}'")
    if attr and attr not in credits:
        credits.append(attr)

(tmp / "list.txt").write_text("\n".join(lines) + "\n")
(root / "credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")

font_size = int(34 * H / 1440)
margin_v = int(52 * H / 1440)
outline_w = max(2, int(3 * H / 1440))
style = f"FontName=DejaVu Sans,FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline={outline_w},Shadow=0,MarginV={margin_v}"
vf = f"fps={FPS},format=yuv420p"
if (root / "captions.srt").exists():
    vf += f",subtitles=captions.srt:force_style='{style}'"
cmd = ["ffmpeg", "-y", "-loglevel", "error", "-stats",
       "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
       "-i", str(root / "narration.wav")]

if (root / "music.mp3").exists():
    cmd += ["-stream_loop", "-1", "-i", str(root / "music.mp3")]
    # yt-winter balanced audio mix: voice at 1.0, music at 0.15 (background)
    cmd += ["-filter_complex", f"[0:v]{vf}[v];[1:a]volume=1.0[a1];[2:a]volume=0.15[a2];[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[a]"]
    cmd += ["-map", "[v]", "-map", "[a]"]
else:
    cmd += ["-vf", vf]
    
cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", "video.mp4"]

run(cmd)
print(f"done: video.mp4 ({dur(root / 'video.mp4'):.0f}s), credits -> credits.txt")
