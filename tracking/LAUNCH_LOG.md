# 30-Day Launch Calendar & Tracker

**Source: Claude's File 3 (tested research, 21 Oct 2026)**

Day 1 = Thu 22 Oct 2026. Day 30 = Fri 20 Nov 2026.
All thresholds are [my judgment] rule-of-thumb values, not published benchmarks.
Europe moves to winter time on Sun 25 Oct 2026 — convert publish times after that date.

---

## 1. Calendar (Claude File 3, §1 — exact)

| Day | Date | Task | Output |
|---|---|---|---|
| 1 | Thu 22 Oct | Create the channel. **Phone-verify the account** (needed for videos > 15 min). Studio → Settings → Channel → Advanced settings: untick "Allow automatic dubbing". Run the VidIQ keyword list from File 2 §3.2. | Channel live, keyword table |
| 2 | Fri 23 Oct | Audio: record 2–3 rain takes (30–40 min each), or pick CC0 files on Freesound (licence filter = CC0). Start the licence log. Pick and trim footage (File 1 §3.2). | Raw audio + clips + log |
| 3 | Sat 24 Oct | Make the 1815s audio mix. Run the 60s benchmark. Run build.sh with small COPIES to prove the chain. Full-decode check, listen to a loop seam. Make a thumbnail. | Tested chain, V1 file |
| **4** | **Sun 25 Oct** | **Publish V1: concept #1, "Regen am Fenster", 10h colour.** Upload evening before and schedule for 17:00–19:00 German time. 10h files can take long to process; upload several hours ahead. | V1 live |
| 5–6 | 26–27 Oct | Build V2 audio (different source from V1) and the black-screen file. **At 48h after V1:** record impressions, CTR, views. Do not edit title or thumbnail before 48h. | V2 file |
| **7** | **Wed 28 Oct** | **Publish V2: concept #7, black screen, 10h**, with audio different from V1. If V1 has ≥ 500 impressions and CTR < 2%, replace V1's thumbnail first, then its title. | V2 live |
| 8–10 | 29–31 Oct | Build V3 (concept #2, distant thunder; limit thunder peaks). Log all metrics for V1/V2 at 7d. | V3 file |
| **11** | **Sun 1 Nov** | **Publish V3: concept #2, rain with distant thunder.** | V3 live |
| 12–13 | 2–3 Nov | Build V4 (concept #3 car roof, or the next-best concept per the table). | V4 file |
| **14** | **Wed 4 Nov** | **Checkpoint 1 (§3 below). Publish V4.** | V4 live, decision |
| 15–17 | 5–7 Nov | Apply the gate's decision. Build V5 (concept #4, tent or tin roof, own recording if possible). Run the Geography check (§2). | V5 file |
| **18** | **Sun 8 Nov** | **Publish V5.** | V5 live |
| 19–20 | 9–10 Nov | Build V6 (concept #5 forest, or a second video in the best-performing concept with new audio and scene). | V6 file |
| **21** | **Wed 11 Nov** | **Checkpoint 2 (§3). Publish V6.** | V6 live, decision |
| 22–24 | 12–14 Nov | Build V7: **first English-titled upload** with its own audio and scene (File 2 §3.4). Add translated title and description to best videos. | V7 file |
| **25** | **Sun 15 Nov** | **Publish V7 (English).** | V7 live |
| 26–27 | 16–17 Nov | Build V8 (concept #6 fire + rain, or a black-screen of the best-performing audio, per §3). | V8 file |
| **28** | **Wed 18 Nov** | **Publish V8.** | V8 live |
| 29 | Thu 19 Nov | Pull all metrics into the log; export the Studio data. | Data complete |
| **30** | **Fri 20 Nov** | **Final decision (§3).** | Go / pivot / stop |

Each video needs its own audio mix and its own scene (File 2 §0).
If time runs short, publish fewer videos rather than reusing loops.

---

## 2. What to Read in YouTube Studio (Claude File 3, §2)

Analytics → Content → select the video.

| Metric | Where | Why |
|---|---|---|
| Impressions, Impressions CTR | Reach | Title and thumbnail fit |
| Traffic source types and **YouTube search → search terms** | Reach | Whether your keyword is what brings viewers |
| Average view duration | Engagement | Hours per viewer |
| **Audience retention graph, value at 1:00:00** | Engagement | Do viewers stay past the first hour? |
| Geography | Audience | Are viewers in DACH? File 2 §1 warns keyword data may overstate other markets |
| Views at 48h / 7d / 14d | Content table | Growth shape |

Ignore "average percentage viewed" on a 10-hour video; it will always look tiny.

---

## 3. Decision Criteria (Claude File 3, §3 — exact)

### Per-video signals (check at 7 and 14 days):

| Signal | Weak | Acceptable | Strong |
|---|---|---|---|
| CTR (after ≥ 1,000 impressions) | < 2% → change thumbnail | 2–5% | > 5% |
| Average view duration | < 20 min (leaving, not sleeping) | 20–60 min | ≥ 60 min |
| Retention at 1:00:00 | < 10% | 10–20% | ≥ 20% |
| YouTube search share of views | < 20% (not keyword-driven) | 20–40% | ≥ 40% (keyword works) |

### Checkpoint 1 (Day 14) and Checkpoint 2 (Day 21):

- **Double down** on a concept if one video meets at least 2 of 3: ≥ 500 views in first 10 days, AVD ≥ 60 min, YouTube search share ≥ 40%. Next uploads: same keyword family, new audio and scene.
- **Pivot** if every video is under 300 views and under 2,000 impressions after 10 days. Pivot options in order: (1) keyword angle from unpulled candidates in File 2 §3.2; (2) bilingual tail on title; (3) black screen as main format; (4) new thumbnail style. Change one thing at a time, give each 7 days.
- **Impressions fine, views low:** thumbnail/title problem.
- **Views fine, AVD low:** scene or audio wrong for sleep (sudden sounds, level changes).

### Day 30 final decision:

- **Go:** at least one concept hit "double down" and channel total rising week over week.
- **Pivot:** best video 300–1,000 views in 14d, or search share low but retention good. 30 more days with changed variable.
- **Stop or restructure:** channel total under 3,000 views after 8 videos, no video above 1,000.

---

## 4. Metrics Log

| V# | Publish Date | Concept | Keyword | Audio Source | 48h Impr | 48h CTR | 48h Views | 7d Views | 7d AVD | Ret@1h | Search% | Top Country |
|:--:|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| V1 | | #1 Fenster | regengeräusche zum einschlafen | | | | | | | | | |
| V2 | | #7 Schwarz | regengeräusche schwarzer bildschirm | | | | | | | | | |
| V3 | | #2 Gewitter | regengeräusche gewitter | | | | | | | | | |
| V4 | | #3 Auto | regen auto geräusche | | | | | | | | | |
| V5 | | #4 Zelt/Blech | regen auf dem zeltdach | | | | | | | | | |
| V6 | | #5 Wald | naturgeräusche zum einschlafen | | | | | | | | | |
| V7 | | EN global | rain sounds for sleeping | | | | | | | | | |
| V8 | | #6 Kamin | kaminfeuer und regen | | | | | | | | | |

---

## 5. Channel Setup Checklist

- [ ] Phone-verify the account
- [ ] Untick "Allow automatic dubbing" (Studio → Settings → Channel → Advanced)
- [ ] Set video language: German (or "No linguistic content" if available)
- [ ] Run VidIQ keyword pulls from File 2 §3.2 unpulled list
- [ ] Upload channel banner + profile picture
