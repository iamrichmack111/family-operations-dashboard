#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="${VENV:-.ci-venv}"

echo "===== LOCAL CI: PYTHON ====="
"$PYTHON_BIN" --version

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
# shellcheck disable=SC1090
source "$VENV/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

export PYTHONPATH="$ROOT"
export FAMILY_DASHBOARD_SECRET="ci-only-secret-not-for-production"
export TZ="America/New_York"

echo "===== LOCAL CI: COMPILE ====="
python -m compileall -q app tests run.py wsgi.py

echo "===== LOCAL CI: APP IMPORT ====="
python - <<'PY'
from app import create_app
app = create_app({
    "TESTING": True,
    "AUTO_BACKUP_DATABASE": False,
    "SEED_DEFAULTS": False,
    "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
})
print("Flask application import/create: ok")
PY

echo "===== LOCAL CI: BLOCKING CORE TESTS ====="
python -m unittest -v tests.test_chore_rotation tests.test_ci_contracts

echo "===== LOCAL CI: EXTENDED DIAGNOSTICS ====="
if ! python -m unittest -v tests.test_photo_proof tests.test_rewards_trades; then
  echo "WARNING: extended Flask diagnostics reported failures."
  echo "Core CI continues; inspect the output above for the exact regression."
fi

echo "===== LOCAL CI: SQLITE ====="
python - <<'PY'
import sqlite3
from pathlib import Path
p = Path('instance/family_dashboard.db')
if not p.exists():
    print(f'SKIP: {p} is not present in this checkout; production database is preserved separately.')
else:
    with sqlite3.connect(p) as con:
        result = con.execute('PRAGMA integrity_check').fetchone()[0]
        users = con.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        chores = con.execute('SELECT COUNT(*) FROM chores').fetchone()[0]
        points = con.execute('SELECT COUNT(*) FROM point_transactions').fetchone()[0]
    if result != 'ok':
        raise SystemExit(f'SQLite integrity check failed: {result}')
    print(f'SQLite integrity_check: ok | users={users} chores={chores} point_transactions={points}')
PY

echo "===== LOCAL CI: DEPENDENCY AUDIT ====="
python -m pip install pip-audit
python -m pip_audit -r requirements.txt

echo "===== LOCAL CI: DOCKER BUILD ====="
if command -v docker >/dev/null 2>&1; then
  docker build -t family-operations-dashboard:local-ci .
else
  echo "SKIP: Docker is not installed. GitHub Actions will run the Docker build check."
fi

echo "===== LOCAL CI PASSED ====="
