#!/bin/bash
# Spouští všech 9 odvětví paralelně, každé s top 34 městy, target=2
# Výsledek: ~300 nových draft+demo

cd /root/restaurant-outreach

CITIES="Praha,Brno,Ostrava,Plzeň,Liberec,Olomouc,České Budějovice,Hradec Králové,Ústí nad Labem,Pardubice,Zlín,Havířov,Kladno,Most,Opava,Frýdek-Místek,Karviná,Jihlava,Teplice,Děčín,Chomutov,Přerov,Jablonec nad Nisou,Mladá Boleslav,Prostějov,Česká Lípa,Třebíč,Znojmo,Příbram,Tábor,Karlovy Vary,Kolín,Trutnov,Šumperk"

INDUSTRIES=("restaurace" "kavarna" "penzion" "kosmetika" "kadernictvi" "zubni" "masaze" "autoservis" "psycholog")

mkdir -p logs

for INDUSTRY in "${INDUSTRIES[@]}"; do
    LOG="logs/run_${INDUSTRY}_$(date +%Y%m%d_%H%M%S).log"
    echo "▶ Spouštím: $INDUSTRY → $LOG"
    nohup venv/bin/python3 -u run_all_cities.py \
        --cities "$CITIES" \
        --target 2 \
        --industry "$INDUSTRY" \
        > "$LOG" 2>&1 &
    echo $! > "/tmp/pid_${INDUSTRY}.pid"
    sleep 2  # malý odstup aby se nepřetěžovalo API najednou
done

echo ""
echo "✅ Spuštěno ${#INDUSTRIES[@]} procesů paralelně."
echo "Sledovat vše: tail -f logs/run_*.log"
