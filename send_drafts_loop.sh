#!/bin/bash
# Spouští send_drafts.py každých 30 minut – zachytí nové drafty z pipeline.
# Pokud už instance běží, přeskočí.
cd /root/restaurant-outreach

LOCKFILE="/tmp/send_drafts.lock"
LOG="/tmp/send_drafts_loop.log"

if [ -f "$LOCKFILE" ] && kill -0 "$(cat $LOCKFILE)" 2>/dev/null; then
    echo "$(date '+%H:%M:%S') Předchozí instance stále běží (PID $(cat $LOCKFILE)), přeskakuji." >> "$LOG"
    exit 0
fi

echo "$(date '+%H:%M:%S') Spouštím send_drafts.py..." >> "$LOG"
venv/bin/python3 -u send_drafts.py --delay 60 >> "$LOG" 2>&1 &
echo $! > "$LOCKFILE"
echo "$(date '+%H:%M:%S') PID: $(cat $LOCKFILE)" >> "$LOG"
