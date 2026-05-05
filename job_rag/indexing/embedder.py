"""Small token-vector fallback used by the MVP local vector store."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from job_rag.config import (
    EMBEDDING_API_ALLOW_FALLBACK,
    EMBEDDING_API_BASE_URL,
    EMBEDDING_API_KEY,
    EMBEDDING_API_MODEL,
    EMBEDDING_API_TIMEOUT_SECONDS,
    EMBEDDING_PROVIDER,
)
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


def cosine_similarity(left: Embedding, right: Embedding) -> float:
    """Return cosine similarity for sparse dict or dense list embeddings."""
    if not left or not right:
        return 0.0
    if isinstance(left, list) and isinstance(right, list):
        length = min(len(left), len(right))
        if length == 0:
            return 0.0
        dot_product = sum(float(left[index]) * float(right[index]) for index in range(length))
        left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
        right_norm = math.sqrt(sum(float(value) * float(value) for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return round(float(dot_product / (left_norm * right_norm)), 4)
    if not isinstance(left, dict) or not isinstance(right, dict):
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


class OpenAICompatibleEmbeddingProvider:
    """OpenAI-compatible embedding provider configured only through env vars."""

    name = "openai_compatible"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: int = EMBEDDING_API_TIMEOUT_SECONDS,
        allow_fallback: bool = EMBEDDING_API_ALLOW_FALLBACK,
    ) -> None:
        self.api_key = EMBEDDING_API_KEY if api_key is None else api_key
        self.base_url = EMBEDDING_API_BASE_URL if base_url is None else base_url
        self.model = EMBEDDING_API_MODEL if model is None else model
        self.timeout_seconds = timeout_seconds
        self.allow_fallback = allow_fallback
        self.fallback_provider = LocalTokenEmbeddingProvider()

    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        return self._embed(texts)

    def embed_query(self, text: str) -> Embedding:
        return self._embed([text])[0]

    def _embed(self, texts: list[str]) -> list[Embedding]:
        if not texts:
            return []
        if not self.api_key or not self.model:
            return self._fallback(texts)
        try:
            from openai import OpenAI

            client_options: dict[str, Any] = {"api_key": self.api_key, "timeout": self.timeout_seconds}
            if self.base_url:
                client_options["base_url"] = self.base_url
            client = OpenAI(**client_options)
            response = client.embeddings.create(model=self.model, input=texts)
            return [list(map(float, item.embedding)) for item in response.data]
        except Exception:
            if self.allow_fallback:
                return self._fallback(texts)
            raise

    def _fallback(self, texts: list[str]) -> list[Embedding]:
        return self.fallback_provider.embed_documents(texts)


def get_embedding_provider(
    provider: str | None = None,
    options: dict[str, Any] | None = None,
) -> LocalTokenEmbeddingProvider | OpenAICompatibleEmbeddingProvider:
    """Return the configured embedding provider.

    The API provider reads only generic environment variables. Real keys,
    model names, and service URLs must stay in the local runtime environment.
    """
    provider_name = (provider or EMBEDDING_PROVIDER or "local").lower()
    options = options or {}
    if provider_name in {"local", "fallback", "token", "token_overlap"}:
        return LocalTokenEmbeddingProvider()
    if provider_name in {"openai", "openai_compatible", "api", "remote"}:
        return OpenAICompatibleEmbeddingProvider(**options)
    return LocalTokenEmbeddingProvider()


def embed_texts(texts: list[str], provider: str | None = None) -> list[Embedding]:
    """Embed multiple texts through the configured provider interface."""
    return get_embedding_provider(provider).embed_documents(texts)
