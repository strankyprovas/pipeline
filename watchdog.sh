#!/bin/bash
# Watchdog – kontroluje každých 15 minut, že všech 9 pipeline procesů běží.
# Pokud některý chybí, restartuje ho s target 5.
# Loguje akce do logs/watchdog.log.

cd /root/restaurant-outreach

INDUSTRIES=(psycholog kadernictvi kosmetika masaze kavarna penzion autoservis zubni restaurace)
WATCHDOG_LOG="logs/watchdog.log"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$WATCHDOG_LOG"
}

start_industry() {
  local ind="$1"
  local ts=$(date +%Y%m%d_%H%M)
  local logfile="logs/${ind}_${ts}.log"
  setsid nohup venv/bin/python3 -u run_all_cities.py --industry "$ind" --target 5 > "$logfile" 2>&1 < /dev/null &
  disown
  log "  → START $ind → log: $logfile"
}

log "=== Watchdog started (PID $$) ==="

while true; do
  for ind in "${INDUSTRIES[@]}"; do
    # Kontroluj, jestli běží proces s tímto odvětvím
    if ! pgrep -f "run_all_cities.py --industry $ind" > /dev/null 2>&1; then
      log "❌ Chybí proces: $ind — restartuji"
      start_industry "$ind"
    fi
  done

  # Status report
  alive=$(pgrep -f "run_all_cities.py --industry" | wc -l)
  log "📊 Živých procesů: $alive/9"

  sleep 900  # 15 minut
done
