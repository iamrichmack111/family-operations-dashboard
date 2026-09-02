#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

echo "===== STOP OLD DASHBOARD ====="
sudo systemctl stop family-dashboard 2>/dev/null || true

if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k 8011/tcp 2>/dev/null || true
fi

echo "===== INSTALL APP ====="
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "===== ENVIRONMENT ====="
if [[ ! -f /etc/family-dashboard.env ]]; then
  SECRET="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  sudo tee /etc/family-dashboard.env >/dev/null <<ENVEOF
FAMILY_DASHBOARD_SECRET=$SECRET
FAMILY_DASHBOARD_HOST=0.0.0.0
FAMILY_DASHBOARD_PORT=8011
FLASK_DEBUG=0
ENVEOF
else
  if sudo grep -q '^FAMILY_DASHBOARD_HOST=' /etc/family-dashboard.env; then
    sudo sed -i 's/^FAMILY_DASHBOARD_HOST=.*/FAMILY_DASHBOARD_HOST=0.0.0.0/' /etc/family-dashboard.env
  else
    echo 'FAMILY_DASHBOARD_HOST=0.0.0.0' | sudo tee -a /etc/family-dashboard.env >/dev/null
  fi
  if sudo grep -q '^FAMILY_DASHBOARD_PORT=' /etc/family-dashboard.env; then
    sudo sed -i 's/^FAMILY_DASHBOARD_PORT=.*/FAMILY_DASHBOARD_PORT=8011/' /etc/family-dashboard.env
  else
    echo 'FAMILY_DASHBOARD_PORT=8011' | sudo tee -a /etc/family-dashboard.env >/dev/null
  fi
fi
sudo chmod 600 /etc/family-dashboard.env

echo "===== INSTALL SYSTEMD SERVICE ====="
sudo cp deploy/family-dashboard.service /etc/systemd/system/family-dashboard.service
sudo systemctl daemon-reload
sudo systemctl enable family-dashboard

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow 8011/tcp >/dev/null 2>&1 || true
fi

sudo systemctl restart family-dashboard
sleep 2

echo "===== SERVICE ====="
sudo systemctl --no-pager --full status family-dashboard || true

echo "===== PORT 8011 ====="
sudo ss -ltnp | grep ':8011' || true

echo "===== HTTP CHECK ====="
curl -I --max-time 5 http://127.0.0.1:8011 || true

echo
echo "Family Operations Dashboard: http://family.local:8011"
