#!/bin/bash
# ============================================================
# Připraví archiv pro přenos na VPS
# Spusť na SVÉM počítači (WSL), pak nahraj na VPS
# ============================================================
set -e

cd /root/restaurant-outreach
echo "Balím projekt pro přenos na VPS..."

tar czf /tmp/strankyprovas_pipeline.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  --exclude='demos' \
  --exclude='demos-*' \
  --exclude='output' \
  --exclude='logs/*.log' \
  .

SIZE=$(du -sh /tmp/strankyprovas_pipeline.tar.gz | cut -f1)
echo ""
echo "✅ Archiv: /tmp/strankyprovas_pipeline.tar.gz ($SIZE)"
echo ""
echo "Přenosu na VPS:"
echo "  scp /tmp/strankyprovas_pipeline.tar.gz root@TVOJE_VPS_IP:/root/"
echo ""
echo "Na VPS:"
echo "  cd /root && tar xzf strankyprovas_pipeline.tar.gz -C restaurant-outreach --strip-components=0"
echo "  mkdir -p restaurant-outreach && tar xzf strankyprovas_pipeline.tar.gz -C restaurant-outreach"
echo "  cd restaurant-outreach && bash deploy/vps_setup.sh"
