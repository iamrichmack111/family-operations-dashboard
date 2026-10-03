from __future__ import annotations

from datetime import datetime, timezone

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from .extensions import db
from .models import PointRequest, PointTransaction
from .services import add_points, log_activity, notify, notify_roles, point_balance

bp = Blueprint("point_requests", __name__)


def reviewer_required():
    if current_user.role not in {"parent", "manager"}:
        abort(403)


@bp.route("/points/request", methods=("GET", "POST"))
@login_required
def request_points():
    if current_user.is_parent:
        flash("Parent accounts use point adjustments instead of point requests.", "warning")
        return redirect(url_for("main.points_ledger"))

    if request.method == "POST":
        amount = request.form.get("amount", type=int) or 0
        reason = (request.form.get("reason") or "").strip()
        if amount < 1 or amount > 10000:
            flash("Choose an amount from 1 to 10,000 points.", "danger")
        elif not reason:
            flash("Enter a reason for the request.", "danger")
        else:
            item = PointRequest(user_id=current_user.id, amount=amount, reason=reason[:255], status="pending")
            db.session.add(item)
            db.session.commit()
            notify_roles(
                {"parent", "manager"},
                "📨",
                f"Point request from {current_user.name}",
                f"{amount} points · {reason[:120]}",
                url_for("point_requests.review_requests"),
            )
            log_activity(current_user.id, "requested points", "point_request", item.id, f"{amount}: {reason[:120]}")
            flash("📨 Point request submitted.", "success")
            return redirect(url_for("point_requests.request_points"))

    rows = db.session.scalars(
        db.select(PointRequest)
        .where(PointRequest.user_id == current_user.id)
        .order_by(PointRequest.created_at.desc(), PointRequest.id.desc())
        .limit(500)
    ).all()
    return render_template("request_points.html", rows=rows)


@bp.get("/point-requests")
@login_required
def review_requests():
    reviewer_required()
    rows = db.session.scalars(
        db.select(PointRequest)
        .order_by(PointRequest.created_at.desc(), PointRequest.id.desc())
        .limit(1000)
    ).all()
    pending = sum(1 for row in rows if row.status == "pending")
    total_pending = sum(row.amount for row in rows if row.status == "pending")
    return render_template(
        "parent_point_requests_v62.html",
        point_requests=rows,
        pending_count=pending,
        pending_total=total_pending,
    )


@bp.post("/point-requests/<int:request_id>/approve")
@login_required
def approve_request(request_id: int):
    reviewer_required()
    item = db.session.get(PointRequest, request_id)
    if item is None or item.status != "pending":
        flash("That request is no longer pending.", "warning")
        return redirect(url_for("point_requests.review_requests"))

    if current_user.role == "manager" and item.user_id == current_user.id:
        flash("Managers cannot approve their own point requests.", "danger")
        return redirect(url_for("point_requests.review_requests"))

    existing = db.session.scalar(
        db.select(PointTransaction).where(
            PointTransaction.source_type == "point_request",
            PointTransaction.source_id == item.id,
            PointTransaction.user_id == item.user_id,
        )
    )
    before = point_balance(item.user_id)
    item.status = "approved"
    item.resolved_by = current_user.id
    item.resolved_at = datetime.now(timezone.utc)
    db.session.flush()

    if existing is None:
        add_points(
            item.user_id,
            item.amount,
            f"Approved point request: {item.reason[:220]}",
            "point_request",
            item.id,
            current_user.id,
        )
    else:
        db.session.commit()

    after = point_balance(item.user_id)
    notify(item.user_id, "✅", "Point request approved", f"+{item.amount} points · balance {after}", url_for("point_requests.request_points"))
    log_activity(current_user.id, "approved point request", "point_request", item.id, f"+{item.amount}: {item.reason[:120]} · {before} -> {after}")
    flash(f"Approved {item.amount} points for {item.user.name}.", "success")
    return redirect(url_for("point_requests.review_requests"))


@bp.post("/point-requests/<int:request_id>/deny")
@login_required
def deny_request(request_id: int):
    reviewer_required()
    item = db.session.get(PointRequest, request_id)
    if item is None or item.status != "pending":
        flash("That request is no longer pending.", "warning")
        return redirect(url_for("point_requests.review_requests"))

    if current_user.role == "manager" and item.user_id == current_user.id:
        flash("Managers cannot resolve their own point requests.", "danger")
        return redirect(url_for("point_requests.review_requests"))

    item.status = "denied"
    item.resolved_by = current_user.id
    item.resolved_at = datetime.now(timezone.utc)
    db.session.commit()
    notify(item.user_id, "❌", "Point request denied", f"{item.amount} points · {item.reason[:120]}", url_for("point_requests.request_points"))
    log_activity(current_user.id, "denied point request", "point_request", item.id, item.reason[:120])
    flash("Request denied.", "success")
    return redirect(url_for("point_requests.review_requests"))
