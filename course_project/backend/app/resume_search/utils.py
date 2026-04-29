"""General-purpose utilities shared across the resume_search module.

These are pure functions with no side-effects (save_json excepted).  They handle
text normalisation, JSON I/O, and URL validation — tiny building blocks that
don't warrant their own service.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse


def clean_text(text: str) -> str:
    """Normalise whitespace: collapse tabs, merge blank lines, strip edges.

    Designed for Chinese + English mixed text.  Does NOT modify character
    content — only whitespace structure.
    """
    text = text.replace("\t", " ")
    text = re.sub(r" +", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.splitlines()]
    # Strip leading / trailing empty lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def strip_json_markdown(raw: str) -> str:
    """Peel off ```json ... ``` fences that LLMs often wrap around JSON output.

    Handles both ```json and bare ``` variants.  Idempotent — safe to call on
    already-clean text.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def save_json(data: dict, path: str | Path) -> None:
    """Persist a dict to disk as UTF-8 JSON with consistent formatting.

    Uses ensure_ascii=False for readable Chinese characters and indent=2 for
    human-friendly diffs.  Creates parent directories if needed.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: str | Path) -> dict:
    """Read and parse a JSON file.  Raises on malformed input — callers must handle."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_domain(url: str) -> str:
    """Extract netloc from a URL; returns 'unknown' on parse failure."""
    try:
        return urlparse(url).netloc or "unknown"
    except Exception:
        return "unknown"


def is_valid_http_url(url: str) -> bool:
    """Return True if *url* is a well-formed http/https link with a non-empty host.

    Used as a pre-filter before storing search results — weeds out relative
    paths, data URIs, and garbage text that DuckDuckGo occasionally returns.
    """
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)
