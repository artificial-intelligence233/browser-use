"""Chunking helpers for future long job postings."""

from __future__ import annotations


def chunk_text(text: str, max_chars: int = 2000) -> list[str]:
    """Split text into simple paragraph chunks."""
    if not text:
        return []
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)
            current = paragraph[:max_chars]
    if current:
        chunks.append(current)
    return chunks

