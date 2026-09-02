# 🏠 Family Operations Dashboard v7

A private, dark-mode Flask household operations system designed for Tailscale Serve.

## Included

- 👑 Parent dashboards for Samantha and Jeremy
- 🗝️ House-manager approval access for Jasmin
- 🌟 Child dashboards for Zara and Aria
- 🔔 role-aware notifications
- 🧹 weighted chore rotation, completion, approval, redo, excuse, notes, weekly locking, and regeneration
- 📸 required chore-completion photo proof with protected parent/manager approval
- ⚖️ strict three-person rotation: everyone receives Basement and Bathrooms exactly once per three-day cycle, with no same-day overlap or in-cycle repeats
- 🧭 personal next-day assignment preview, server-side early-completion protection, and a visible Basement/Bathrooms fairness table
- 📚 homework with due dates, recurring labels, points, attachments, archive, approval, and redo
- 💬 direct messages, replies, read tracking, and optional child-to-child restrictions
- 🔒 private grievances visible and answerable only by parents
- ⚠️ violations with categories, evidence attachments, point deductions, receipt acknowledgement, appeal, parent follow-up, revision history, and resolution
- ⭐ auditable point ledger, reversals, balances, and historical monetary rate snapshots
- 📊 seven Chart.js dashboard graphs, including chore status, weekly review flow, daily point movement, and 30-day reports
- 🧾 filterable activity history and login history in exports
- 📦 CSV, JSON, and SQLite ZIP exports
- 🗄️ automatic rotating SQLite backups at startup
- 🔐 CSRF protection, password hashing, secure cookies, session timeout, and temporary lockouts after repeated failed logins

## Install

```bash
cd ~
unzip ~/Downloads/family-operations-dashboard-fair-rotation-tomorrow-v7-with-data.zip
cd ~/family-operations-dashboard-main
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

## Automatic database migration

At startup, the application safely adds the chore photo-proof column when an
older database does not have it. The migration is additive and idempotent: it
does not recreate tables or delete existing users, PIN hashes, chores, points,
or history. The normal rotating database backup runs before an existing SQLite
database is migrated.

To place future model changes under Flask-Migrate:

```bash
export FLASK_APP=wsgi:app
flask db init        # once only
flask db migrate -m "Describe model change"
flask db upgrade
```

## Storage

- Database: `instance/family_dashboard.db`
- Uploaded evidence/homework: `uploads/`
- Chore photo proof: `uploads/chore_proofs/`
- Automatic backups: `backups/`
- Downloadable exports: `exports/`

## Roles

- **Parents:** full administration, PINs, schedules, homework, violations, points, grievances, reports, exports.
- **Manager:** approve or request redo, view operational reports, messages, personal grievances/violations. No parent grievance inbox, PIN controls, violation issuance, or monetary settings.
- **Children:** complete assigned work, view personal points and notices, acknowledge or appeal personal violations, message parents/manager, submit private grievances.

## Chore photo proof

Marking a chore complete requires a JPEG, PNG, or WebP photo no larger than
8 MB. The server verifies the real image format, rejects animated or oversized
images, strips metadata by re-encoding the upload, and generates a random safe
storage filename. Parents and managers can see the proof on the approval screen.
Approve remains locked if the database reference or stored photo is missing;
Needs Redo and Excuse remain available for older proofless records.

Run all migration, photo workflow, approval protection, upload safety, and fair
rotation tests with:

```bash
python -m unittest discover -v
```

## Fair chore rotation

The seven daily chores rotate among Jasmin, Zara, and Aria in a repeating
three-day cycle. Each person receives every chore exactly once during the cycle.
That explicitly includes one Basement assignment and one Bathrooms assignment
per person, with no repeats inside the cycle and no person receiving both on the
same day. Daily workload weights are 5, 6, and 6 points and rotate with the
people; after three days, each person has exactly 17 possible points. **Cook and
dishes** and **Counters and stove** are always assigned to different people on
the same day.

On startup, untouched current and future chores are reconciled to this rotation.
Completed, approved, excused, and Needs Redo records are never reassigned. The
dashboard shows each child or manager their own next-day assignments; parents
see the complete next-day family plan.

After upgrading an existing installation, open **Parent Center → Schedule**,
unlock the current week if needed, and choose **Regenerate** to replace the old
assignments with the fair rotation. Completed historical chores are not changed
automatically.

## GitHub review workflow

See [`GITHUB_REVIEW.md`](GITHUB_REVIEW.md) for the branch, push, pull-request,
reviewer, and separate-account setup.


## Family News visibility (v4)

All signed-in family members, including Aria and Zara, can open **Family News** and see safe household activity such as chore completion, approvals, homework, messages, schedule actions, and positive recognition.

The shared feed automatically excludes private grievances, detailed violations, PIN/password changes, login history, account administration, monetary-rate changes, backups, exports, and parent-only notes. Each user also has a **My activity** view. Samantha and Jeremy receive a separate **Parent audit** view containing the full administrative record.

## Branch-ready pull request package

This ZIP includes its own Git metadata and opens on a dedicated feature branch.
After extracting it, run `git branch --show-current` to verify the branch, then
run `./submit_pr.sh` to fetch `main`, commit the packaged changes, push the
branch, and open the pull request. See `BRANCH_AND_PR.md` for the manual commands.
