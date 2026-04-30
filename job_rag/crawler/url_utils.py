"""URL helpers for crawling and deduplication."""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    raw = (url or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    if parsed.scheme in {"http", "https"}:
        query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
        path = parsed.path.rstrip("/") or "/"
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                "",
                query,
                "",
            )
        )

    return str(Path(raw))


def is_valid_url(url: str) -> bool:
    """Return whether the input is a valid HTTP/HTTPS URL."""
    parsed = urlparse((url or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def make_job_id(url: str, title: str | None = None, company: str | None = None) -> str:
    """Create a stable job id from URL or key fields."""
    source = "|".join(part for part in (normalize_url(url), title or "", company or "") if part)
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
    return f"job_{digest}"


def source_name_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.netloc:
        return parsed.netloc.lower()
    path = Path(url)
    return path.stem or "local"

