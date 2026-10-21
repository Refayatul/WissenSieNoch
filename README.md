# German Rain/Sleep Ambience Channel

**Channel pivot:** WissenSieNoch (DDR history documentaries) → Rain/Sleep Ambience

Based on Claude's research (21 Oct 2026) — 3 files covering reality-check + rendering pipeline, VidIQ keyword data + 10 concepts, and a 30-day launch calendar with decision gates.

## Architecture

```
/home/kai/Downloads/projects/German/     <- code, scripts, metadata (git-tracked)
  scripts/
    build.sh              Claude's tested seamless-loop pipeline
    generate_audio.sh     ffmpeg-synthesized rain audio (fallback)
    fetch_assets.py       Pexels video clip fetcher + licence logger
    fetch_freesound.py    Freesound CC0 audio fetcher
    mix_user_audio.py     Crossfade user recordings into 1815s master
    verify.py             QA: A/V sync, faststart, decode integrity
    benchmark.sh          Local encode speed test
  metadata/               YouTube titles, descriptions, tags per concept
  tracking/LAUNCH_LOG.md  30-day calendar + metrics tracker
  licences/LICENCE_LOG.md Stock & media compliance registry

/mnt/programming/German/                 <- heavy assets (147 GB free, NOT git-tracked)
  audio/                  1815s master WAV mixes (~305 MB each)
  clips/                  Normalised 22s 1080p24 source clips (~12 MB each)
  work/                   Intermediate build files (auto-cleaned)
  out/                    Final 10-hour MP4s (3-6 GB each, or 0.6 GB for black screen)
```

## Quick Start

```bash
# Check workspace status
python manage.py status

# Benchmark your CPU (expect ~1.5x on i5-4210U)
python manage.py bench

# Build Video 1: Regen am Fenster, 10 hours
python manage.py build window

# Build Video 2: Black screen, 10 hours (~0.59 GB)
python manage.py black

# Verify before uploading
python manage.py verify /mnt/programming/German/out/regen_window_10h.mp4
```

## Audio Sources (ranked by Claude File 2, §0)

1. **Record your own rain** — strongest answer to YouTube's "inauthentic content" policy
2. **Freesound CC0** — `python manage.py freesound "rain window"`
3. **YouTube Audio Library** — pre-licensed, smaller catalogue
4. **Synthesized** (this pipeline's fallback) — zero Content ID risk but not "original"

## Key Warnings (Claude's Research)

- **"Inauthentic content" risk:** YouTube renamed "repetitious content" to "inauthentic content" on 15 Jul 2025. Each upload MUST have its own audio and scene. Do NOT publish 3h/8h/10h cuts of the same loop as separate videos.
- **Licence:** Keep raw Pexels clips out of any public repo (redistribution). Use a private repo.
- **Upload:** `videos.insert` API is locked to private for unaudited projects (since Jul 2020). Upload manually in YouTube Studio.
- **Auto-dubbing:** Turn off. 10-hour videos are ineligible anyway (>120 min limit).
