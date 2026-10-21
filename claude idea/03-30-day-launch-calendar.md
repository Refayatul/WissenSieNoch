# Rain-Sound Channel — File 3: 30-Day Launch Calendar (Part 5)

Day 1 = Thu 22 Oct 2026, Day 30 = Fri 20 Nov 2026. All thresholds below are **[my judgment]** rule-of-thumb values, not published benchmarks. Small samples are noisy: judge a concept on at least two or three videos, never one.

Europe moves to winter time on Sun 25 Oct 2026, so convert publish times from your own time zone after that date.

---

## 1. Calendar

| Day | Date | Task | Output |
|---|---|---|---|
| 1 | Thu 22 Oct | Create the channel. **Phone-verify the account** (needed for videos over 15 min [YouTube upload help]). Studio → Settings → Channel → Advanced settings: untick "Allow automatic dubbing". Run the VidIQ keyword list from File 2 §3.2 and fill the decision table. | Channel live, keyword table |
| 2 | Fri 23 Oct | Audio: record 2–3 rain takes (30–40 min each), or pick CC0 files on Freesound (licence filter = CC0). Start the licence log (file → URL → licence). Pick and trim footage (File 1 §3.2). | Raw audio + clips + log |
| 3 | Sat 24 Oct | Make the 1815 s audio mix. Run the 60 s benchmark (File 1 §2). Run `build.sh` with a small `COPIES` to prove the chain. Full-decode check, listen to a loop seam. Make a thumbnail (any free editor). | Tested chain, V1 file |
| **4** | **Sun 25 Oct** | **Publish V1: concept #1, "Regen am Fenster", 10 h colour.** Upload the evening before and schedule it for 17:00–19:00 German time (before bedtime). 10-hour files can take a long time to process; I did not measure this, so upload several hours ahead. | V1 live |
| 5–6 | 26–27 Oct | Build V2 audio (different source from V1) and the black-screen file. **At 48 h after V1:** record impressions, CTR, views. Do not edit title or thumbnail before 48 h. | V2 file |
| **7** | **Wed 28 Oct** | **Publish V2: concept #7, black screen, 10 h**, with audio different from V1. If V1 has ≥ 500 impressions and CTR < 2%, replace V1's thumbnail first, then its title. | V2 live |
| 8–10 | 29–31 Oct | Build V3 (concept #2, distant thunder; limit thunder peaks). Log all metrics for V1/V2 at 7 d. | V3 file |
| **11** | **Sun 1 Nov** | **Publish V3: concept #2, rain with distant thunder.** | V3 live |
| 12–13 | 2–3 Nov | Build V4 (concept #3 car roof, or the next-best concept per the table). | V4 file |
| **14** | **Wed 4 Nov** | **Checkpoint 1 (decision gate, §3). Publish V4.** | V4 live, decision |
| 15–17 | 5–7 Nov | Apply the gate's decision. Build V5 (concept #4, tent or tin roof, own recording if possible). Run the Geography check (§2). | V5 file |
| **18** | **Sun 8 Nov** | **Publish V5.** | V5 live |
| 19–20 | 9–10 Nov | Build V6 (concept #5 forest, or a second video in the best-performing concept with new audio and scene). | V6 file |
| **21** | **Wed 11 Nov** | **Checkpoint 2 (§3). Publish V6.** | V6 live, decision |
| 22–24 | 12–14 Nov | Build V7: **first English-titled upload** with its own audio and scene (File 2 §3.4). Add translated title and description (Studio → Content → [video] → Languages) to your best videos. | V7 file |
| **25** | **Sun 15 Nov** | **Publish V7 (English).** | V7 live |
| 26–27 | 16–17 Nov | Build V8 (concept #6 fire + rain, or a black-screen of the best-performing audio, per §3). | V8 file |
| **28** | **Wed 18 Nov** | **Publish V8.** | V8 live |
| 29 | Thu 19 Nov | Pull all metrics into the log; export the Studio data if you want a backup. | Data complete |
| **30** | **Fri 20 Nov** | **Final decision (§3).** | Go / pivot / stop |

Each video needs its own audio mix and scene (File 2 §0). If time runs short, publish fewer videos rather than reusing loops.

---

## 2. What to read in YouTube Studio

Analytics → Content → select the video.

| Metric | Where | Why |
|---|---|---|
| Impressions, Impressions CTR | Reach | Title and thumbnail fit |
| Traffic source types and **YouTube search → search terms** | Reach | Whether your keyword is what brings viewers |
| Average view duration | Engagement | Hours per viewer |
| **Audience retention graph, value at 1:00:00** | Engagement | Do viewers stay past the first hour? |
| Geography | Audience | Are viewers in Germany, Austria and Switzerland? File 2 §1 warns the keyword data may overstate other markets |
| Views at 48 h / 7 d / 14 d | Content table | Growth shape |

Ignore "average percentage viewed" on a 10-hour video; it will always look tiny.

Log one row per video: concept, keyword, title, thumbnail version, audio source, publish date, the metrics above.

---

## 3. Decision criteria

**Per-video signals (check at 7 and 14 days):**

| Signal | Weak | Acceptable | Strong |
|---|---|---|---|
| CTR (after ≥ 1,000 impressions) | < 2% → change thumbnail | 2–5% | > 5% |
| Average view duration | < 20 min (people are leaving, not sleeping) | 20–60 min | ≥ 60 min |
| Retention at 1:00:00 | < 10% | 10–20% | ≥ 20% |
| YouTube search share of views | < 20% (traffic is not keyword-driven) | 20–40% | ≥ 40% (the keyword works) |

**Checkpoint 1 (Day 14) and Checkpoint 2 (Day 21):**
- **Double down** on a concept if one of its videos meets at least 2 of 3: ≥ 500 views in its first 10 days, average view duration ≥ 60 min, YouTube search share ≥ 40%. Next uploads: same keyword family, new audio and scene.
- **Pivot** if every video is under 300 views and under 2,000 impressions after 10 days. Pivot options in this order: (1) keyword angle from the unpulled candidates in File 2 §3.2; (2) bilingual tail on the title; (3) black screen as the main format; (4) a new thumbnail style. Change one thing at a time and give each change at least 7 days.
- **Impressions fine, views low:** a thumbnail/title problem. **Views fine, average duration low:** the scene or audio is wrong for sleep (sudden sounds, level changes) or viewers are not using it to sleep.

**Day 30 final decision:**
- **Go:** at least one concept hit "double down" and the channel total is rising week over week.
- **Pivot:** best video between 300 and 1,000 views in 14 days, or search share is low but retention is good. Keep going 30 more days with the changed variable.
- **Stop or restructure:** channel total under 3,000 views after 8 videos and no video above 1,000. That is a result: this niche, under these constraints, did not respond. Check monetization status in Studio → Earn separately; I did not verify the current thresholds.

Two questions this calendar does not answer: whether YouTube accepts the channel into the Partner Program (File 2 §0), and whether German demand for each scene exists (File 2 §3.2). Settle both through the Day-1 keyword pulls and the Studio data above.
