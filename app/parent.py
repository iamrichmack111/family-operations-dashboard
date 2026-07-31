from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func
from werkzeug.utils import secure_filename

from .extensions import db
from .forms import HomeworkForm, MoneyRateForm, NewUserForm, PinForm, PointAdjustmentForm, ViolationForm
from .main import role_required
from .models import Chore, Grievance, Homework, PointTransaction, ScheduleLock, Setting, User, Violation, ViolationCategory, ViolationRevision
from .services import add_points, ensure_week, log_activity, notify, point_balance, week_start_for

bp = Blueprint("parent", __name__, url_prefix="/parent")


def active_users():
    return db.session.scalars(db.select(User).where(User.active.is_(True)).order_by(User.role, User.name)).all()


def save_upload(field, prefix: str) -> str:
    if not field or not getattr(field, "data", None) or not field.data.filename:
        return ""
    filename = secure_filename(f"{prefix}-{field.data.filename}")
    field.data.save(Path(current_app.config["UPLOAD_DIR"]) / filename)
    return filename


@bp.route("/")
@login_required
@role_required("parent")
def center():
    users = active_users(); recipients = [u for u in users if not u.is_parent]
    homework_form = HomeworkForm(prefix="homework"); homework_form.assigned_to.choices = [(u.id, f"{u.emoji} {u.name}") for u in recipients]
    new_user_form = NewUserForm(prefix="new-user")
    pin_form = PinForm(prefix="pin"); pin_form.user_id.choices = [(u.id, f"{u.emoji} {u.name} — {u.role.title()}") for u in users]
    points_form = PointAdjustmentForm(prefix="points"); points_form.user_id.choices = [(u.id, f"{u.emoji} {u.name}") for u in recipients]
    rate_form = MoneyRateForm(prefix="rate"); rate_form.money_per_point.data = (db.session.get(Setting, "money_per_point") or Setting(value="0.05")).value
    balances = [{"user":u,"points":point_balance(u.id)} for u in recipients]
    week = week_start_for(date.today()); lock = db.session.scalar(db.select(ScheduleLock).where(ScheduleLock.week_start==week))
    recent_homework = db.session.scalars(db.select(Homework).order_by(Homework.created_at.desc()).limit(12)).all()
    return render_template(
        "parent.html",
        homework_form=homework_form,
        new_user_form=new_user_form,
        pin_form=pin_form,
        points_form=points_form,
        rate_form=rate_form,
        point_balances=balances,
        users=users,
        week=week,
        lock=lock,
        recent_homework=recent_homework,
    )


@bp.route("/grievances")
@login_required
@role_required("parent")
def grievances_page():
    rows = db.session.scalars(db.select(Grievance).order_by(Grievance.created_at.desc())).all()
    return render_template("parent_grievances.html", grievances=rows)


@bp.route("/violations", methods=("GET",))
@login_required
@role_required("parent")
def violations_page():
    users=active_users(); recipients=[u for u in users if not u.is_parent]
    categories=db.session.scalars(db.select(ViolationCategory).where(ViolationCategory.active.is_(True)).order_by(ViolationCategory.label)).all()
    form=ViolationForm(prefix="violation"); form.subject_user_id.choices=[(u.id,f"{u.emoji} {u.name}") for u in recipients]; form.categories.choices=[(c.id,f"{c.label} · default -{c.default_points}") for c in categories]; form.incident_date.data=date.today()
    rows=db.session.scalars(db.select(Violation).order_by(Violation.created_at.desc()).limit(100)).all()
    return render_template("parent_violations.html", form=form, violations=rows)


@bp.post("/homework")
@login_required
@role_required("parent")
def add_homework():
    form=HomeworkForm(prefix="homework"); recipients=[u for u in active_users() if not u.is_parent]; form.assigned_to.choices=[(u.id,u.name) for u in recipients]
    if form.validate_on_submit():
        item=Homework(title=form.title.data.strip(),subject=form.subject.data.strip(),assigned_to=form.assigned_to.data,due_date=form.due_date.data,points=form.points.data,details=form.details.data.strip(),recurring=form.recurring.data,attachment_name=save_upload(form.attachment,"homework"),created_by=current_user.id)
        db.session.add(item); db.session.commit(); notify(item.assigned_to,"📚","New homework assigned",item.title,url_for("main.dashboard")); log_activity(current_user.id,"created homework","homework",item.id,item.title); flash("📚 Homework assigned.","success")
    else: flash("🚫 Complete all required homework fields.","danger")
    return redirect(url_for("parent.center")+"#homework")


@bp.post("/homework/<int:item_id>/archive")
@login_required
@role_required("parent")
def archive_homework(item_id):
    item=db.session.get(Homework,item_id)
    if item: item.status="archived"; db.session.commit(); log_activity(current_user.id,"archived homework","homework",item.id,item.title)
    return redirect(url_for("parent.center")+"#homework")


@bp.post("/users/add")
@login_required
@role_required("parent")
def add_user():
    form = NewUserForm(prefix="new-user")

    if not form.validate_on_submit():
        flash(
            "🚫 Enter a unique name, role, and matching PINs.",
            "danger",
        )
        return redirect(url_for("parent.center") + "#users")

    name = form.name.data.strip()

    existing = db.session.scalar(
        db.select(User).where(func.lower(User.name) == name.lower())
    )

    if existing:
        flash("🚫 A user with that name already exists.", "danger")
        return redirect(url_for("parent.center") + "#users")

    user = User(
        name=name,
        role=form.role.data,
        active=True,
    )

    user.set_pin(
        form.pin.data,
        require_change=True,
    )

    db.session.add(user)
    db.session.commit()

    log_activity(
        current_user.id,
        "added family member",
        "account",
        user.id,
        f"{user.name} · {user.role}",
    )

    flash(
        f"✅ {user.name} was added as {user.role}.",
        "success",
    )

    return redirect(url_for("parent.center") + "#users")


@bp.post("/pin")
@login_required
@role_required("parent")
def change_pin():
    form=PinForm(prefix="pin"); users=active_users(); form.user_id.choices=[(u.id,u.name) for u in users]
    if form.validate_on_submit():
        user=db.session.get(User,form.user_id.data); user.set_pin(form.pin.data,require_change=False); user.failed_logins=0; user.locked_until=None; db.session.commit(); log_activity(current_user.id,"changed user PIN","user",user.id,user.name); flash(f"🔑 PIN updated for {user.name}.","success")
    else: flash("🚫 PINs must match and contain at least four characters.","danger")
    return redirect(url_for("parent.center")+"#users")


@bp.post("/users/<int:user_id>/toggle")
@login_required
@role_required("parent")
def toggle_user(user_id):
    user=db.session.get(User,user_id)
    if user and user.id!=current_user.id: user.active=not user.active; db.session.commit(); log_activity(current_user.id,"updated account status","user",user.id,f"active={user.active}")
    return redirect(url_for("parent.center")+"#users")


@bp.post("/schedule")
@login_required
@role_required("parent")
def schedule_control():
    action=request.form.get("action"); week=week_start_for(date.today()); reason=request.form.get("reason","").strip(); lock=db.session.scalar(db.select(ScheduleLock).where(ScheduleLock.week_start==week))
    if not lock: lock=ScheduleLock(week_start=week); db.session.add(lock)
    if action=="lock": lock.locked=True
    elif action=="unlock":
        if not reason: flash("🚫 Enter a reason to unlock the week.","danger"); return redirect(url_for("parent.center")+"#schedule")
        lock.locked=False
    elif action=="regenerate":
        if lock.locked: flash("🔒 Unlock the week before regenerating.","warning"); return redirect(url_for("parent.center")+"#schedule")
        end = week + timedelta(days=6); db.session.execute(db.delete(Chore).where(Chore.task_date>=week,Chore.task_date<=end)); db.session.commit(); ensure_week(week,force=True)
    lock.changed_by=current_user.id; lock.reason=reason; lock.changed_at=datetime.now(timezone.utc); db.session.commit(); log_activity(current_user.id,f"schedule {action}","schedule",details=reason); flash("📅 Schedule updated.","success"); return redirect(url_for("parent.center")+"#schedule")


@bp.post("/grievance/<int:grievance_id>")
@login_required
@role_required("parent")
def respond_grievance(grievance_id):
    g=db.session.get(Grievance,grievance_id); status=request.form.get("status"); response=request.form.get("response","").strip()
    if g and status in {"under_review","resolved","dismissed"} and response:
        g.status=status; g.parent_response=response; g.responded_by=current_user.id; db.session.commit(); notify(g.submitted_by,"📩",f"Grievance #{g.id} updated",status.replace('_',' ').title(),url_for("main.grievances")); log_activity(current_user.id,"responded to grievance","grievance",g.id); flash("🔒 Response saved.","success")
    else: flash("🚫 Select a status and enter a response.","danger")
    return redirect(url_for("parent.grievances_page"))


@bp.post("/violation")
@login_required
@role_required("parent")
def issue_violation():
    form=ViolationForm(prefix="violation"); recipients=[u for u in active_users() if not u.is_parent]; categories=db.session.scalars(db.select(ViolationCategory).where(ViolationCategory.active.is_(True))).all(); form.subject_user_id.choices=[(u.id,u.name) for u in recipients]; form.categories.choices=[(c.id,c.label) for c in categories]
    if form.validate_on_submit():
        selected=db.session.scalars(db.select(ViolationCategory).where(ViolationCategory.id.in_(form.categories.data))).all(); v=Violation(subject_user_id=form.subject_user_id.data,issued_by=current_user.id,incident_date=form.incident_date.data,explanation=form.explanation.data.strip(),evidence_notes=form.evidence_notes.data.strip(),attachment_name=save_upload(form.attachment,"violation"),points_deducted=form.points_deducted.data,categories=selected)
        db.session.add(v); db.session.commit(); add_points(v.subject_user_id,-v.points_deducted,f"Violation #{v.id}","violation",v.id,current_user.id); notify(v.subject_user_id,"⚠️",f"Violation notice #{v.id}","Acknowledgement confirms receipt only.",url_for("main.violations")); log_activity(current_user.id,"issued violation","violation",v.id,v.explanation[:120]); flash("⚠️ Violation issued.","success")
    else: flash("🚫 Choose a person, subject, and explanation.","danger")
    return redirect(url_for("parent.violations_page"))


@bp.post("/violation/<int:violation_id>/resolve")
@login_required
@role_required("parent")
def resolve_violation(violation_id):
    v=db.session.get(Violation,violation_id); status=request.form.get("status"); followup=request.form.get("followup","").strip(); new_points=request.form.get("points",type=int)
    if not v or status not in {"issued","acknowledged","appealed","resolved","dismissed"}: flash("🚫 Invalid update.","danger"); return redirect(url_for("parent.violations_page"))
    old_points=v.points_deducted
    if new_points is not None and new_points!=old_points:
        db.session.add(ViolationRevision(violation_id=v.id,edited_by=current_user.id,previous_explanation=v.explanation,previous_points=old_points,change_note=followup or "Point deduction updated")); add_points(v.subject_user_id,old_points-new_points,f"Violation #{v.id} point correction","violation_correction",v.id,current_user.id); v.points_deducted=new_points
    v.status=status; v.parent_followup=followup
    if status in {"resolved","dismissed"}: v.resolved_at=datetime.now(timezone.utc)
    db.session.commit(); notify(v.subject_user_id,"📝",f"Violation #{v.id} updated",status.title(),url_for("main.violations")); log_activity(current_user.id,"updated violation","violation",v.id,status); return redirect(url_for("parent.violations_page"))


@bp.post("/points")
@login_required
@role_required("parent")
def adjust_points():
    form=PointAdjustmentForm(prefix="points"); recipients=[u for u in active_users() if not u.is_parent]; form.user_id.choices=[(u.id,u.name) for u in recipients]
    if form.validate_on_submit(): tx=add_points(form.user_id.data,form.amount.data,form.reason.data.strip(),"manual",None,current_user.id); log_activity(current_user.id,"adjusted points","points",tx.id,f"{form.amount.data}: {form.reason.data}"); flash("⭐ Points updated.","success")
    return redirect(url_for("parent.center")+"#points")


@bp.post("/points/<int:transaction_id>/reverse")
@login_required
@role_required("parent")
def reverse_points(transaction_id):
    tx=db.session.get(PointTransaction,transaction_id)
    if tx and not db.session.scalar(db.select(PointTransaction.id).where(PointTransaction.reversal_of_id==tx.id)):
        reversal=add_points(tx.user_id,-tx.amount,f"Reversal: {tx.reason}","reversal",tx.id,current_user.id,reversal_of_id=tx.id); log_activity(current_user.id,"reversed points","points",reversal.id,tx.reason)
    return redirect(url_for("main.reports"))


@bp.post("/money-rate")
@login_required
@role_required("parent")
def money_rate_update():
    form=MoneyRateForm(prefix="rate")
    try: value=float(form.money_per_point.data)
    except (TypeError,ValueError): value=-1
    if form.validate_on_submit() and value>=0:
        setting=db.session.get(Setting,"money_per_point") or Setting(key="money_per_point",value="0.05"); setting.value=str(value); setting.updated_by=current_user.id; db.session.add(setting); db.session.commit(); log_activity(current_user.id,"updated monetary rate","setting",details=str(value)); flash("💵 Monetary value updated.","success")
    return redirect(url_for("parent.center")+"#points")
