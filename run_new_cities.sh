#!/bin/bash
# Spouští všech 9 odvětví paralelně pro NOVÁ střední/menší města (ne top 34)
# Cíl: ~300 nových draft+demo
# Spuštění: bash run_new_cities.sh

cd /root/restaurant-outreach

# Střední a menší města, která NEJSOU v původním run_all_industries.sh (top 34)
# ~60 měst z celé ČR – všechny kraje zastoupeny
CITIES="Kutná Hora,Benešov,Beroun,Mělník,Nymburk,Poděbrady,Slaný,Říčany,Strakonice,Písek,Jindřichův Hradec,Český Krumlov,Třeboň,Klatovy,Domažlice,Rokycany,Sokolov,Cheb,Mariánské Lázně,Litoměřice,Louny,Roudnice nad Labem,Varnsdorf,Žatec,Rumburk,Turnov,Nový Bor,Jičín,Náchod,Dvůr Králové nad Labem,Vrchlabí,Chrudim,Litomyšl,Svitavy,Vysoké Mýto,Česká Třebová,Havlíčkův Brod,Žďár nad Sázavou,Humpolec,Pelhřimov,Velké Meziříčí,Blansko,Hodonín,Vyškov,Boskovice,Mikulov,Uherské Hradiště,Kroměříž,Uherský Brod,Vsetín,Krnov,Nový Jičín,Bohumín,Kopřivnice,Třinec,Zábřeh,Šternberk,Hranice,Jeseník,Bruntál"

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
    sleep 2  # malý odstup aby se nepřetěžovalo Sheets API najednou
done

echo ""
echo "✅ Spuštěno ${#INDUSTRIES[@]} procesů paralelně."
echo "PIDs: $(cat /tmp/pid_*.pid | tr '\n' ' ')"
echo ""
echo "Sledovat vše: tail -f /root/restaurant-outreach/logs/run_*$(date +%Y%m%d)*.log"
echo "Nebo konkrétní: tail -f logs/run_restaurace_*.log"
