#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required." >&2
  exit 1
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
if ! python -c 'import flask, flask_sqlalchemy, flask_wtf, PIL' >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

export FAMILY_DASHBOARD_SECRET="${FAMILY_DASHBOARD_SECRET:-$(python -c 'import secrets; print(secrets.token_hex(32))')}"
export FAMILY_DASHBOARD_PORT="${FAMILY_DASHBOARD_PORT:-8010}"

echo "Family Operations Dashboard"
echo "Open: http://127.0.0.1:${FAMILY_DASHBOARD_PORT}"
echo "Press Ctrl+C to stop."
exec python run.py
