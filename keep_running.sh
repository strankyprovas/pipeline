#!/bin/bash
# Strážce: restartuje spadlé pipeline pro každé odvětví
cd /root/restaurant-outreach
INDUSTRIES="restaurace kavarna kosmetika kadernictvi zubni masaze autoservis psycholog penzion"
for ind in $INDUSTRIES; do
  if ! pgrep -f "run_all_cities.py --industry $ind" > /dev/null; then
    nohup venv/bin/python3 run_all_cities.py --industry $ind --target 30 --min-pop 5000 \
      > /root/restaurant-outreach/logs_$ind.txt 2>&1 &
    echo "$(date '+%H:%M:%S') restartoval $ind"
  fi
done
