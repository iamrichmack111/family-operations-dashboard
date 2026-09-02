from __future__ import annotations

import csv
import json
import shutil
import zipfile
from datetime import date, datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename

from .chore_rotation import (
    ROTATION_LENGTH,
    SPECIAL_ROTATION_CHORES,
    chore_assignments_for,
    rotation_cycle_start,
    rotation_day_number,
)
from .extensions import db
from .forms import FamilyPostForm, GrievanceForm, MessageForm
from .models import Activity, Chore, Grievance, Homework, LoginEvent, Message, Notification, PointTransaction, ScheduleLock, Setting, User, Violation, ViolationCategory, ViolationRevision
from .proof_images import ProofImageError, chore_proof_exists, chore_proof_path, delete_chore_proof, save_chore_proof
from .services import add_points, backup_database, ensure_week, log_activity, money_rate, notify, notify_roles, point_balance, week_start_for, family_safe_activity, activity_is_family_safe

bp = Blueprint("main", __name__)


@bp.post("/activity/family-post")
@login_required
def create_family_post():
    form = FamilyPostForm(prefix="family-post")

    if not form.validate_on_submit():
        flash(
            "🚫 Enter a family update before posting.",
            "danger",
        )
        return redirect(
            url_for("main.activity", view="household")
        )

    message = form.message.data.strip()

    log_activity(
        current_user.id,
        "posted a family update",
        "family_post",
        details=message,
    )

    flash("📣 Family update posted.", "success")

    return redirect(
        url_for("main.activity", view="household")
    )



def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                flash("🚫 You do not have permission for that action.", "danger")
                return redirect(url_for("main.dashboard"))
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def wants_htmx() -> bool:
    return request.headers.get("HX-Request") == "true"


def task_model(kind: str):
    return Chore if kind == "chore" else Homework if kind == "homework" else None


@bp.app_context_processor
def inject_notifications():
    if not current_user.is_authenticated:
        return {"nav_unread": 0}
    unread = int(db.session.scalar(db.select(func.count(Notification.id)).where(Notification.user_id == current_user.id, Notification.read_at.is_(None))) or 0)
    return {"nav_unread": unread}


@bp.route("/")
@login_required
def dashboard():
    ensure_week(date.today())
    today = date.today(); tomorrow = today + timedelta(days=1); week_start = today - timedelta(days=6)
    chore_query = db.select(Chore).where(Chore.task_date == today).order_by(Chore.id)
    tomorrow_query = db.select(Chore).where(Chore.task_date == tomorrow).order_by(Chore.id)
    homework_query = db.select(Homework).where(Homework.status.notin_(["approved", "excused", "archived"]), Homework.due_date <= today + timedelta(days=7)).order_by(Homework.due_date)
    if current_user.role == "child":
        chore_query = chore_query.where(Chore.assigned_to == current_user.id); homework_query = homework_query.where(Homework.assigned_to == current_user.id)
    if current_user.role in {"child", "manager"}:
        tomorrow_query = tomorrow_query.where(Chore.assigned_to == current_user.id)
    chores = db.session.scalars(chore_query).all(); tomorrow_chores = db.session.scalars(tomorrow_query).all(); homework = db.session.scalars(homework_query).all()

    cycle_start = rotation_cycle_start(today)
    special_rotation = []
    for offset in range(ROTATION_LENGTH):
        cycle_day = cycle_start + timedelta(days=offset)
        assigned_to = {
            title: person
            for title, person, _points in chore_assignments_for(
                cycle_day,
                include_emoji=False,
            )
        }
        special_rotation.append(
            {
                "date": cycle_day,
                "day_number": offset + 1,
                "is_today": cycle_day == today,
                "bathrooms": assigned_to[SPECIAL_ROTATION_CHORES[0]],
                "basement": assigned_to[SPECIAL_ROTATION_CHORES[1]],
            }
        )
    members = db.session.scalars(db.select(User).where(User.role.in_(["manager", "child"]), User.active.is_(True)).order_by(User.name)).all()
    points=[]; completion=[]; earned_vs_deducted=[]; workload=[]
    for member in members:
        balance = point_balance(member.id)
        earned = int(db.session.scalar(db.select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(PointTransaction.user_id == member.id, PointTransaction.amount > 0)) or 0)
        deducted = abs(int(db.session.scalar(db.select(func.coalesce(func.sum(PointTransaction.amount), 0)).where(PointTransaction.user_id == member.id, PointTransaction.amount < 0)) or 0))
        total = int(db.session.scalar(db.select(func.count(Chore.id)).where(Chore.assigned_to == member.id, Chore.task_date >= week_start)) or 0)
        complete = int(db.session.scalar(db.select(func.count(Chore.id)).where(Chore.assigned_to == member.id, Chore.task_date >= week_start, Chore.status.in_(["completed", "approved"]))) or 0)
        load = int(db.session.scalar(db.select(func.coalesce(func.sum(Chore.weight), 0)).where(Chore.assigned_to == member.id, Chore.task_date >= week_start)) or 0)
        points.append({"name":member.name,"emoji":member.emoji,"points":balance,"money":round(balance*money_rate(),2)})
        completion.append({"name":member.name,"percent":round(complete/total*100) if total else 0})
        earned_vs_deducted.append({"name":member.name,"earned":earned,"deducted":deducted})
        workload.append({"name":member.name,"weight":load})

    # Extra family pulse charts use real persisted records and fixed date
    # windows, so the dashboard remains useful even on days with no activity.
    status_start = today - timedelta(days=29)
    status_rows = db.session.execute(
        db.select(Chore.status, func.count(Chore.id))
        .where(Chore.task_date >= status_start)
        .group_by(Chore.status)
    ).all()
    status_counts = {status: int(count) for status, count in status_rows}
    status_labels = {
        "approved": "Approved",
        "assigned": "Assigned",
        "completed": "Waiting approval",
        "needs_redo": "Needs redo",
        "excused": "Excused",
    }
    chore_status = [
        {"label": status_labels[status], "value": status_counts.get(status, 0)}
        for status in ("approved", "assigned", "completed", "needs_redo", "excused")
        if status_counts.get(status, 0)
    ]

    review_start = today - timedelta(days=6)
    review_rows = db.session.execute(
        db.select(Chore.task_date, Chore.status, func.count(Chore.id))
        .where(Chore.task_date >= review_start, Chore.task_date <= today)
        .group_by(Chore.task_date, Chore.status)
    ).all()
    review_counts = {
        (task_date, status): int(count)
        for task_date, status, count in review_rows
    }
    review_week = []
    for offset in range(7):
        day = review_start + timedelta(days=offset)
        review_week.append(
            {
                "label": day.strftime("%a"),
                "date": day.strftime("%b %d"),
                "approved": review_counts.get((day, "approved"), 0),
                "redo": review_counts.get((day, "needs_redo"), 0),
                "open": review_counts.get((day, "assigned"), 0)
                + review_counts.get((day, "completed"), 0),
            }
        )

    movement_start = today - timedelta(days=13)
    movement_day = func.date(PointTransaction.created_at)
    movement_rows = db.session.execute(
        db.select(movement_day, func.coalesce(func.sum(PointTransaction.amount), 0))
        .where(
            PointTransaction.created_at
            >= datetime.combine(movement_start, datetime.min.time(), tzinfo=timezone.utc)
        )
        .group_by(movement_day)
    ).all()
    movement_counts = {str(day): int(amount or 0) for day, amount in movement_rows}
    point_movement = [
        {
            "label": (movement_start + timedelta(days=offset)).strftime("%b %d"),
            "net": movement_counts.get(
                (movement_start + timedelta(days=offset)).isoformat(), 0
            ),
        }
        for offset in range(14)
    ]

    pending = int(db.session.scalar(db.select(func.count()).select_from(Chore).where(Chore.status=="completed")) or 0)+int(db.session.scalar(db.select(func.count()).select_from(Homework).where(Homework.status=="completed")) or 0)
    unread_messages=int(db.session.scalar(db.select(func.count(Message.id)).where(Message.recipient_id==current_user.id,Message.read_at.is_(None))) or 0)
    unacked=int(db.session.scalar(db.select(func.count(Violation.id)).where(Violation.subject_user_id==current_user.id,Violation.status=="issued")) or 0)
    open_grievances=int(db.session.scalar(db.select(func.count(Grievance.id)).where(Grievance.status.in_(["open","under_review"]))) or 0) if current_user.is_parent else 0
    notifications=db.session.scalars(db.select(Notification).where(Notification.user_id==current_user.id).order_by(Notification.created_at.desc()).limit(8)).all()
    activity=family_safe_activity(10)
    return render_template(
        "dashboard.html",
        chores=chores,
        tomorrow_chores=tomorrow_chores,
        tomorrow_date=tomorrow,
        tomorrow_is_personal=current_user.role in {"child", "manager"},
        rotation_day=rotation_day_number(today),
        rotation_length=ROTATION_LENGTH,
        special_rotation=special_rotation,
        homework=homework,
        points=points,
        completion=completion,
        earned_vs_deducted=earned_vs_deducted,
        workload=workload,
        chore_status=chore_status,
        review_week=review_week,
        point_movement=point_movement,
        money_rate=money_rate(),
        pending_approvals=pending,
        unacked=unacked,
        open_grievances=open_grievances,
        unread_messages=unread_messages,
        notifications=notifications,
        activity=activity,
    )


@bp.post("/tasks/<kind>/<int:item_id>/complete")
@login_required
def complete_task(kind,item_id):
    model=task_model(kind); item=db.session.get(model,item_id) if model else None
    if not item or item.status not in {"assigned", "needs_redo"} or (current_user.role=="child" and item.assigned_to!=current_user.id):
        flash("🚫 You cannot complete that item.","danger"); return redirect(url_for("main.dashboard"))
    if kind == "chore" and item.task_date > date.today():
        flash("🧭 This is a preview. The chore can be completed on its assignment date.", "warning")
        return redirect(request.referrer or url_for("main.dashboard"))

    old_proof_name = item.proof_photo_name if kind == "chore" else ""
    new_proof_name = ""
    if kind == "chore":
        try:
            new_proof_name = save_chore_proof(request.files.get("proof_photo"), item.id)
        except ProofImageError as exc:
            if wants_htmx():
                return render_template("partials/task_card.html", item=item, kind=kind, proof_error=str(exc))
            flash(f"📷 {exc}", "danger")
            return redirect(request.referrer or url_for("main.dashboard"))

    item.status="completed"
    item.completed_by=current_user.id
    if kind == "chore":
        item.note=request.form.get("note","").strip()
        item.proof_photo_name = new_proof_name
    try:
        db.session.commit()
    except Exception:
        if new_proof_name:
            delete_chore_proof(new_proof_name)
        raise
    if old_proof_name and old_proof_name != new_proof_name:
        delete_chore_proof(old_proof_name)
    notify_roles({"parent","manager"},"✅",f"{item.assignee.name} completed {kind}",item.title,url_for("main.approvals"))
    log_activity(current_user.id,"marked complete",kind,item.id,item.title)
    if wants_htmx(): return render_template("partials/task_card.html",item=item,kind=kind)
    flash("✅ Marked complete and sent for approval.","success"); return redirect(request.referrer or url_for("main.dashboard"))


@bp.post("/tasks/<kind>/<int:item_id>/review")
@login_required
@role_required("parent","manager")
def review_task(kind,item_id):
    model = task_model(kind)
    item = db.session.get(model, item_id) if model else None
    status = request.form.get("status")

    if not item or item.status != "completed" or status not in {"approved", "needs_redo", "excused"}:
        flash("🚫 Invalid review.", "danger")
        return redirect(url_for("main.approvals"))

    if status == "approved" and kind == "chore" and not chore_proof_exists(item.proof_photo_name):
        message = "Photo proof is required before this chore can be approved. Needs Redo and Excuse are still available."
        if wants_htmx():
            return render_template(
                "partials/approval_row.html",
                item=item,
                kind=kind,
                has_proof=False,
                approval_error=message,
            )
        flash(f"📷 {message}", "danger")
        return redirect(url_for("main.approvals"))

    old_status = item.status
    review_note = request.form.get("note", "").strip()
    item.status = status
    item.approved_by = current_user.id

    # Chores have a persisted note column. Homework does not, so keep
    # homework review comments in the notification/activity record without
    # changing the existing database schema.
    if kind == "chore" and review_note:
        item.note = review_note

    db.session.commit()

    if status == "approved" and old_status != "approved":
        add_points(
            item.assigned_to,
            item.points,
            f"Approved {kind}: {item.title}",
            kind,
            item.id,
            current_user.id,
        )

    notify(
        item.assigned_to,
        "✅" if status == "approved" else "🔁",
        f"{item.title}: {status.replace('_', ' ').title()}",
        review_note,
        url_for("main.dashboard"),
    )
    log_activity(
        current_user.id,
        status.replace("_", " "),
        kind,
        item.id,
        f"{item.title}{': ' + review_note if review_note else ''}",
    )

    if wants_htmx():
        return render_template(
            "partials/approval_row.html",
            item=item,
            kind=kind,
            has_proof=(kind != "chore" or chore_proof_exists(item.proof_photo_name)),
        )
    return redirect(url_for("main.approvals"))


@bp.route("/approvals")
@login_required
@role_required("parent","manager")
def approvals():
    chores=db.session.scalars(db.select(Chore).where(Chore.status=="completed").order_by(Chore.task_date)).all()
    homework=db.session.scalars(db.select(Homework).where(Homework.status=="completed").order_by(Homework.due_date)).all()
    chore_proof_ids={item.id for item in chores if chore_proof_exists(item.proof_photo_name)}
    return render_template("approvals.html",chores=chores,homework=homework,chore_proof_ids=chore_proof_ids)


@bp.get("/chores/<int:item_id>/proof")
@login_required
def chore_proof(item_id):
    item = db.session.get(Chore, item_id)
    if item is None or not item.proof_photo_name:
        abort(404)
    if not current_user.can_approve and current_user.id not in {item.assigned_to, item.completed_by}:
        abort(403)
    path = chore_proof_path(item.proof_photo_name)
    if path is None or not path.is_file():
        abort(404)
    response = send_file(path, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.route("/messages",methods=("GET","POST"))
@login_required
def messages():
    recipients=db.session.scalars(db.select(User).where(User.active.is_(True),User.id!=current_user.id).order_by(User.name)).all()
    if current_user.role=="child" and (db.session.get(Setting,"kid_direct_messages") or Setting(value="0")).value!="1": recipients=[u for u in recipients if u.role in {"parent","manager"}]
    form=MessageForm(); form.recipient_id.choices=[(u.id,f"{u.emoji} {u.name} — {u.role.title()}") for u in recipients]
    if form.validate_on_submit():
        msg=Message(sender_id=current_user.id,recipient_id=form.recipient_id.data,subject=form.subject.data.strip(),body=form.body.data.strip()); db.session.add(msg); db.session.flush(); msg.thread_id=msg.id; db.session.commit()
        notify(msg.recipient_id,"💬",f"New message from {current_user.name}",msg.subject,url_for("main.messages")); log_activity(current_user.id,"sent message","message",msg.id,msg.subject); return redirect(url_for("main.messages"))
    inbox=db.session.scalars(db.select(Message).where(Message.recipient_id==current_user.id).order_by(Message.created_at.desc())).all(); sent=db.session.scalars(db.select(Message).where(Message.sender_id==current_user.id).order_by(Message.created_at.desc())).all()
    for row in inbox:
        if row.read_at is None: row.read_at=datetime.now(timezone.utc)
    db.session.commit(); return render_template("messages.html",form=form,inbox=inbox,sent=sent)


@bp.post("/messages/<int:message_id>/reply")
@login_required
def reply_message(message_id):
    original=db.session.get(Message,message_id)
    if not original or current_user.id not in {original.sender_id,original.recipient_id}: flash("🚫 Message not found.","danger"); return redirect(url_for("main.messages"))
    recipient=original.sender_id if current_user.id==original.recipient_id else original.recipient_id; body=request.form.get("body","").strip()
    if body:
        msg=Message(sender_id=current_user.id,recipient_id=recipient,subject=f"Re: {original.subject}",body=body,thread_id=original.thread_id or original.id); db.session.add(msg); db.session.commit(); notify(recipient,"↩️",f"Reply from {current_user.name}",original.subject,url_for("main.messages"))
    return redirect(url_for("main.messages"))


@bp.route("/grievances",methods=("GET","POST"))
@login_required
def grievances():
    form=GrievanceForm()
    if form.validate_on_submit():
        g=Grievance(submitted_by=current_user.id,subject=form.subject.data.strip(),description=form.description.data.strip()); db.session.add(g); db.session.commit(); notify_roles({"parent"},"🔒",f"New grievance from {current_user.name}",g.subject,url_for("parent.grievances_page")); log_activity(current_user.id,"submitted grievance","grievance",g.id,g.subject); return redirect(url_for("main.grievances"))
    own=db.session.scalars(db.select(Grievance).where(Grievance.submitted_by==current_user.id).order_by(Grievance.created_at.desc())).all(); return render_template("grievances.html",form=form,grievances=own)


@bp.route("/violations")
@login_required
def violations():
    query=db.select(Violation).order_by(Violation.created_at.desc())
    if not current_user.is_parent: query=query.where(Violation.subject_user_id==current_user.id)
    return render_template("violations.html",violations=db.session.scalars(query).all())


@bp.post("/violations/<int:violation_id>/acknowledge")
@login_required
def acknowledge_violation(violation_id):
    v=db.session.get(Violation,violation_id)
    if not v or v.subject_user_id!=current_user.id: flash("🚫 You cannot acknowledge that notice.","danger")
    else:
        action=request.form.get("action","acknowledge"); v.recipient_response=request.form.get("response","").strip(); v.acknowledged_at=datetime.now(timezone.utc)
        if action=="appeal": v.status="appealed"; v.appealed_at=v.acknowledged_at; notify_roles({"parent"},"📣",f"Violation #{v.id} appealed",v.subject_user.name,url_for("parent.violations_page"))
        else: v.status="acknowledged"
        db.session.commit(); log_activity(current_user.id,v.status,"violation",v.id); flash("✅ Response recorded. Acknowledgement confirms receipt only.","success")
    return redirect(url_for("main.violations"))


@bp.route("/notifications")
@login_required
def notifications():
    rows=db.session.scalars(db.select(Notification).where(Notification.user_id==current_user.id).order_by(Notification.created_at.desc()).limit(200)).all(); return render_template("notifications.html",rows=rows)


@bp.post("/notifications/<int:notification_id>/read")
@login_required
def notification_read(notification_id):
    row=db.session.get(Notification,notification_id)
    if row and row.user_id==current_user.id: row.read_at=datetime.now(timezone.utc); db.session.commit()
    return redirect(request.referrer or url_for("main.notifications"))


@bp.route("/activity")
@login_required
def activity():
    view = request.args.get("view", "household")
    entity = request.args.get("entity", "").strip()
    person = request.args.get("person", type=int)

    # Only parents may open the complete administrative audit trail.
    if view == "parent" and not current_user.is_parent:
        view = "household"

    if view == "mine":
        query = db.select(Activity).where(Activity.actor_id == current_user.id).order_by(Activity.created_at.desc())
        if entity:
            query = query.where(Activity.entity_type == entity)
        rows = db.session.scalars(query.limit(500)).all()
    elif view == "parent":
        query = db.select(Activity).order_by(Activity.created_at.desc())
        if person:
            query = query.where(Activity.actor_id == person)
        if entity:
            query = query.where(Activity.entity_type == entity)
        rows = db.session.scalars(query.limit(500)).all()
    else:
        rows = family_safe_activity(500)
        if person:
            rows = [row for row in rows if row.actor_id == person]
        if entity:
            rows = [row for row in rows if row.entity_type == entity]

    users = db.session.scalars(db.select(User).where(User.active.is_(True)).order_by(User.name)).all()
    family_post_form = FamilyPostForm(prefix="family-post")

    return render_template(
        "activity.html",
        rows=rows,
        users=users,
        view=view,
        family_post_form=family_post_form,
    )


@bp.route("/points")
@login_required
def points_ledger():
    query = db.select(PointTransaction).order_by(PointTransaction.created_at.desc())
    if not current_user.is_parent:
        query = query.where(PointTransaction.user_id == current_user.id)
    rows = db.session.scalars(query.limit(500)).all()
    members = db.session.scalars(db.select(User).where(User.role.in_(["manager", "child"]), User.active.is_(True)).order_by(User.name)).all()
    balances = [{"user": member, "points": point_balance(member.id), "money": point_balance(member.id) * money_rate()} for member in members]
    return render_template("points.html", rows=rows, balances=balances, rate=money_rate())


@bp.route("/reports")
@login_required
@role_required("parent","manager")
def reports():
    start=date.today()-timedelta(days=29); members=db.session.scalars(db.select(User).where(User.role.in_(["manager","child"]),User.active.is_(True)).order_by(User.name)).all()
    member_rows=[]
    for u in members:
        chores_total=int(db.session.scalar(db.select(func.count(Chore.id)).where(Chore.assigned_to==u.id,Chore.task_date>=start)) or 0)
        chores_approved=int(db.session.scalar(db.select(func.count(Chore.id)).where(Chore.assigned_to==u.id,Chore.task_date>=start,Chore.status=="approved")) or 0)
        redo=int(db.session.scalar(db.select(func.count(Chore.id)).where(Chore.assigned_to==u.id,Chore.task_date>=start,Chore.status=="needs_redo")) or 0)
        violations_count=int(db.session.scalar(db.select(func.count(Violation.id)).where(Violation.subject_user_id==u.id,Violation.incident_date>=start)) or 0)
        member_rows.append({"name":u.name,"points":point_balance(u.id),"completion":round(chores_approved/chores_total*100) if chores_total else 0,"redo":redo,"violations":violations_count})
    categories=[]
    for c in db.session.scalars(db.select(ViolationCategory).order_by(ViolationCategory.label)).all():
        count=int(db.session.scalar(db.select(func.count()).select_from(Violation).join(Violation.categories).where(ViolationCategory.id==c.id,Violation.incident_date>=start)) or 0); categories.append({"label":c.label,"count":count})
    return render_template("reports.html",members=member_rows,categories=categories)


@bp.route("/exports")
@login_required
@role_required("parent")
def exports(): return render_template("exports.html")


@bp.post("/exports/create")
@login_required
@role_required("parent")
def create_export():
    stamp=datetime.now().strftime("%Y%m%d-%H%M%S"); root=Path(current_app.config["EXPORT_DIR"]); folder=root/f"family-export-{stamp}"; folder.mkdir(parents=True,exist_ok=True)
    models={"users":User,"chores":Chore,"homework":Homework,"messages":Message,"grievances":Grievance,"violations":Violation,"violation_categories":ViolationCategory,"violation_revisions":ViolationRevision,"points":PointTransaction,"notifications":Notification,"activity":Activity,"login_events":LoginEvent,"schedule_locks":ScheduleLock}
    manifest={}
    for name,model in models.items():
        data=[]
        for row in db.session.scalars(db.select(model)).all():
            payload={col.name:getattr(row,col.name) for col in row.__table__.columns}; data.append({k:(v.isoformat() if hasattr(v,"isoformat") else v) for k,v in payload.items()})
        manifest[name]=data
        if data:
            with (folder/f"{name}.csv").open("w",newline="",encoding="utf-8") as h: writer=csv.DictWriter(h,fieldnames=data[0].keys()); writer.writeheader(); writer.writerows(data)
    (folder/"full-backup.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8"); backup=backup_database()
    if backup: shutil.copy2(backup,folder/"family_dashboard.db")
    zip_path=root/f"family-export-{stamp}.zip"
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as archive:
        for file in folder.iterdir(): archive.write(file,file.name)
    shutil.rmtree(folder); log_activity(current_user.id,"created export","export",details=zip_path.name); return send_file(zip_path,as_attachment=True)
