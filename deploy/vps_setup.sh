#!/bin/bash
# ============================================================
# StránkyProVás – Pipeline VPS Setup Script
# Funguje na: Ubuntu 22.04 / 24.04 (Oracle Cloud Free Tier, Hetzner, atd.)
# Spustit jako root: bash vps_setup.sh
# ============================================================
set -e

echo "=== StránkyProVás Pipeline Setup ==="
echo ""

# 1. Základní balíčky
echo "[1/8] Instaluji systémové závislosti..."
apt-get update -qq
apt-get install -y -qq python3.12 python3.12-venv python3-pip git curl unzip

# 2. GitHub CLI
echo "[2/8] Instaluji GitHub CLI..."
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  > /etc/apt/sources.list.d/github-cli.list
apt-get update -qq && apt-get install -y -qq gh

# 3. Zkopíruj projekt (očekává se že je v /root/restaurant-outreach)
echo "[3/8] Připravuji projekt..."
cd /root/restaurant-outreach

# 4. Python virtualenv + závislosti
echo "[4/8] Instaluji Python závislosti..."
python3.12 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q \
  requests gspread google-auth google-auth-oauthlib google-auth-httplib2 \
  google-api-python-client anthropic playwright beautifulsoup4 dnspython

# 5. Playwright browsers
echo "[5/8] Instaluji Playwright..."
venv/bin/playwright install chromium --with-deps 2>/dev/null || true

# 6. Git konfigurace
echo "[6/8] Konfiguruji Git..."
git config --global user.name "StrankyProVas Bot"
git config --global user.email "matyas.vrbaa@gmail.com"
git config --global credential.helper "store"

# 7. Cron job – každý den v 8:00 ráno (CET = UTC+1)
echo "[7/8] Nastavuji cron job (každý den 8:00 CET)..."
CRON_CMD="0 7 * * * cd /root/restaurant-outreach && bash deploy/run_daily.sh >> logs/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v "run_daily.sh"; echo "$CRON_CMD") | crontab -
echo "  ✅ Cron nastaven"

# 8. Vytvoř potřebné složky
mkdir -p logs

echo ""
echo "=== Setup hotový! ==="
echo ""
echo "Zbývá dokončit manuálně:"
echo "  1. gh auth login   (přihlášení do GitHubu)"
echo "  2. Zkontroluj že token.pickle a credentials.json jsou v /root/restaurant-outreach/"
echo "  3. Nastav ANTHROPIC_API_KEY do /root/.bashrc:"
echo "     echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> /root/.bashrc"
echo "  4. Spusť test: cd /root/restaurant-outreach && venv/bin/python3 main.py Praha 1"
echo ""
echo "Pipeline se bude spouštět automaticky každý den v 8:00 ráno."
