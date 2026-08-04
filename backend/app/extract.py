"""Extract plain text from uploaded article files."""

from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


def extension_of(filename: str) -> str:
    return Path(filename).suffix.lower()


def is_allowed_filename(filename: str) -> bool:
    return extension_of(filename) in ALLOWED_EXTENSIONS


def extract_text(filename: str, raw: bytes) -> str:
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Upload a .txt, .md, or .pdf file."
        )

    if ext in {".txt", ".md"}:
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("Could not decode file as UTF-8 text.") from exc
        return text.strip()

    # PDF
    try:
        reader = PdfReader(io.BytesIO(raw))
        parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(page_text)
        text = "\n".join(parts).strip()
    except Exception as exc:  # noqa: BLE001 — surface parse failures to API
        raise ValueError("Could not extract text from the PDF.") from exc

    return text
