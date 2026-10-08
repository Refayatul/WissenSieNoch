#!/usr/bin/env python3
"""narration.wav -> captions.srt (German, short cues, CPU only).
Usage: python3 captions.py narration.wav captions.srt"""
import sys
from faster_whisper import WhisperModel

wav, srt = sys.argv[1], sys.argv[2]
model = WhisperModel("small", device="cpu", compute_type="int8")
segments, _ = model.transcribe(wav, language="de", word_timestamps=True, beam_size=5)

words = [w for s in segments for w in s.words]
cues, cur = [], []
for w in words:
    cur.append(w)
    text = "".join(x.word for x in cur).strip()
    if len(cur) >= 7 or len(text) >= 38 or w.word.strip().endswith((".", "?", "!")):
        cues.append(cur); cur = []
if cur:
    cues.append(cur)

def ts(t):
    h, rem = divmod(t, 3600); m, s = divmod(rem, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02},{int((s % 1) * 1000):03}"

with open(srt, "w", encoding="utf-8") as f:
    for i, c in enumerate(cues, 1):
        f.write(f"{i}\n{ts(c[0].start)} --> {ts(c[-1].end)}\n{''.join(x.word for x in c).strip()}\n\n")
print(f"{len(cues)} cues -> {srt}")
