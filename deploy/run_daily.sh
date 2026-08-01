#!/bin/bash
# ============================================================
# Denní spuštění pipeline – všechna odvětví, všechna města
# Spouštěno automaticky cronem každý den v 8:00
# ============================================================
cd /root/restaurant-outreach
source /root/.bashrc 2>/dev/null || true

DATE=$(date +%Y%m%d_%H%M%S)
echo ""
echo "=============================="
echo "START: $(date)"
echo "=============================="

# Zastav případné zbývající procesy z předchozího běhu
pkill -f "run_all_cities.py" 2>/dev/null || true
sleep 2

# Spusť všechna odvětví paralelně
for industry in restaurace kavarna penzion kosmetika kadernictvi zubni masaze autoservis psycholog; do
  nohup venv/bin/python3 run_all_cities.py \
    --industry $industry \
    --target 2 \
    > logs/daily_${DATE}_${industry}.log 2>&1 &
  echo "▶ $industry (PID $!)"
done

echo ""
echo "Všechna odvětví spuštěna. Logy: logs/daily_${DATE}_*.log"
echo "Pipeline doběhne za ~2–4 hodiny."

# Počkej až všechny procesy doběhnou
wait
echo ""
echo "=============================="
echo "KONEC: $(date)"
echo "=============================="

# Souhrn draftů
echo "Nové drafty dnes:"
for f in logs/daily_${DATE}_*.log; do
  industry=$(echo $f | grep -o '[a-z]*\.log' | sed 's/\.log//')
  count=$(grep -c "Gmail draft" $f 2>/dev/null || echo 0)
  echo "  $industry: $count"
done
