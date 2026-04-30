"""Crawl candidate pages into PageContent records.

The production version can replace the HTTP/local-file fallback with a real
Browser Use runner. The fallback keeps the demo stable and compliant.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from job_rag.config import EXAMPLES_DIR, LOCAL_JOBS_DIR
from job_rag.crawler.browser_use_adapter import (
    BrowserUseUnavailable,
    crawl_with_browser_use,
    should_try_browser_use,
)
from job_rag.crawler.page_extractor import html_to_visible_text, truncate_text
from job_rag.crawler.url_utils import is_valid_url
from job_rag.schemas import PageContent


def _resolve_local_path(url: str) -> Path | None:
    raw = (url or "").strip()
    if not raw:
        return None

    parsed = urlparse(raw)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path.lstrip("/")) if parsed.netloc == "" else unquote(parsed.path))

    candidates = [
        Path(raw),
        EXAMPLES_DIR / raw,
        LOCAL_JOBS_DIR / raw,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _read_local_html(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fetch_http_html(url: str, timeout: int = 15) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; JobRAGDemo/1.0; public demo crawler)",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=", 1)[-1].split(";")[0].strip()
        return response.read().decode(charset or "utf-8", errors="replace")


async def crawl_page(url: str) -> PageContent:
    """Crawl one public job page or local demo page and return visible text."""
    raw_url = (url or "").strip()
    if not raw_url:
        return PageContent(url=url, status="failed", error="empty url")

    try:
        local_path = _resolve_local_path(raw_url)
        browser_use_error = None
        if local_path:
            html = await asyncio.to_thread(_read_local_html, local_path)
        elif is_valid_url(raw_url):
            if should_try_browser_use(raw_url):
                try:
                    return await crawl_with_browser_use(raw_url)
                except BrowserUseUnavailable as exc:
                    browser_use_error = str(exc)
            html = await asyncio.to_thread(_fetch_http_html, raw_url)
        else:
            return PageContent(url=raw_url, status="failed", error="invalid url or missing local file")

        visible_text, title = html_to_visible_text(html)
        visible_text = truncate_text(visible_text)
        if not visible_text:
            return PageContent(url=raw_url, status="failed", title=title, html=html, error="empty visible text")
        return PageContent(
            url=raw_url,
            status="success",
            title=title,
            visible_text=visible_text,
            html=html,
            error=browser_use_error,
        )
    except (HTTPError, URLError, OSError, UnicodeDecodeError) as exc:
        return PageContent(url=raw_url, status="failed", error=str(exc))


async def crawl_pages(urls: list[str]) -> list[PageContent]:
    """Crawl multiple URLs and keep failed results instead of crashing."""
    results: list[PageContent] = []
    for url in urls:
        results.append(await crawl_page(url))
    return results
