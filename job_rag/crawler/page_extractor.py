"""Extract visible text from HTML and clean page text."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser

from job_rag.config import MAX_PAGE_TEXT_CHARS


class VisibleTextParser(HTMLParser):
    """Small HTML visible-text extractor based on the standard library."""

    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas", "template"}
    BLOCK_TAGS = {
        "article",
        "aside",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "header",
        "li",
        "main",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
        "ul",
        "ol",
    }

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
            title = clean_visible_text(" ".join(self._title_parts))
            self.title = title or None
        if tag in self.BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = unescape(data).strip()
        if not text:
            return
        if self._in_title:
            self._title_parts.append(text)
            return
        self._parts.append(text)

    def text(self) -> str:
        return clean_visible_text("\n".join(self._parts))


def html_to_visible_text(html: str) -> tuple[str, str | None]:
    parser = VisibleTextParser()
    parser.feed(html or "")
    return parser.text(), parser.title


def clean_visible_text(text: str) -> str:
    """Remove obvious repeated whitespace and simple navigation noise."""
    if not text:
        return ""

    normalized = text.replace("\r", "\n").replace("\t", " ")
    normalized = re.sub(r"[ \u00a0]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    lines: list[str] = []
    seen_short: set[str] = set()
    noisy = {
        "home",
        "login",
        "sign in",
        "register",
        "privacy policy",
        "terms",
        "cookie policy",
        "apply now",
        "share",
    }
    for raw_line in normalized.splitlines():
        line = raw_line.strip(" -|")
        if not line:
            continue
        lower = line.lower()
        if lower in noisy:
            continue
        if len(line) <= 24:
            if lower in seen_short:
                continue
            seen_short.add(lower)
        lines.append(line)

    return "\n".join(lines).strip()


def truncate_text(text: str, max_chars: int = MAX_PAGE_TEXT_CHARS) -> str:
    """Keep text within model context limits."""
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit("\n", 1)[0].strip()
