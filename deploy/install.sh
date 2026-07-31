#!/usr/bin/env bash
set -euo pipefail
APP_DIR="${1:-/opt/family-operations-dashboard}"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"
echo "Installed. Edit deploy/family-dashboard.service and /etc/family-dashboard.env before enabling." 
