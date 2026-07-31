# 🏠 Family Operations Dashboard v3

A private, dark-mode Flask household operations system designed for Tailscale Serve.

## Included

- 👑 Parent dashboards for Samantha and Jeremy
- 🗝️ House-manager approval access for Jasmin
- 🌟 Child dashboards for Zara and Aria
- 🔔 role-aware notifications
- 🧹 weighted chore rotation, completion, approval, redo, excuse, notes, weekly locking, and regeneration
- 📚 homework with due dates, recurring labels, points, attachments, archive, approval, and redo
- 💬 direct messages, replies, read tracking, and optional child-to-child restrictions
- 🔒 private grievances visible and answerable only by parents
- ⚠️ violations with categories, evidence attachments, point deductions, receipt acknowledgement, appeal, parent follow-up, revision history, and resolution
- ⭐ auditable point ledger, reversals, balances, and historical monetary rate snapshots
- 📊 Chart.js dashboards and 30-day reports
- 🧾 filterable activity history and login history in exports
- 📦 CSV, JSON, and SQLite ZIP exports
- 🗄️ automatic rotating SQLite backups at startup
- 🔐 CSRF protection, password hashing, secure cookies, session timeout, and temporary lockouts after repeated failed logins

## Install

```bash
cd ~
unzip ~/Downloads/Family-Operations-Dashboard-Flask-v3.zip
cd ~/family-operations-flask-v3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Start on a free port

```bash
export FAMILY_DASHBOARD_SECRET="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export FAMILY_DASHBOARD_PORT=8010
python run.py
```

Open `http://127.0.0.1:8010`.

Initial accounts are Samantha, Jeremy, Jasmin, Zara, and Aria. Their temporary PIN is `1234`. Parents should immediately change every PIN in **Parent Center → Users and PINs**.

## Production server

```bash
source .venv/bin/activate
gunicorn --workers 2 --bind 127.0.0.1:8010 --timeout 60 'wsgi:app'
```

## Tailscale Serve

```bash
sudo tailscale serve reset
sudo tailscale serve --bg http://127.0.0.1:8010
sudo tailscale serve status
```

Use Serve, not Funnel, for private family information.

## Database migrations

The application creates a fresh SQLite schema automatically. To place future model changes under Flask-Migrate:

```bash
export FLASK_APP=wsgi:app
flask db init        # once only
flask db migrate -m "Describe model change"
flask db upgrade
```

## Storage

- Database: `instance/family_dashboard.db`
- Uploaded evidence/homework: `uploads/`
- Automatic backups: `backups/`
- Downloadable exports: `exports/`

## Roles

- **Parents:** full administration, PINs, schedules, homework, violations, points, grievances, reports, exports.
- **Manager:** approve or request redo, view operational reports, messages, personal grievances/violations. No parent grievance inbox, PIN controls, violation issuance, or monetary settings.
- **Children:** complete assigned work, view personal points and notices, acknowledge or appeal personal violations, message parents/manager, submit private grievances.


## Family News visibility (v4)

All signed-in family members, including Aria and Zara, can open **Family News** and see safe household activity such as chore completion, approvals, homework, messages, schedule actions, and positive recognition.

The shared feed automatically excludes private grievances, detailed violations, PIN/password changes, login history, account administration, monetary-rate changes, backups, exports, and parent-only notes. Each user also has a **My activity** view. Samantha and Jeremy receive a separate **Parent audit** view containing the full administrative record.
