"""Small token-vector fallback used by the MVP local vector store."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from job_rag.config import EMBEDDING_PROVIDER
from job_rag.indexing.interfaces import Embedding


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "we",
    "with",
    "you",
    "your",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]*", (text or "").lower())
    return [token for token in tokens if token not in STOPWORDS and len(token) > 1]


def embed_text(text: str) -> dict[str, float]:
    counts = Counter(tokenize(text))
    if not counts:
        return {}
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {token: value / norm for token, value in counts.items()}


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    score = sum(value * right.get(token, 0.0) for token, value in left.items())
    return round(float(score), 4)


class LocalTokenEmbeddingProvider:
    """Dependency-free sparse token embedding provider used as fallback."""

    name = "local"

    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        return [embed_text(text) for text in texts]

    def embed_query(self, text: str) -> Embedding:
        return embed_text(text)


def get_embedding_provider(provider: str | None = None, options: dict[str, Any] | None = None) -> LocalTokenEmbeddingProvider:
    """Return the configured embedding provider.

    The formal provider interface is in place now; external providers such as
    OpenAI can be added later without changing callers. Until then, unsupported
    provider names intentionally fall back to the local deterministic provider.
    """
    provider_name = (provider or EMBEDDING_PROVIDER or "local").lower()
    _ = options
    if provider_name in {"local", "fallback", "token", "token_overlap"}:
        return LocalTokenEmbeddingProvider()
    return LocalTokenEmbeddingProvider()


def embed_texts(texts: list[str], provider: str | None = None) -> list[Embedding]:
    """Embed multiple texts through the configured provider interface."""
    return get_embedding_provider(provider).embed_documents(texts)
