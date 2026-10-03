from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .extensions import db
from .models import Homework
from .services import log_activity, notify_roles

bp = Blueprint("sentence_upload", __name__)

ALLOWED = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".doc", ".docx", ".txt"}
MAX_BYTES = 20 * 1024 * 1024

def upload_dir() -> Path:
    p = Path(current_app.instance_path) / "homework_submissions"
    p.mkdir(parents=True, exist_ok=True)
    return p

def may_submit(item: Homework) -> bool:
    if item.assigned_to == current_user.id:
        return True
    return bool(getattr(current_user, "can_approve", False) or current_user.role == "parent")

@bp.get("/upload-sentences")
@login_required
def upload_sentences():
    stmt = db.select(Homework).where(Homework.status.in_(("assigned", "needs_redo")))
    if current_user.role in {"child", "manager"}:
        stmt = stmt.where(Homework.assigned_to == current_user.id)
    if hasattr(Homework, "due_date"):
        stmt = stmt.order_by(Homework.due_date.asc(), Homework.id.desc())
    else:
        stmt = stmt.order_by(Homework.id.desc())
    return render_template("upload_sentences.html", homework=db.session.scalars(stmt).all())

@bp.post("/upload-sentences/<int:item_id>")
@login_required
def submit_homework(item_id: int):
    item = db.session.get(Homework, item_id)
    if item is None:
        abort(404)
    if not may_submit(item):
        abort(403)
    if item.status not in {"assigned", "needs_redo"}:
        flash("That homework is no longer waiting for an upload.", "warning")
        return redirect(url_for("sentence_upload.upload_sentences"))

    f = request.files.get("homework_file")
    if f is None or not f.filename:
        flash("Choose the homework file or picture first.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    original = secure_filename(f.filename) or "homework"
    ext = Path(original).suffix.lower()
    if ext not in ALLOWED:
        flash("Use PDF, JPG, PNG, WebP, HEIC/HEIF, DOC/DOCX, or TXT.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    raw = f.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        flash("The homework file must be between 1 byte and 20 MB.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    stored = f"homework-{item.id}-{uuid4().hex}{ext}"
    dest = upload_dir() / stored
    dest.write_bytes(raw)

    old = (getattr(item, "submission_name", "") or "").strip()
    item.submission_name = stored
    item.submission_original_name = original
    item.status = "completed"
    item.completed_by = current_user.id

    try:
        db.session.commit()
    except Exception:
        dest.unlink(missing_ok=True)
        raise

    if old and old != stored:
        (upload_dir() / Path(old).name).unlink(missing_ok=True)

    notify_roles(
        {"parent", "manager"},
        "📚",
        f"{item.assignee.name} uploaded homework",
        item.title,
        url_for("main.approvals"),
    )
    log_activity(current_user.id, "uploaded homework", "homework", item.id, original)
    flash("📚 Homework uploaded and sent to Approvals.", "success")
    return redirect(url_for("sentence_upload.upload_sentences"))

@bp.get("/homework-submissions/<int:item_id>")
@login_required
def homework_submission(item_id: int):
    item = db.session.get(Homework, item_id)
    if item is None or not getattr(item, "submission_name", ""):
        abort(404)
    if not may_submit(item):
        abort(403)
    stored = Path(item.submission_name).name
    if not (upload_dir() / stored).exists():
        abort(404)
    return send_from_directory(
        str(upload_dir()),
        stored,
        download_name=(item.submission_original_name or stored),
        as_attachment=False,
    )
