#!/bin/bash
# Automatické follow-up emaily – spouštět každý den ráno přes cron
# Nastavení: crontab -e → přidat řádek:
#   0 9 * * * /root/restaurant-outreach/run_daily_followups.sh
cd /root/restaurant-outreach
venv/bin/python3 check_followups.py --send --days 5 --delay 30 >> /tmp/followups.log 2>&1
