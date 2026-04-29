"""Extract plain text from resume files (.pdf / .docx / .txt).

This is the first stage of the pipeline.  We normalise to UTF-8 plain text
regardless of source format so that downstream parsers see a uniform input.

Format strategy:
- PDF  → PyMuPDF (handles both text-layer and scanned PDFs that have OCR)
- DOCX → python-docx (reads paragraph text only; embedded tables/images ignored)
- TXT  → direct read with UTF-8 encoding

All extracted text passes through clean_text() to collapse excess whitespace.
"""

from __future__ import annotations

from pathlib import Path


def extract_text(file_path: str | Path) -> str:
    """Dispatch to the appropriate reader based on file extension.

    Returns cleaned UTF-8 plain text.  Raises FileNotFoundError if the path
    doesn't exist, and ValueError for unsupported formats or empty extractions
    (so the pipeline can short-circuit with a clear error).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf(path)
    elif suffix == ".docx":
        text = _extract_docx(path)
    elif suffix == ".txt":
        text = _extract_txt(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Supported: .pdf, .docx, .txt")

    # Deferred import avoids circular dependency at module level
    from course_project.backend.app.resume_search.utils import clean_text

    cleaned = clean_text(text)
    if not cleaned.strip():
        raise ValueError("Extracted text is empty after cleaning")
    return cleaned


def _extract_pdf(path: Path) -> str:
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    parts: list[str] = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    return "\n".join(parts)


def _extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _extract_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")
