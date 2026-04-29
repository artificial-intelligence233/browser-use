"""Search for job links using DuckDuckGo (free, no API key required).

We use DuckDuckGo's text search API because it requires zero authentication and
works across all platforms.  The trade-off is rate-limiting: bursts of >~30
queries may be temporarily throttled.

Import fallback chain: duckduckgo_search (project dependency) → ddgs →
empty results with a warning.  This ensures the module is importable even when
the search dependency is missing.

Important: this module only returns candidate job URLs from search results.
It does NOT verify HTTP status, content type, or whether a page is a real job
detail page — that is handled by downstream browser-use/RAG modules.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys

from course_project.backend.app.resume_search.schema import JobLink
from course_project.backend.app.resume_search.utils import get_domain, is_valid_http_url

logger = logging.getLogger(__name__)
SEARCH_TIMEOUT_SECONDS = 30


def _format_search_warning(query: str, reason: str) -> str:
    return f"DuckDuckGo search failed for query {query!r}: {reason}"


def search_jobs_by_query_with_warning(query: str, max_results: int = 5) -> tuple[list[JobLink], str | None]:
    """Execute a single search and return both results and a user-visible warning.

    Returning warning text lets CLI/API callers expose real search failures
    instead of silently showing "0 links" with no explanation.
    """
    payload = json.dumps({"query": query, "max_results": max_results}, ensure_ascii=False)
    try:
        completed = subprocess.run(
            [sys.executable, "-c", _DUCKDUCKGO_CHILD_SCRIPT],
            input=payload,
            text=True,
            capture_output=True,
            timeout=SEARCH_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        warning = _format_search_warning(query, f"timeout after {SEARCH_TIMEOUT_SECONDS}s")
        logger.warning(warning)
        return [], warning
    except Exception as exc:
        warning = _format_search_warning(query, f"{type(exc).__name__}: {exc}")
        logger.warning(warning)
        return [], warning

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "search subprocess failed").strip()
        warning = _format_search_warning(query, detail[-1200:])
        logger.warning(warning)
        return [], warning

    results: list[JobLink] = []
    try:
        raw_items = json.loads(completed.stdout or "[]")
    except json.JSONDecodeError as exc:
        warning = _format_search_warning(query, f"{type(exc).__name__}: {exc}")
        logger.warning(warning)
        return [], warning

    for item in raw_items:
        url = item.get("href", "")
        if not is_valid_http_url(url):
            continue
        results.append(
            JobLink(
                title=item.get("title", ""),
                url=url,
                snippet=item.get("body", ""),
                source_query=query,
                source=get_domain(url),
            )
        )

    if not results:
        warning = f"DuckDuckGo search returned 0 valid links for query {query!r}"
        logger.warning(warning)
        return [], warning

    return results, None


_DUCKDUCKGO_CHILD_SCRIPT = r"""
import json
import sys
import warnings

payload = json.loads(sys.stdin.read())
query = payload["query"]
max_results = payload["max_results"]

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS
    except ImportError:
        print("ddgs / duckduckgo-search not installed", file=sys.stderr)
        raise SystemExit(2)

try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        with DDGS() as ddgs:
            items = list(ddgs.text(query, max_results=max_results))
    print(json.dumps(items, ensure_ascii=False))
except Exception as exc:
    print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit(1)
"""


def search_jobs_by_query(query: str, max_results: int = 5) -> list[JobLink]:
    """Execute a single DuckDuckGo text search and return JobLink results.

    Invalid URLs (non-http, empty host) are silently dropped.
    Search failures are logged and return an empty list — they never propagate.
    """
    results, _ = search_jobs_by_query_with_warning(query, max_results=max_results)
    return results


def search_job_links_with_warnings(
    queries: list[str], max_results_per_query: int = 5
) -> tuple[list[JobLink], list[str]]:
    """Run multiple searches and return deduplicated links plus warnings."""
    seen_urls: set[str] = set()
    all_links: list[JobLink] = []
    warning_messages: list[str] = []

    for query in queries:
        links, warning = search_jobs_by_query_with_warning(query, max_results=max_results_per_query)
        if warning:
            warning_messages.append(warning)
        for link in links:
            normalized = link.url.rstrip("/")
            if normalized not in seen_urls:
                seen_urls.add(normalized)
                all_links.append(link)

    return all_links, warning_messages


def search_job_links(
    queries: list[str], max_results_per_query: int = 5
) -> list[JobLink]:
    """Run searches for multiple queries and return deduplicated results.

    Deduplication key is the URL with trailing slash normalised — two URLs
    that differ only in trailing slash are treated as identical.
    """
    links, _ = search_job_links_with_warnings(queries, max_results_per_query=max_results_per_query)
    return links
