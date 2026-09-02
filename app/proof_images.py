"""Validation and storage helpers for chore photo proof."""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from uuid import uuid4

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


ALLOWED_UPLOAD_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
}
STORED_EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class ProofImageError(ValueError):
    """Raised when uploaded proof is missing, unsafe, or not a valid image."""


def _proof_directory() -> Path:
    directory = Path(current_app.config["CHORE_PROOF_DIR"])
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def chore_proof_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    safe_name = Path(filename).name
    if safe_name != filename or Path(safe_name).suffix.lower() not in set(STORED_EXTENSIONS.values()):
        return None
    return _proof_directory() / safe_name


def chore_proof_exists(filename: str | None) -> bool:
    path = chore_proof_path(filename)
    return bool(path and path.is_file())


def delete_chore_proof(filename: str | None) -> None:
    path = chore_proof_path(filename)
    if path:
        path.unlink(missing_ok=True)


def save_chore_proof(upload: FileStorage | None, chore_id: int) -> str:
    """Validate, normalize, and atomically store one proof image.

    Uploaded bytes are decoded and re-encoded instead of being copied as-is.
    That strips original metadata and trailing payloads while ensuring the file
    contents really match the allowed JPEG, PNG, or WebP extension.
    """

    if upload is None or not upload.filename:
        raise ProofImageError("Take or choose a photo before marking this chore complete.")

    cleaned_name = secure_filename(upload.filename)
    extension = Path(cleaned_name).suffix.lower()
    expected_format = ALLOWED_UPLOAD_FORMATS.get(extension)
    if not cleaned_name or expected_format is None:
        raise ProofImageError("Use a JPEG, PNG, or WebP image.")

    stream = upload.stream
    try:
        stream.seek(0, os.SEEK_END)
        byte_count = stream.tell()
        stream.seek(0)
    except (AttributeError, OSError) as exc:
        raise ProofImageError("The selected photo could not be read.") from exc

    max_bytes = int(current_app.config["PROOF_IMAGE_MAX_BYTES"])
    if byte_count <= 0:
        raise ProofImageError("The selected photo is empty.")
    if byte_count > max_bytes:
        raise ProofImageError(f"The photo must be smaller than {max_bytes // (1024 * 1024)} MB.")

    target: Path | None = None
    temporary: Path | None = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(stream) as source:
                actual_format = (source.format or "").upper()
                if actual_format != expected_format or actual_format not in STORED_EXTENSIONS:
                    raise ProofImageError("The image contents do not match the filename.")
                if getattr(source, "n_frames", 1) != 1:
                    raise ProofImageError("Animated images are not allowed for chore proof.")

                width, height = source.size
                max_pixels = int(current_app.config["PROOF_IMAGE_MAX_PIXELS"])
                if width < 1 or height < 1 or width * height > max_pixels:
                    raise ProofImageError("The photo dimensions are too large.")

                source.load()
                normalized = ImageOps.exif_transpose(source)
                if actual_format == "JPEG":
                    normalized = normalized.convert("RGB")
                    save_options = {"quality": 90, "optimize": True, "progressive": True}
                elif normalized.mode not in {"RGB", "RGBA", "L", "LA"}:
                    normalized = normalized.convert("RGBA")
                    save_options = {"optimize": True} if actual_format == "PNG" else {"quality": 90, "method": 4}
                else:
                    save_options = {"optimize": True} if actual_format == "PNG" else {"quality": 90, "method": 4}

                stored_extension = STORED_EXTENSIONS[actual_format]
                filename = f"chore-{chore_id}-{uuid4().hex}{stored_extension}"
                target = _proof_directory() / filename
                temporary = target.with_name(f".{target.name}.{uuid4().hex}.uploading")
                normalized.save(temporary, format=actual_format, **save_options)

        os.replace(temporary, target)
        return target.name
    except ProofImageError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError, OSError, ValueError) as exc:
        raise ProofImageError("The selected file is not a safe, readable image.") from exc
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)
