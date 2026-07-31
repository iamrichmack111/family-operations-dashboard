from __future__ import annotations

from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_pin = db.Column(db.Boolean, default=True, nullable=False)
    failed_logins = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime(timezone=True))
    last_login_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_pin(self, pin: str, *, require_change: bool = False) -> None:
        self.password_hash = generate_password_hash(pin)
        self.must_change_pin = require_change

    def check_pin(self, pin: str) -> bool:
        return check_password_hash(self.password_hash, pin)

    @property
    def is_parent(self) -> bool:
        return self.role == "parent"

    @property
    def can_approve(self) -> bool:
        return self.role in {"parent", "manager"}

    @property
    def emoji(self) -> str:
        return {"parent": "👑", "manager": "🗝️", "child": "🌟"}.get(self.role, "👤")


class LoginEvent(db.Model):
    __tablename__ = "login_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user_name = db.Column(db.String(80), nullable=False)
    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(80), default="", nullable=False)
    user_agent = db.Column(db.String(255), default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class Chore(TimestampMixin, db.Model):
    __tablename__ = "chores"
    __table_args__ = (db.UniqueConstraint("task_date", "title", name="uq_chore_day_title"),)
    id = db.Column(db.Integer, primary_key=True)
    task_date = db.Column(db.Date, nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    points = db.Column(db.Integer, default=5, nullable=False)
    weight = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(30), default="assigned", nullable=False, index=True)
    completed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    note = db.Column(db.Text, default="", nullable=False)
    reassignment_reason = db.Column(db.Text, default="", nullable=False)
    carried_from_id = db.Column(db.Integer, db.ForeignKey("chores.id"))
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    approver = db.relationship("User", foreign_keys=[approved_by])


class Homework(TimestampMixin, db.Model):
    __tablename__ = "homework"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    due_date = db.Column(db.Date, nullable=False, index=True)
    points = db.Column(db.Integer, default=5, nullable=False)
    status = db.Column(db.String(30), default="assigned", nullable=False, index=True)
    details = db.Column(db.Text, default="", nullable=False)
    recurring = db.Column(db.String(20), default="none", nullable=False)
    attachment_name = db.Column(db.String(255), default="", nullable=False)
    completed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    approver = db.relationship("User", foreign_keys=[approved_by])
    creator = db.relationship("User", foreign_keys=[created_by])


class Message(TimestampMixin, db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, nullable=False)
    thread_id = db.Column(db.Integer, index=True)
    read_at = db.Column(db.DateTime(timezone=True))
    sender = db.relationship("User", foreign_keys=[sender_id])
    recipient = db.relationship("User", foreign_keys=[recipient_id])


class Grievance(TimestampMixin, db.Model):
    __tablename__ = "grievances"
    id = db.Column(db.Integer, primary_key=True)
    submitted_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    subject = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), default="open", nullable=False, index=True)
    parent_response = db.Column(db.Text, default="", nullable=False)
    responded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    submitter = db.relationship("User", foreign_keys=[submitted_by])
    responder = db.relationship("User", foreign_keys=[responded_by])


violation_items = db.Table(
    "violation_items",
    db.Column("violation_id", db.Integer, db.ForeignKey("violations.id", ondelete="CASCADE"), primary_key=True),
    db.Column("category_id", db.Integer, db.ForeignKey("violation_categories.id"), primary_key=True),
)


class ViolationCategory(db.Model):
    __tablename__ = "violation_categories"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(80), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)
    default_points = db.Column(db.Integer, default=0, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)


class Violation(TimestampMixin, db.Model):
    __tablename__ = "violations"
    id = db.Column(db.Integer, primary_key=True)
    subject_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    issued_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    incident_date = db.Column(db.Date, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    evidence_notes = db.Column(db.Text, default="", nullable=False)
    attachment_name = db.Column(db.String(255), default="", nullable=False)
    points_deducted = db.Column(db.Integer, default=0, nullable=False)
    status = db.Column(db.String(30), default="issued", nullable=False, index=True)
    recipient_response = db.Column(db.Text, default="", nullable=False)
    parent_followup = db.Column(db.Text, default="", nullable=False)
    acknowledged_at = db.Column(db.DateTime(timezone=True))
    appealed_at = db.Column(db.DateTime(timezone=True))
    resolved_at = db.Column(db.DateTime(timezone=True))
    subject_user = db.relationship("User", foreign_keys=[subject_user_id])
    issuer = db.relationship("User", foreign_keys=[issued_by])
    categories = db.relationship("ViolationCategory", secondary=violation_items, lazy="selectin")


class ViolationRevision(db.Model):
    __tablename__ = "violation_revisions"
    id = db.Column(db.Integer, primary_key=True)
    violation_id = db.Column(db.Integer, db.ForeignKey("violations.id"), nullable=False)
    edited_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    previous_explanation = db.Column(db.Text, nullable=False)
    previous_points = db.Column(db.Integer, nullable=False)
    change_note = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class PointTransaction(db.Model):
    __tablename__ = "point_transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    amount = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(60), nullable=False)
    source_id = db.Column(db.Integer)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reversal_of_id = db.Column(db.Integer, db.ForeignKey("point_transactions.id"))
    money_rate = db.Column(db.Float, default=0.0, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user = db.relationship("User", foreign_keys=[user_id])
    creator = db.relationship("User", foreign_keys=[created_by])


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    icon = db.Column(db.String(20), default="🔔", nullable=False)
    title = db.Column(db.String(180), nullable=False)
    body = db.Column(db.Text, default="", nullable=False)
    link = db.Column(db.String(255), default="", nullable=False)
    read_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    user = db.relationship("User")


class ScheduleLock(db.Model):
    __tablename__ = "schedule_locks"
    id = db.Column(db.Integer, primary_key=True)
    week_start = db.Column(db.Date, unique=True, nullable=False, index=True)
    locked = db.Column(db.Boolean, default=False, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    reason = db.Column(db.Text, default="", nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.String(255), nullable=False)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Activity(db.Model):
    __tablename__ = "activity"
    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    action = db.Column(db.String(160), nullable=False)
    entity_type = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text, default="", nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    actor = db.relationship("User")
