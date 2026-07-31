from __future__ import annotations

import shutil
from datetime import date, timedelta
from pathlib import Path

from flask import current_app, url_for
from sqlalchemy import func

from .extensions import db
from .models import Activity, Chore, Notification, PointTransaction, ScheduleLock, Setting, User, ViolationCategory

PEOPLE = ("Zara", "Jasmin", "Aria")
DEFAULT_USERS = (("Samantha", "parent"), ("Jeremy", "parent"), ("Jasmin", "manager"), ("Zara", "child"), ("Aria", "child"))
VIOLATION_CATEGORIES = (
    ("insubordination", "Insubordination", 15),
    ("poor_job_performance", "Poor job performance", 5),
    ("unauthorized_usage", "Unauthorized usage", 10),
    ("theft", "Theft", 30),
    ("vandalism", "Vandalism", 25),
    ("assault", "Assault", 40),
    ("other", "Other", 0),
)


def seed_defaults() -> None:
    for name, role in DEFAULT_USERS:
        user = db.session.scalar(db.select(User).where(User.name == name))
        if user is None:
            user = User(name=name, role=role, active=True)
            user.set_pin("1234", require_change=True)
            db.session.add(user)
    for code, label, points in VIOLATION_CATEGORIES:
        category = db.session.scalar(db.select(ViolationCategory).where(ViolationCategory.code == code))
        if category is None:
            db.session.add(ViolationCategory(code=code, label=label, default_points=points, active=True))
    defaults = {"money_per_point": "0.05", "allow_negative_points": "0", "session_minutes": "60", "kid_direct_messages": "0"}
    for key, value in defaults.items():
        if db.session.get(Setting, key) is None:
            db.session.add(Setting(key=key, value=value))
    db.session.commit()
    ensure_week(date.today())


def week_start_for(day: date) -> date:
    return day - timedelta(days=day.weekday())


def is_week_locked(day: date) -> bool:
    lock = db.session.scalar(db.select(ScheduleLock).where(ScheduleLock.week_start == week_start_for(day)))
    return bool(lock and lock.locked)


def ensure_week(start: date, *, force: bool = False) -> None:
    if is_week_locked(start) and not force:
        return
    anchor = date(2026, 7, 27)
    users = {u.name: u.id for u in db.session.scalars(db.select(User).where(User.name.in_(PEOPLE))).all()}
    weights = {"🍳 Cook and dishes": 4, "🧽 Counters and stove": 1, "🪑 Table, chairs, and floor": 1, "🛁 Bathrooms": 3, "🧹 Kitchen deep clean": 3, "📦 Basement": 3, "🧺 Laundry": 2}
    for offset in range(7):
        day = start + timedelta(days=offset)
        idx = (day - anchor).days % len(PEOPLE)
        cook = PEOPLE[idx]
        others = [p for p in PEOPLE if p != cook]
        if (day - anchor).days % 2:
            others.reverse()
        assignments = [
            ("🍳 Cook and dishes", cook), ("🧽 Counters and stove", others[0]), ("🪑 Table, chairs, and floor", others[1]),
            ("🛁 Bathrooms", others[day.toordinal() % 2]), ("🧹 Kitchen deep clean", others[(day.toordinal() + 1) % 2]),
            ("📦 Basement", others[day.toordinal() % 2]), ("🧺 Laundry", others[(day.toordinal() + 1) % 2]),
        ]
        for title, person in assignments:
            exists = db.session.scalar(db.select(Chore.id).where(Chore.task_date == day, Chore.title == title))
            if not exists:
                db.session.add(Chore(task_date=day, title=title, assigned_to=users[person], points=weights[title], weight=weights[title]))
    db.session.commit()


def log_activity(actor_id: int | None, action: str, entity_type: str, entity_id: int | None = None, details: str = "") -> None:
    db.session.add(Activity(actor_id=actor_id, action=action, entity_type=entity_type, entity_id=entity_id, details=details))
    db.session.commit()


def money_rate() -> float:
    setting = db.session.get(Setting, "money_per_point")
    return float(setting.value if setting else 0.0)


def add_points(user_id: int, amount: int, reason: str, source_type: str, source_id: int | None, created_by: int | None, reversal_of_id: int | None = None) -> PointTransaction:
    transaction = PointTransaction(user_id=user_id, amount=amount, reason=reason, source_type=source_type, source_id=source_id, created_by=created_by, reversal_of_id=reversal_of_id, money_rate=money_rate())
    db.session.add(transaction)
    db.session.commit()
    return transaction


def point_balance(user_id: int) -> int:
    return int(db.session.scalar(db.select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(PointTransaction.user_id == user_id)) or 0)


def notify(user_id: int, icon: str, title: str, body: str = "", link: str = "") -> None:
    db.session.add(Notification(user_id=user_id, icon=icon, title=title, body=body, link=link))
    db.session.commit()


def notify_roles(roles: set[str], icon: str, title: str, body: str = "", link: str = "") -> None:
    users = db.session.scalars(db.select(User).where(User.role.in_(roles), User.active.is_(True))).all()
    for user in users:
        db.session.add(Notification(user_id=user.id, icon=icon, title=title, body=body, link=link))
    db.session.commit()


def backup_database() -> Path | None:
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not uri.startswith("sqlite:///"):
        return None
    db_path = Path(uri.removeprefix("sqlite:///"))
    if not db_path.exists():
        return None
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"family-dashboard-{date.today().isoformat()}.db"
    shutil.copy2(db_path, target)
    backups = sorted(backup_dir.glob("family-dashboard-*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in backups[14:]:
        old.unlink(missing_ok=True)
    return target


# Activity visibility rules. The shared family feed intentionally excludes
# confidential, disciplinary, financial-administration, authentication, and
# account-management events. Parents retain access to the complete audit log.
PRIVATE_ACTIVITY_ENTITIES = {
    "grievance", "violation", "session", "login", "authentication",
    "account", "setting", "export", "backup",
}
PRIVATE_ACTIVITY_PHRASES = (
    "pin", "password", "login", "signed in", "signed out", "locked account",
    "grievance", "violation", "money rate", "monetary", "cash value",
    "created export", "database backup", "parent note", "role changed",
)

def activity_is_family_safe(activity: Activity) -> bool:
    """Return True when an audit event is suitable for the shared family feed."""
    entity = (activity.entity_type or "").strip().lower()
    action = (activity.action or "").strip().lower()
    details = (activity.details or "").strip().lower()
    if entity in PRIVATE_ACTIVITY_ENTITIES:
        return False
    combined = f"{action} {details}"
    return not any(phrase in combined for phrase in PRIVATE_ACTIVITY_PHRASES)

def family_safe_activity(limit: int = 100) -> list[Activity]:
    """Fetch recent shared activity, filtering sensitive events in Python."""
    candidates = db.session.scalars(
        db.select(Activity).order_by(Activity.created_at.desc()).limit(max(limit * 4, 200))
    ).all()
    return [row for row in candidates if activity_is_family_safe(row)][:limit]
