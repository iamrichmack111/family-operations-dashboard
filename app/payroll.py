"""Parent-funded manager payroll. Funds are separate from a manager's own balance."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import update
from .extensions import db
from .models import PayrollGrant, PayrollPayout, PointTransaction, User
from .services import money_rate, notify

bp = Blueprint("payroll", __name__, url_prefix="/payroll")


def _redirect():
    return redirect(url_for("payroll.index"))


def _positive_amount(value):
    try:
        value = int(value)
        if 1 <= value <= 1000000:
            return value
    except (TypeError, ValueError):
        pass
    return None


@bp.get("/")
@login_required
def index():
    if current_user.role not in {"parent", "manager"}:
        return _redirect_denied()
    managers = db.session.scalars(db.select(User).where(User.role == "manager", User.active.is_(True)).order_by(User.name)).all()
    recipients = db.session.scalars(db.select(User).where(User.role.in_(["child", "manager"]), User.active.is_(True), User.id != current_user.id).order_by(User.name)).all()
    stmt = db.select(PayrollGrant)
    if current_user.role == "manager":
        stmt = stmt.where(PayrollGrant.manager_id == current_user.id)
    grants = db.session.scalars(stmt.order_by(PayrollGrant.created_at.desc())).all()
    payouts = db.session.scalars(db.select(PayrollPayout).order_by(PayrollPayout.created_at.desc()).limit(50)).all()
    names = {u.id: u.name for u in db.session.scalars(db.select(User)).all()}
    return render_template("payroll.html", managers=managers, recipients=recipients, grants=grants, payouts=payouts, names=names)


def _redirect_denied():
    flash("Only parents and managers can access payroll.", "danger")
    return redirect(url_for("main.dashboard"))


@bp.post("/fund")
@login_required
def fund():
    if current_user.role != "parent":
        return _redirect_denied()
    amount = _positive_amount(request.form.get("amount"))
    note = (request.form.get("note") or "Household work payroll").strip()[:255]
    manager = db.session.get(User, request.form.get("manager_id", type=int))
    if amount is None or manager is None or not manager.active or manager.role != "manager":
        flash("Choose an active manager and a positive amount up to 1,000,000.", "danger")
        return _redirect()
    grant = PayrollGrant(manager_id=manager.id, parent_id=current_user.id, amount=amount, remaining=amount, note=note)
    db.session.add(grant)
    db.session.commit()
    notify(manager.id, "💼", "Payroll funded", f"A parent allocated {amount:,} points for work payouts.", link=url_for("payroll.index"))
    flash(f"Funded {manager.name}'s payroll with {amount:,} points.", "success")
    return _redirect()


@bp.post("/pay")
@login_required
def pay():
    if current_user.role != "manager":
        return _redirect_denied()
    amount = _positive_amount(request.form.get("amount"))
    recipient = db.session.get(User, request.form.get("recipient_id", type=int))
    reason = (request.form.get("reason") or "").strip()[:255]
    if amount is None or not reason or recipient is None or not recipient.active or recipient.role == "parent" or recipient.id == current_user.id:
        flash("Select another active non-parent member, a positive amount, and a work reason.", "danger")
        return _redirect()
    # Spend oldest grants first, with conditional updates to prevent overspending
    # even when two payment requests are submitted together.
    grants = db.session.scalars(db.select(PayrollGrant).where(PayrollGrant.manager_id == current_user.id, PayrollGrant.remaining > 0).order_by(PayrollGrant.created_at, PayrollGrant.id)).all()
    if sum(g.remaining for g in grants) < amount:
        flash("Insufficient payroll funds. Ask a parent to fund the budget.", "danger")
        return _redirect()
    balance = amount
    for grant in grants:
        if balance <= 0:
            break
        take = min(grant.remaining, balance)
        result = db.session.execute(update(PayrollGrant).where(PayrollGrant.id == grant.id, PayrollGrant.remaining >= take).values(remaining=PayrollGrant.remaining-take))
        if result.rowcount != 1:
            db.session.rollback()
            flash("Payroll changed during payment. Try again.", "warning")
            return _redirect()
        db.session.add(PayrollPayout(grant_id=grant.id, manager_id=current_user.id, recipient_id=recipient.id, points=take, reason=reason))
        balance -= take
    if balance:
        db.session.rollback()
        flash("Insufficient payroll funds. Retry.", "danger")
        return _redirect()
    db.session.add(PointTransaction(user_id=recipient.id, amount=amount, reason=f"Manager payroll: {reason}"[:255], source_type="manager_payroll", created_by=current_user.id, money_rate=money_rate()))
    db.session.commit()
    notify(recipient.id, "⭐", "Payroll points awarded", f"{current_user.name} awarded {amount:,} points for: {reason}", link=url_for("main.points_ledger"))
    flash(f"Awarded {amount:,} points to {recipient.name}. Remaining payroll funds updated.", "success")
    return _redirect()
