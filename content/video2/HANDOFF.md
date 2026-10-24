# Video 2 — Arbeitsjournal / Handoff for the next agent

**Branch:** `feat/ddr-alltag-video2`
**Status:** video rendered and assembled once; **3 fixes pending** (see §7). Read §2 before touching anything.

---

## 1. What this video is

A ~5:18 German-language explainer, 2560×1440, 25 fps, about DDR everyday life — thesis:
*the timetable of the factory canteen, not the wall, shaped a republic's daily life; a whole country
ate hot food at 11:30.* Mix of motion graphics (diagrams, ticker, timeline, schematic map) and two
licensed Bundesarchiv stills. German narration by Gemini TTS (voice `Charon`).

Deliverable: `content/video2/out/video2_ddr_alltag.mp4` (+ `video2_description.txt`, `video2_tags.txt`).

---

## 2. Hard constraints discovered the hard way — do not relearn these

| Constraint | Evidence | Consequence |
|---|---|---|
| **Gemini TTS free tier = 10 requests/day *per model*, ~4 models** | `scripts/quota_reset.py` returns `limit: 10` + `retryDelay` | Never retry blindly. Run `scripts/check_quota.py` first. A full film = 1–2 calls. |
| **One call cannot exceed ~3000 chars** and ~1700 chars already hit `MAX_TOKENS` | probe matrix in `tmp/probe/block_probe.py` output | Split narration into 2 acts (`scripts/narrate_acts.py`). |
| **A long/charged script returns `finishReason=SAFETY`** | full 5822-char script blocked, plain prose passed | Keep calls short; phrase political passages soberly. |
| **A bare number as marker gets blocked** | `siebenundzwanzig.` → no `content` | Use natural sentences as markers: `Nun zum nächsten Abschnitt.` |
| **TTS *speaks* a "Director's note" prefix aloud** | transcription of probe audio | `STYLE` must stay `""` in `narrate_onetake.py`. |
| **ffmpeg stderr pipe deadlocks** a Python `Popen` writing frames | 48-byte mp4, hung job | Always drain stderr on a thread (`render_graphics.py`). |
| **PNG at 2560×1440 is the render bottleneck** (~0.4 fps) | `tmp/probe/perf*.py` | Current path: downscale inside the page + PNG. Measured 1–2.7 fps. |
| **GitHub Actions is blocked by account billing** | every run since 2026-10-23 21:51 fails before any step | Cannot fix in code. Render locally until the owner resolves billing. |
| **`String.fromCharCode(32)` gives a non-breaking space** | font string silently fell back to `10px sans-serif` | Never build font strings from char codes; use template literals. |
| **Tooling mangles escaped quotes in written files** | repeated `edit` corruption | Prefer whole-file writes with template literals, or patch via a Node/Python script by line number. |

---

## 3. Pipeline (run order)

```
content/video2/plan.json          narration text + scene spec per beat  (SOURCE OF TRUTH)
content/video2/script.txt         human-readable script
content/video2/BRIEF.md           visual plan + fact/source table
content/video2/renderer/frames.html   deterministic canvas renderer: renderFrame(t) is pure

scripts/check_quota.py       which TTS models are free right now (costs 1 req each)
scripts/narrate_acts.py      2 TTS calls -> build/video2/audio/act_1.wav, act_2.wav, acts.json
scripts/cut_acts.py          cut scenes at markers via transcript alignment (slow, needs chat quota)
scripts/recut_scenes.py      split acts proportionally by word count, write manifest (fast, no quota)
scripts/fetch_photos.py      2 x CC BY-SA Bundesarchiv images -> build/video2/images.json (data URLs)
scripts/render_graphics.py   headless Chromium -> ffmpeg, one MP4 per scene
scripts/assemble.py          concat + narration + generated bed + loudnorm -> final MP4
scripts/youtube_meta.py      description, chapters, tags
scripts/finalize_when_done.sh  detached watcher: assemble when all segments exist
```

Key files produced: `build/video2/manifest.json` (scene start/end/duration, measured), `build/video2/render_report.json`.

---

## 4. Decisions and why

* **Graphics over stock footage** — the first video was archive-stills-only and read as a slideshow.
* **Continuous motion layer** (`cameraPush`, `orbitAccents`, `lightSweep`, 60 Hz grain): measured frame
  delta before was **0.09 %** per 0.2 s after the intro (a still image); now **3–5 %**. This was the single
  biggest "not boring" fix. Re-run `tmp/probe/motion.py` after any renderer change to confirm.
* **Progress rail + `NN / 18` counter** — retention cue, costs nothing.
* **Act-split narration** instead of per-scene calls — quota.
* **Audio bed generated with ffmpeg** (low drone + pink noise) — royalty-free by construction, sits under
  `sidechaincompress` ducking.
* **Facts** verified against the repo's own `sources/de_*.txt` Wikipedia dumps; see `BRIEF.md` table.
  Corrected during review: HO ≠ Konsum; WBS 70 timing; POS is ten-class (school laws 1959/1965).

---

## 5. State at handoff (verified)

* 18 scenes, total **318 s (5:18)**, all 18 segments present in `build/video2/segments/`.
* `content/video2/out/video2_ddr_alltag.mp4`: 2560×1440, 25 fps, ~131 MB, mean audio −23 dB — **playable**.
* Rendered stills checked: hook, day chart, bars, compare, chain, timeline, quote, ticker, end card — all legible.

## 6. Known issues and their status
1. **Photo scenes showed the `[Archivbild]` placeholder** in the first assembly. Cause: renderer looked up
   `sceneImages[s.id]` while the plan names images (`image: "platte"`). **Fixed**: `sceneImages[s.image] || sceneImages[s.id]`.
2. **Captions did not match the photos.** Scene 4 used the cyclists frame from the Schwedt refinery
   (Bundesarchiv 1981) but was captioned "Betriebskantine". Captions now read:
   * scene 4 — "Schichtwechsel, Erdölverarbeitungswerk Schwedt" / "Bundesarchiv 1981 – der Weg zur Frühschicht"
   * scene 6 — "Großer Dreesch, Schwerin" / "Bundesarchiv 1982 – Neubaugebiet als Zuteilung"
   **Rule: the caption must describe what the frame actually shows.** If a better canteen photo is found,
   update `WANTED` in `scripts/fetch_photos.py` *and* the caption together.
3. **`Konsum & Intershop` heading collided with the year line** in the compare layout. Patched (46 px, `lineH` 1.1).
   Affected scenes 8 and 12 were re-rendered.
4. `scripts/cut_acts.py` transcription path is slow and unreliable; `scripts/recut_scenes.py` (proportional
   split) is the dependable route when the script order matches the acts.
5. Scene 15 (end card) is intentionally short; the long closing narration lives in scene 18 (ticker recap).

## 7. Next steps (in order)

```bash
CHROME_PATH=~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome \
  python3 scripts/render_graphics.py 2560 4,6      # re-render the two photo scenes
python3 scripts/assemble.py                        # rebuild the MP4
python3 scripts/youtube_meta.py
ffmpeg -ss 100 -i content/video2/out/video2_ddr_alltag.mp4 -frames:v 1 tmp/check.png  # photo must show
```

Then: commit, push `feat/ddr-alltag-video2`, and once billing is restored re-run the workflow
(`.github/workflows/build-video2.yml`) which does the same steps on Actions at 1440p.

## 8. Do-nots

* Do not spend TTS calls without `check_quota.py`.
* Do not put a style prefix into the TTS prompt (it is spoken).
* Do not `git add -A` — the working tree contains unrelated files; stage explicitly.
* Do not edit `frames.html` with escaped-quote string replacement; it corrupts the file. Use template
  literals in a whole-file write or a line-number patch script.
