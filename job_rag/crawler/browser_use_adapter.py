"""Optional Browser Use integration for public job pages.

The demo must run without browser-use, so this module keeps all imports lazy and
raises structured errors that the runner can fall back from.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
from typing import Any
from urllib.parse import urlparse

from job_rag.config import (
    BROWSER_USE_CONFIG_DIR,
    BROWSER_USE_DOWNLOADS_DIR,
    BROWSER_USE_ENABLED,
    BROWSER_USE_HEADLESS,
    BROWSER_USE_HOME_DIR,
    BROWSER_USE_PROFILE_DIR,
    BROWSER_USE_TIMEOUT_SECONDS,
)
from job_rag.crawler.page_extractor import html_to_visible_text, truncate_text
from job_rag.schemas import PageContent


class BrowserUseUnavailable(RuntimeError):
    """Raised when browser-use is not installed, configured, or able to run."""


def is_browser_use_enabled() -> bool:
    """Return whether the project is configured to try browser-use."""
    return BROWSER_USE_ENABLED


def is_browser_use_available() -> bool:
    """Return True when the browser_use Python package can be imported."""
    return importlib.util.find_spec("browser_use") is not None


def should_try_browser_use(url: str) -> bool:
    """Return True when a URL should use the browser-use path."""
    parsed = urlparse((url or "").strip())
    return is_browser_use_enabled() and parsed.scheme in {"http", "https"} and is_browser_use_available()


def configure_browser_use_environment() -> None:
    """Point browser-use writable directories at the workspace by default."""
    BROWSER_USE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_USE_HOME_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_USE_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_USE_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("BROWSER_USE_CONFIG_DIR", str(BROWSER_USE_CONFIG_DIR))
    os.environ.setdefault("BROWSER_USE_HOME", str(BROWSER_USE_HOME_DIR))
    os.environ.setdefault("BROWSER_USE_SETUP_LOGGING", "false")


async def _evaluate_current_page(session: Any, expression: str) -> Any:
    cdp_session = await session.get_or_create_cdp_session()
    result = await cdp_session.cdp_client.send.Runtime.evaluate(
        params={"expression": expression, "returnByValue": True},
        session_id=cdp_session.session_id,
    )
    return (result.get("result") or {}).get("value")


async def _crawl_with_browser_use(url: str) -> PageContent:
    configure_browser_use_environment()
    try:
        from browser_use import BrowserSession
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise BrowserUseUnavailable(f"browser-use import failed: {exc}") from exc

    session = BrowserSession(
        headless=BROWSER_USE_HEADLESS,
        user_data_dir=str(BROWSER_USE_PROFILE_DIR),
        downloads_path=str(BROWSER_USE_DOWNLOADS_DIR),
        keep_alive=False,
        args=[
            "--disable-crash-reporter",
            "--disable-crashpad",
            "--disable-breakpad",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )
    try:
        await session.start()
        await session.navigate_to(url)
        title = await session.get_current_page_title()
        html = await _evaluate_current_page(session, "document.documentElement.outerHTML")
        visible_text = await _evaluate_current_page(session, "document.body ? document.body.innerText : ''")
        if not visible_text and html:
            visible_text, parsed_title = html_to_visible_text(str(html))
            title = title or parsed_title
        visible_text = truncate_text(str(visible_text or ""))
        if not visible_text:
            return PageContent(url=url, status="failed", title=title, html=str(html or ""), error="empty visible text")
        return PageContent(
            url=url,
            status="success",
            title=title,
            visible_text=visible_text,
            html=str(html or ""),
        )
    except Exception as exc:  # pragma: no cover - real browser environment dependent
        raise BrowserUseUnavailable(f"browser-use crawl failed: {exc}") from exc
    finally:
        try:
            await session.kill()
        except Exception:
            pass


async def crawl_with_browser_use(url: str) -> PageContent:
    """Open a public URL with browser-use and return visible page content."""
    raw_url = (url or "").strip()
    if not is_browser_use_enabled():
        raise BrowserUseUnavailable("browser-use is disabled; set JOB_RAG_ENABLE_BROWSER_USE=1 to enable it")
    if not is_browser_use_available():
        raise BrowserUseUnavailable("browser-use package is not installed")
    if urlparse(raw_url).scheme not in {"http", "https"}:
        raise BrowserUseUnavailable("browser-use only handles http/https URLs in this module")
    try:
        return await asyncio.wait_for(_crawl_with_browser_use(raw_url), timeout=BROWSER_USE_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        raise BrowserUseUnavailable(f"browser-use crawl timed out after {BROWSER_USE_TIMEOUT_SECONDS}s") from exc
