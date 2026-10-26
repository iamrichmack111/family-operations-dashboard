from pathlib import Path
from uuid import uuid4
from io import BytesIO

from flask import (
    Blueprint, current_app, flash, redirect,
    render_template, request, send_from_directory, url_for
)
from flask_login import current_user, login_required
from PIL import Image, ImageOps, UnidentifiedImageError

from .extensions import db
from .models import User, utcnow

bp = Blueprint("family_photos", __name__, url_prefix="/family-photos")


class FamilyPhoto(db.Model):
    __tablename__ = "family_photos"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False, unique=True)
    title = db.Column(db.String(160), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    uploader = db.relationship(User)


@bp.route("/", methods=["GET", "POST"])
@login_required
def gallery():
    if request.method == "POST":
        if current_user.role not in ("parent", "manager"):
            flash("Only parents and managers can upload photos.", "warning")
            return redirect(url_for("family_photos.gallery"))

        upload = request.files.get("photo")
        title = request.form.get("title", "").strip()[:160]

        if not upload or not upload.filename:
            flash("Choose a photo to upload.", "warning")
            return redirect(url_for("family_photos.gallery"))

        photo_dir = Path(current_app.config["UPLOAD_DIR"]) / "family_photos"
        photo_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{uuid4().hex}.jpg"
        destination = photo_dir / filename

        try:
            data = upload.read(8 * 1024 * 1024 + 1)

            if len(data) > 8 * 1024 * 1024:
                raise ValueError("Photo exceeds the 8 MB limit.")

            with Image.open(BytesIO(data)) as original:
                if original.format not in ("JPEG", "PNG", "WEBP"):
                    raise ValueError("Only JPG, PNG, and WEBP photos are allowed.")

                if original.width * original.height > 25_000_000:
                    raise ValueError("Photo dimensions are too large.")

                original.load()
                image = ImageOps.exif_transpose(original)
                image = image.convert("RGB")
                image.thumbnail((2400, 2400))
                image.save(destination, "JPEG", quality=87, optimize=True)

            photo = FamilyPhoto(
                filename=filename,
                title=title or "Family photo",
                uploaded_by=current_user.id
            )

            db.session.add(photo)
            db.session.commit()

            flash("📸 Photo uploaded successfully!", "success")

        except (
            ValueError,
            UnidentifiedImageError,
            Image.DecompressionBombError,
            OSError
        ) as error:
            destination.unlink(missing_ok=True)
            flash(f"Upload failed: {error}", "danger")

        return redirect(url_for("family_photos.gallery"))

    photos = db.session.scalars(
        db.select(FamilyPhoto).order_by(FamilyPhoto.created_at.desc())
    ).all()

    return render_template("family_photos.html", photos=photos)


@bp.route("/image/<int:photo_id>")
@login_required
def image(photo_id):
    photo = db.get_or_404(FamilyPhoto, photo_id)
    folder = Path(current_app.config["UPLOAD_DIR"]) / "family_photos"

    response = send_from_directory(folder, photo.filename)
    response.headers["Cache-Control"] = "private, max-age=3600"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
