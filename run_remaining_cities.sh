#!/bin/bash
cd /root/restaurant-outreach

# Zbývajících 50 měst (ta co nebyla v prvním runu)
CITIES="Kroměříž,Uherské Hradiště,Hodonín,Břeclav,Cheb,Nový Jičín,Vsetín,Sokolov,Písek,Strakonice,Havlíčkův Brod,Žďár nad Sázavou,Vyškov,Blansko,Náchod,Valašské Meziříčí,Beroun,Kutná Hora,Uherský Brod,Mělník,Hranice,Rožnov pod Radhoštěm,Klatovy,Bruntál,Pelhřimov,Dvůr Králové nad Labem,Jičín,Rychnov nad Kněžnou,Zábřeh,Šternberk,Nymburk,Jindřichův Hradec,Rakovník,Mariánské Lázně,Litovel,Kopřivnice,Domažlice,Prachatice,Jeseník,Turnov,Český Krumlov,Poděbrady,Bílovec,Litvínov,Vrchlabí,Holešov,Strážnice,Rýmařov,Rokycany,Třinec"

# Jen odvětví co skončila s nízkým počtem
INDUSTRIES=("kosmetika" "masaze" "autoservis" "psycholog" "kadernictvi" "zubni")

mkdir -p logs

for INDUSTRY in "${INDUSTRIES[@]}"; do
    LOG="logs/run_${INDUSTRY}_$(date +%Y%m%d_%H%M%S)_extra.log"
    echo "▶ $INDUSTRY (50 dalších měst) → $LOG"
    nohup venv/bin/python3 -u run_all_cities.py \
        --cities "$CITIES" \
        --target 2 \
        --industry "$INDUSTRY" \
        > "$LOG" 2>&1 &
    echo $! > "/tmp/pid_${INDUSTRY}_extra.pid"
    sleep 2
done

echo "✅ Spuštěno ${#INDUSTRIES[@]} procesů pro zbývajících 50 měst."
