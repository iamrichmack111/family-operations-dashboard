from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash

PEOPLE = ("Zara", "Jasmin", "Aria")
DEFAULT_USERS = (
    ("Samantha", "parent"),
    ("Jeremy", "parent"),
    ("Jasmin", "manager"),
    ("Zara", "child"),
    ("Aria", "child"),
)
VIOLATION_CATEGORIES = (
    ("insubordination", "Insubordination", 15),
    ("poor_job_performance", "Poor job performance", 5),
    ("unauthorized_usage", "Unauthorized usage", 10),
    ("theft", "Theft", 30),
    ("vandalism", "Vandalism", 25),
    ("assault", "Assault", 40),
    ("other", "Other", 0),
)

SCHEMA = r"""
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  role TEXT NOT NULL CHECK(role IN ('parent','manager','child')),
  password_hash TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_date TEXT NOT NULL,
  title TEXT NOT NULL,
  assigned_to INTEGER NOT NULL REFERENCES users(id),
  points INTEGER NOT NULL DEFAULT 5,
  status TEXT NOT NULL DEFAULT 'assigned' CHECK(status IN ('assigned','completed','approved','needs_redo','excused')),
  completed_by INTEGER REFERENCES users(id),
  approved_by INTEGER REFERENCES users(id),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(task_date, title)
);

CREATE TABLE IF NOT EXISTS homework (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  subject TEXT NOT NULL,
  assigned_to INTEGER NOT NULL REFERENCES users(id),
  due_date TEXT NOT NULL,
  points INTEGER NOT NULL DEFAULT 5,
  status TEXT NOT NULL DEFAULT 'assigned' CHECK(status IN ('assigned','completed','approved','needs_redo','excused')),
  details TEXT NOT NULL DEFAULT '',
  completed_by INTEGER REFERENCES users(id),
  approved_by INTEGER REFERENCES users(id),
  created_by INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sender_id INTEGER NOT NULL REFERENCES users(id),
  recipient_id INTEGER NOT NULL REFERENCES users(id),
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  read_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grievances (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  submitted_by INTEGER NOT NULL REFERENCES users(id),
  subject TEXT NOT NULL,
  description TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','under_review','resolved','dismissed')),
  parent_response TEXT NOT NULL DEFAULT '',
  responded_by INTEGER REFERENCES users(id),
  acknowledged_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS violations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_user_id INTEGER NOT NULL REFERENCES users(id),
  issued_by INTEGER NOT NULL REFERENCES users(id),
  incident_date TEXT NOT NULL,
  explanation TEXT NOT NULL,
  evidence_notes TEXT NOT NULL DEFAULT '',
  points_deducted INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'issued' CHECK(status IN ('issued','acknowledged','amended','reversed')),
  recipient_response TEXT NOT NULL DEFAULT '',
  acknowledged_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS violation_categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  default_points INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS violation_items (
  violation_id INTEGER NOT NULL REFERENCES violations(id) ON DELETE CASCADE,
  category_id INTEGER NOT NULL REFERENCES violation_categories(id),
  PRIMARY KEY(violation_id, category_id)
);

CREATE TABLE IF NOT EXISTS violation_revisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  violation_id INTEGER NOT NULL REFERENCES violations(id),
  edited_by INTEGER NOT NULL REFERENCES users(id),
  previous_explanation TEXT NOT NULL,
  previous_points INTEGER NOT NULL,
  change_note TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS point_transactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  amount INTEGER NOT NULL,
  reason TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_id INTEGER,
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_by INTEGER REFERENCES users(id),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  actor_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id INTEGER,
  details TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chores_date ON chores(task_date);
CREATE INDEX IF NOT EXISTS idx_homework_due ON homework(due_date);
CREATE INDEX IF NOT EXISTS idx_points_user ON point_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_violations_user ON violations(subject_user_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity(created_at);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 5000")
    return g.db


def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    get_db().executescript(SCHEMA)


def seed_defaults() -> None:
    db = get_db()
    for name, role in DEFAULT_USERS:
        db.execute(
            """INSERT OR IGNORE INTO users(name, role, password_hash)
               VALUES (?, ?, ?)""",
            (name, role, generate_password_hash("1234")),
        )
    for code, label, points in VIOLATION_CATEGORIES:
        db.execute(
            """INSERT OR IGNORE INTO violation_categories(code, label, default_points)
               VALUES (?, ?, ?)""",
            (code, label, points),
        )
    db.execute(
        "INSERT OR IGNORE INTO settings(key, value) VALUES ('money_per_point', '0.05')"
    )
    db.execute(
        "INSERT OR IGNORE INTO settings(key, value) VALUES ('allow_negative_points', '0')"
    )
    db.commit()
    ensure_week(date.today())


def user_id(name: str) -> int:
    row = get_db().execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone()
    if not row:
        raise ValueError(f"Unknown user: {name}")
    return int(row["id"])


def ensure_week(start: date) -> None:
    db = get_db()
    for offset in range(7):
        day = start + timedelta(days=offset)
        anchor = date(2026, 7, 27)
        rotation_index = (day - anchor).days % 3
        cook = PEOPLE[rotation_index]
        others = [person for person in PEOPLE if person != cook]
        if (day - anchor).days % 2:
            others.reverse()
        assignments = [
            ("Cook and dishes", cook, 4),
            ("Counters and stove", others[0], 1),
            ("Table, chairs, and floor", others[1], 1),
            ("Bathrooms", others[(day.toordinal() + 0) % 2], 3),
            ("Kitchen deep clean", others[(day.toordinal() + 1) % 2], 3),
            ("Basement", others[(day.toordinal() + 0) % 2], 3),
            ("Laundry", others[(day.toordinal() + 1) % 2], 2),
        ]
        for title, person, points in assignments:
            db.execute(
                """INSERT OR IGNORE INTO chores(task_date, title, assigned_to, points)
                   VALUES (?, ?, ?, ?)""",
                (day.isoformat(), title, user_id(person), points),
            )
    db.commit()


def log_activity(actor_id: int | None, action: str, entity_type: str, entity_id: int | None = None, details: str = "") -> None:
    db = get_db()
    db.execute(
        "INSERT INTO activity(actor_id, action, entity_type, entity_id, details) VALUES (?, ?, ?, ?, ?)",
        (actor_id, action, entity_type, entity_id, details),
    )
    db.commit()


def add_points(user: int, amount: int, reason: str, source_type: str, source_id: int | None, created_by: int | None) -> None:
    db = get_db()
    db.execute(
        """INSERT INTO point_transactions(user_id, amount, reason, source_type, source_id, created_by)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user, amount, reason, source_type, source_id, created_by),
    )
    db.commit()
