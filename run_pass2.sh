#!/bin/bash
# Pass 2 – top 34 měst s target=5 (doplnění k ~300 draftům)
cd /root/restaurant-outreach

CITIES="Praha,Brno,Ostrava,Plzeň,Liberec,Olomouc,České Budějovice,Hradec Králové,Ústí nad Labem,Pardubice,Zlín,Havířov,Kladno,Most,Opava,Frýdek-Místek,Karviná,Jihlava,Teplice,Děčín,Chomutov,Přerov,Jablonec nad Nisou,Mladá Boleslav,Prostějov,Česká Lípa,Třebíč,Znojmo,Příbram,Tábor,Karlovy Vary,Kolín,Trutnov,Šumperk"

INDUSTRIES=("restaurace" "kavarna" "penzion" "kosmetika" "kadernictvi" "zubni" "masaze" "autoservis" "psycholog")

mkdir -p logs

for INDUSTRY in "${INDUSTRIES[@]}"; do
    LOG="logs/run_${INDUSTRY}_$(date +%Y%m%d_%H%M%S)_pass2.log"
    echo "▶ Spouštím: $INDUSTRY → $LOG"
    nohup venv/bin/python3 -u run_all_cities.py \
        --cities "$CITIES" \
        --target 5 \
        --industry "$INDUSTRY" \
        > "$LOG" 2>&1 &
    echo $! > "/tmp/pid2_${INDUSTRY}.pid"
    sleep 3
done

echo ""
echo "✅ Pass2 spuštěno (${#INDUSTRIES[@]} procesů, target=5)"
echo "Sledovat: tail -f logs/run_*$(date +%Y%m%d)*pass2.log"
