#!/usr/bin/env bash
# Wait for the segment render to finish, then assemble and report.
# Runs detached so the interactive session is never blocked on it.
set -u
cd "$(dirname "$0")/.."
EXPECTED=18
for i in $(seq 1 720); do            # up to 6 hours, 30 s steps
  n=$(ls build/video2/segments/*.mp4 2>/dev/null | wc -l)
  if ! pgrep -f "render_graphics.py 2560" >/dev/null 2>&1; then
    echo "renderer stopped with $n/$EXPECTED segments"
    break
  fi
  sleep 30
done

n=$(ls build/video2/segments/*.mp4 2>/dev/null | wc -l)
if [ "$n" -lt "$EXPECTED" ]; then
  echo "INCOMPLETE: only $n of $EXPECTED segments" > tmp/finalize.log
  exit 1
fi

echo "assembling from $n segments" >> tmp/finalize.log
python3 scripts/assemble.py >> tmp/finalize.log 2>&1
python3 scripts/youtube_meta.py >> tmp/finalize.log 2>&1
echo "DONE" >> tmp/finalize.log
