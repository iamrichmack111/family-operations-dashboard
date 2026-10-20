"""Extract and count readable sentences from homework documents."""
from __future__ import annotations
import io
import re
from zipfile import BadZipFile


def count_sentences(text: str) -> int:
    """Count sentence-ending punctuation; ignore empty and punctuation-only fragments."""
    text = re.sub(r"\s+", " ", text).strip()
    # A period in decimals is not a sentence boundary. Consecutive punctuation counts once.
    return sum(1 for m in re.finditer(r"(?<!\d)[.!?]+(?=\s|$|[\"'’”])", text))


def sentences_in_upload(data: bytes, suffix: str) -> int | None:
    """Return a count or None when text cannot be reliably extracted."""
    if suffix == ".txt":
        text = data.decode("utf-8-sig", errors="replace")
    elif suffix == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(data))
        text = "\n".join([p.text for p in doc.paragraphs] + [c.text for t in doc.tables for row in t.rows for c in row.cells])
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=False)
        if len(reader.pages) > 200:
            raise ValueError("PDF has too many pages (maximum 200).")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    else:
        return None  # Scanned images and old .doc are not machine-readable here.
    return count_sentences(text) if text.strip() else None
