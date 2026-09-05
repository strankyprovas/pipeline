#!/bin/bash
# Sériový běh všech odvětví přes ~223 kurátorovaných měst – jeden proces naráz.
# Spouštěno přes systemd (outreach.service): auto-start při bootu + restart při pádu.
# Dedup v DB zajistí navázání tam, kde to skončilo. Žádné duplikáty.
set -uo pipefail
cd /root/restaurant-outreach || exit 1

LOGDIR=/root/restaurant-outreach/outreach-logs
mkdir -p "$LOGDIR"
PY=/root/restaurant-outreach/venv/bin/python3
TARGET=20
CITIES="$(cat /root/restaurant-outreach/cities_list.txt)"

INDUSTRIES="pekarna kvetinarstvi restaurace penzion kavarna kadernictvi autoservis zubni masaze kosmetika psycholog"

echo "=== START $(date) ===" >> "$LOGDIR/_serial_master.log"
for ind in $INDUSTRIES; do
    echo "[$(date +%F\ %H:%M:%S)] START odvetvi: $ind" >> "$LOGDIR/_serial_master.log"
    # Odvětví nesmí shodit celý běh: případný pád jen zalogujeme a jdeme dál
    $PY run_all_cities.py --cities "$CITIES" --target $TARGET --industry "$ind" >> "$LOGDIR/$ind.log" 2>&1 || \
        echo "[$(date +%F\ %H:%M:%S)] WARN: $ind skoncilo s chybou (exit $?)" >> "$LOGDIR/_serial_master.log"
    echo "[$(date +%F\ %H:%M:%S)] DONE odvetvi: $ind" >> "$LOGDIR/_serial_master.log"
done
echo "=== HOTOVO $(date) ===" >> "$LOGDIR/_serial_master.log"
# Po dokončení všech odvětví: značka, ať systemd nerestartuje donekonečna
touch "$LOGDIR/.done"
