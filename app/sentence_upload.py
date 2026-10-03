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

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".doc", ".docx", ".txt"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def _upload_dir() -> Path:
    path = Path(current_app.instance_path) / "homework_submissions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _can_manage_homework(item: Homework) -> bool:
    if item.assigned_to == current_user.id:
        return True
    return bool(getattr(current_user, "can_approve", False) or current_user.role == "parent")


@bp.get("/upload-sentences")
@login_required
def upload_sentences():
    stmt = db.select(Homework).where(Homework.status.in_(("assigned", "needs_redo")))

    # Zara/children/managers see their own schoolwork here. Parent accounts can
    # see all outstanding homework so they can help submit when needed.
    if current_user.role in {"child", "manager"}:
        stmt = stmt.where(Homework.assigned_to == current_user.id)

    # due_date exists in the Family Operations Homework model used by the
    # dashboard. Fall back to ID ordering if an older model lacks it.
    if hasattr(Homework, "due_date"):
        stmt = stmt.order_by(Homework.due_date.asc(), Homework.id.desc())
    else:
        stmt = stmt.order_by(Homework.id.desc())

    homework = db.session.scalars(stmt).all()
    return render_template("upload_sentences.html", homework=homework)


@bp.post("/upload-sentences/<int:item_id>")
@login_required
def submit_homework(item_id: int):
    item = db.session.get(Homework, item_id)
    if item is None:
        abort(404)
    if not _can_manage_homework(item):
        abort(403)
    if item.status not in {"assigned", "needs_redo"}:
        flash("That homework is no longer waiting for an upload.", "warning")
        return redirect(url_for("sentence_upload.upload_sentences"))

    upload = request.files.get("homework_file")
    if upload is None or not upload.filename:
        flash("Choose a homework photo or file first.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    original = secure_filename(upload.filename) or "homework"
    suffix = Path(original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        flash("Use PDF, JPG, PNG, WebP, HEIC/HEIF, DOC/DOCX, or TXT.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    data = upload.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        flash("Homework uploads must be 20 MB or smaller.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")
    if not data:
        flash("That upload was empty. Choose the homework file again.", "danger")
        return redirect(url_for("sentence_upload.upload_sentences") + f"#homework-{item.id}")

    folder = _upload_dir()
    stored = f"homework-{item.id}-{uuid4().hex}{suffix}"
    destination = folder / stored
    destination.write_bytes(data)

    old_name = (getattr(item, "submission_name", "") or "").strip()
    item.submission_name = stored
    item.submission_original_name = original
    item.status = "completed"
    item.completed_by = current_user.id

    try:
        db.session.commit()
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    if old_name and old_name != stored:
        (folder / Path(old_name).name).unlink(missing_ok=True)

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
    if not _can_manage_homework(item):
        abort(403)

    stored = Path(item.submission_name).name
    folder = _upload_dir()
    if not (folder / stored).exists():
        abort(404)

    return send_from_directory(
        str(folder),
        stored,
        download_name=(item.submission_original_name or stored),
        as_attachment=False,
    )
