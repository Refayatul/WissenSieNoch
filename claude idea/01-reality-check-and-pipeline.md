# Rain-Sound Channel — File 1: Reality Check + Rendering Pipeline (Part 2)

Prepared 21 Oct 2026. Everything marked **[tested]** was run in a sandbox (2 CPU cores, ffmpeg 6.1.1, synthetic 1080p24 test pattern + synthetic noise audio). That is not your CPU and not real rain footage, so speeds and sizes are indicative only. Everything marked **[source]** links to a document at the end. Everything marked **[untested]** or **[my judgment]** is exactly that.

---

## 0. Corrections to the brief (read first)

| Claim in your brief | Status | What it means for you |
|---|---|---|
| Actions: 6 h hard limit per job; free and unlimited on public repos | **Confirmed** [GitHub limits, runners] | Fine, but see row 3: you will not hit 6 h anyway. |
| Public-repo runner is "2-core" | **Wrong in your favor.** Public-repo `ubuntu-latest` is 4 vCPU / 16 GB / 14 GB SSD. Private repos get 2 vCPU / 8 GB and 2,000 min/month on Free [runners, limits] | Public repos are faster, but see the licence warning in §2. |
| Codespaces: 120 core-hours and 15 GB per month | **Confirmed** [Codespaces] | Not needed (see §2). |
| "14 GB artifact storage" on Actions | **Mixed up.** 14 GB is the runner's local SSD. Artifact storage is a separate quota (500 MB on Free for private repos [limits]). I could not verify the per-artifact size limit for public repos; sources I found conflict (500 MB to 5 GB). | Do not plan to move multi-GB files through artifacts. |
| Auto-dubbing will help global expansion | **Does not apply.** YouTube lists videos over 120 minutes as ineligible for auto-dubbing [YouTube dubbing help]. A 10-hour video is never dubbed. It also has no speech to dub. | Turn auto-dubbing off. Use translated titles/descriptions instead (File 2). |
| Upload directly to YouTube from the runner | **Blocked for public videos.** `videos.insert` from an unaudited API project created after 28 Jul 2020 is locked to private [Google API doc]; reports of the audit taking weeks to months [GitHub issue thread]. | Upload manually in Studio. |
| 12-hour videos allowed | **Confirmed**, 12 h or 256 GB, whichever is smaller, after phone verification [YouTube upload help] | Verify the account first. |
| Breakout stats (15.8% / 6.7% / 58%), "27 languages Feb 2026" | **Not verified by me.** | Nothing below depends on them. |

**The main finding: you do not need to render 10 hours.** Encode one 30-minute base segment (the only slow step), then repeat it with stream copy (`-c copy`). **[tested]**

| Test | Result |
|---|---|
| 50 s segment, 1080p24, `veryfast`, CRF 27, maxrate 1.2 Mbps, 2 cores | 18 s → about 2.8× real time (synthetic pattern; real footage will differ) |
| 12 × 50 s joined with concat demuxer, `-c copy` | 600 s file in 1.2 s; video 600.000 s, audio 600.023 s; decodes with no errors |
| Same with 3 copies (full `build.sh` run) | audio is 150.023 s vs video 150.000 s. The 23 ms offset is constant (AAC padding), it does **not** grow with joins |
| `-stream_loop N -c copy` instead of concat | works, but ended at 600.17 s with more timestamp drift; use the concat demuxer |
| Black screen, 1280×720, 1 fps, `-tune stillimage`, AAC 128k | 9.77 MB per 600 s → about **0.59 GB for 10 h** |
| Colour test pattern at the above settings | 8.45 MB per 50 s ≈ 1.35 Mbps all-in → about 6 GB for 10 h. Smooth rain footage should be smaller; the `maxrate` caps it |

---

## 1. Where the real bottleneck is

Rendering is minutes. **Getting 3–6 GB (or 0.6 GB for black screen) to YouTube from your connection** is the hours-long step, and it cannot be moved to GitHub because of the API-audit lock above.

- Upload time in hours ≈ `size_GB × 8000 / (upload_Mbps × 3600)`. Example: 6 GB at 5 Mbps ≈ 2.7 h; 0.59 GB at 5 Mbps ≈ 16 min.
- To shrink files: lower `MAXRATE` (e.g. 600k for slow, soft footage), use 720p, or use the black-screen variant. YouTube re-encodes whatever you send, so a very high bitrate gains nothing for a low-motion scene **[my judgment]**.
- I do not know whether Studio resumes a broken upload; keep the machine awake and on cable.

---

## 2. Actions vs Codespaces vs local — decision

**Recommendation: build locally with `build.sh`. Use GitHub Actions only for the 30-minute base-segment encode if your own benchmark is too slow.** Reasons:

1. Local needs one slow encode (30 min of video). Benchmark your laptop first (below). If the speed is ≥ about 0.7× real time, a 30-minute segment takes under about 45 min, which is fine overnight.
2. Actions cannot deliver the final file (artifact quota, API lock), so it only helps the base segment, which at ≤ 1 Mbps is ≈ 250 MB and fits a 500 MB quota. Delete it after download (`retention-days: 1`).
3. **Licence warning for a public repo:** Pexels says its videos may be used on YouTube when used to create your own video, and that simply posting an unmodified clip is not permitted; Pixabay warns its music can be registered in Content ID [secondary source: iTechGuides; confirm on pexels.com/license and pixabay.com/service/license]. A public repo holding raw stock clips is redistribution. Use a **private** repo for assets; the job needs only minutes, so 2,000 free minutes/month is plenty.
4. **Codespaces: skip.** 120 core-hours is 60 hours on a 2-core machine, storage is billed in GB-hours, and the file still has to reach YouTube from your connection. No advantage over Actions.
5. Optional fallback: Kaggle CPU notebooks (free, no card; reported 12 h sessions, 4 cores, up to 20 GB saved output). Verify current limits at kaggle.com/docs/notebooks before relying on it. Source for these numbers is a book excerpt and a summary page, not Kaggle's own docs.

**Benchmark on your laptop (60 s of real footage; read `speed=`):**
```bash
ffmpeg -y -i clip.mp4 -t 60 -an -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=24,format=yuv420p" \
  -c:v libx264 -preset veryfast -crf 27 -maxrate 1000k -bufsize 2000k -g 48 bench.mp4
```
If `speed=` is below 0.3x, switch `PRESET` to `superfast` or `ultrafast` (bigger file), drop to 720p (`W=1280 H=720`), or use Actions.

---

## 3. Commands (all **[tested]** unless stated)

Folder layout:
```
rain/ clips/  audio/  scripts/build.sh  out/
```

### 3.1 Prepare audio (CPU-cheap)
Build one master track of 30 min + `ACF` seconds from several CC0 recordings so the loop is long (listeners asleep will not notice 20 repeats of 30 minutes). To join two recordings smoothly (same mechanism as the tested loop):
```bash
ffmpeg -i rainA.wav -i rainB.wav -filter_complex "[0:a][1:a]acrossfade=d=20:c1=tri:c2=tri" -c:a pcm_s16le mix.wav
```
Target `mix.wav` = **1815 s** (1800 s loop + 15 s crossfade). Check: `ffprobe -v error -show_entries format=duration -of csv=p=0 mix.wav`. Keep peaks at or below −3 dBFS and avoid loud, sudden events (thunder, car horns) in sleep audio **[my judgment]**.

### 3.2 Choose clip length so loops line up
`audio loop = floor(mix) − ACF` must be a multiple of the video loop:

| Mode | Video loop | Example for 1800 s audio loop |
|---|---|---|
| `pingpong` (forward + reverse) | 2 × clip | 20 s clip → 40 s loop; 1800 / 40 = 45 ✔ |
| `xfade` (1–2 s crossfade) | clip − `VXF` | 22 s clip, `VXF=2` → 20 s loop; 1800 / 20 = 90 ✔ |

Use **`xfade` whenever raindrops or streaks are visible**: ping-pong makes rain fall upward. Use `pingpong` only for fog, trees, lamps, candles. Trim the clip to an exact length first:
```bash
ffmpeg -i pexels_raw.mp4 -t 22 -an -c:v libx264 -crf 12 -preset veryfast clips/window_22s.mp4
```

### 3.3 One-command build (10 h)
```bash
CLIP=clips/window_22s.mp4 AUDIO=audio/mix.wav MODE=xfade VXF=2 ACF=15 COPIES=20 \
  OUT=out/regen_fenster_10h.mp4 bash scripts/build.sh
```
`build.sh` (in this folder) runs: audio crossfade loop → video loop → one 1800 s segment encode → lossless concat of `COPIES` repeats. It stops with an error if the loop lengths do not divide evenly. Ran end to end in both modes **[tested]**: 150 s output in about 25 s, clean decode.

**Length variants from the same segment (no re-encode, seconds each):**
| Variant | `COPIES` (× 1800 s) | Total |
|---|---|---|
| 3 h | 6 | 10,800 s |
| 8 h | 16 | 28,800 s |
| 10 h | 20 | 36,000 s |

(Re-running `build.sh` re-encodes the segment each time; to reuse it, copy `work/segment.mp4`, write a list file, and run only the last `ffmpeg -f concat` line.)

### 3.4 Splitting into two 5-hour halves and joining losslessly
Only needed if you want smaller files. Each half is the same concat, with `COPIES=10`. To join halves later (same codec parameters, so no re-encode):
```bash
printf "file 'part1.mp4'\nfile 'part2.mp4'\n" > join.txt
ffmpeg -f concat -safe 0 -i join.txt -c copy -movflags +faststart full_10h.mp4
```
Tested with two copies of a segment → 100.02 s, as expected.

### 3.5 Black-screen version
```bash
ffmpeg -f lavfi -i "color=c=black:s=1280x720:r=1" -stream_loop -1 -i work/loop.wav -t 36000 \
  -map 0:v -map 1:a -c:v libx264 -preset veryfast -tune stillimage -crf 35 -g 60 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -ar 44100 -shortest -movflags +faststart out/regen_schwarz_10h.mp4
```
Tested at 600 s (9.77 MB). Expect ≈ 0.59 GB at 10 h, so ≈ 16 min to upload at 5 Mbps.

### 3.6 Verify before uploading
```bash
ffprobe -v error -show_entries format=duration,size -of default=nw=1 out/regen_fenster_10h.mp4
ffmpeg -v error -i out/regen_fenster_10h.mp4 -f null -     # full decode; silent output means no errors
```
Then spot-listen at three loop seams (`1800 s`, `3600 s`, `5400 s`) with headphones.

---

## 4. Optional: GitHub Actions workflow for the base segment **[untested]**

I could not run GitHub Actions from here. Dry-run it first with `seg_seconds` input small and read the `speed=` line in the log.

`.github/workflows/segment.yml` in a **private** repo (assets under `clips/`, `audio/`, script under `scripts/`):
```yaml
name: base-segment
on:
  workflow_dispatch:
    inputs:
      copies:
        description: "copies of the segment (1 = segment only)"
        default: "1"
jobs:
  encode:
    runs-on: ubuntu-latest
    timeout-minutes: 300
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update && sudo apt-get install -y ffmpeg
      - run: |
          CLIP=clips/window_22s.mp4 AUDIO=audio/mix.wav MODE=xfade VXF=2 ACF=15 \
          COPIES=${{ inputs.copies }} OUT=out/segment.mp4 bash scripts/build.sh
      - uses: actions/upload-artifact@v4
        with:
          name: segment
          path: out/segment.mp4
          retention-days: 1
          compression-level: 0
```
Download the artifact, then run `COPIES=20` locally using that segment (concat line only). Keep `mix.wav`/clips under GitHub's per-file push limit (100 MB) or use Git LFS (check its free quota first).

---

## 5. Sources

- GitHub Actions limits: https://docs.github.com/en/actions/reference/limits
- GitHub-hosted runners (public vs private specs): https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- Codespaces included usage: https://docs.github.com/en/get-started/learning-about-github/githubs-plans and https://docs.github.com/en/codespaces/troubleshooting/troubleshooting-included-usage
- YouTube automatic dubbing (120-minute ineligibility, channel opt-out): https://support.google.com/youtube/answer/15569972
- YouTube upload limits and verification: https://support.google.com/youtube/answer/71673
- YouTube Data API `videos.insert` (private lock for unaudited projects): https://developers.google.com/youtube/v3/docs/videos/insert
- API audit experience: https://github.com/porjo/youtubeuploader/issues/86
- Stock licence summary (secondary): https://www.itechguides.com/?p=325642
