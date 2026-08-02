from __future__ import annotations

from datetime import datetime, timedelta, timezone

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import csrf, db, login_manager
from .forms import LoginForm
from .models import LoginEvent, User
from .services import log_activity

bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


@bp.route("/login", methods=("GET", "POST"))
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    users = db.session.scalars(db.select(User).where(User.active.is_(True)).order_by(User.role, User.name)).all()
    form = LoginForm()
    form.user_id.choices = [(u.id, f"{u.emoji} {u.name} — {u.role.title()}") for u in users]
    if form.validate_on_submit():
        user = db.session.get(User, form.user_id.data)
        now = datetime.now(timezone.utc)
        locked = bool(user and user.locked_until and user.locked_until > now)
        success = bool(user and not locked and user.active and user.check_pin(form.password.data))
        db.session.add(LoginEvent(user_id=user.id if user else None, user_name=user.name if user else "Unknown", success=success, ip_address=request.remote_addr or "", user_agent=(request.user_agent.string or "")[:255]))
        if success:
            user.failed_logins = 0; user.locked_until = None; user.last_login_at = now
            db.session.commit(); login_user(user, remember=form.remember.data); session.permanent = True
            log_activity(user.id, "signed in", "session")
            flash(f"👋 Welcome back, {user.name}!", "success")
            if user.must_change_pin:
                flash("🔑 Your PIN is temporary. Ask a parent to change it from Parent Center.", "warning")
            return redirect(url_for("main.dashboard"))
        if user:
            user.failed_logins += 1
            if user.failed_logins >= 5:
                user.locked_until = now + timedelta(minutes=15); user.failed_logins = 0
        db.session.commit()
        flash("🚫 Incorrect PIN or temporarily locked account.", "danger")
    return render_template("login.html", form=form)


@bp.post("/logout")
@csrf.exempt
@login_required
def logout():
    log_activity(current_user.id, "signed out", "session")
    logout_user()
    return redirect(url_for("auth.login"))
