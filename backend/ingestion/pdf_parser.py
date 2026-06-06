"""PDF parser for bank statements and bills."""

from __future__ import annotations

from pathlib import Path


def extract_text_from_pdf(file_path: str | Path) -> str:
    """Extract plain text from a PDF using PyMuPDF."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise ImportError("Install pymupdf: pip install pymupdf") from exc

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    chunks: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            chunks.append(page.get_text())

    return "\n".join(chunks).strip()


def extract_text_from_bytes(data: bytes) -> str:
    """Extract text from PDF bytes (e.g. uploaded file)."""
    try:
        import fitz
    except ImportError as exc:
        raise ImportError("Install pymupdf: pip install pymupdf") from exc

    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc).strip()
