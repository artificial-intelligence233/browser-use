"""Shared interfaces for embedding providers and vector store backends."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, TypeAlias

from job_rag.schemas import JobPosting


Embedding: TypeAlias = dict[str, float] | list[float]


class EmbeddingProvider(Protocol):
    """Convert retrieval text into vectors."""

    name: str

    def embed_documents(self, texts: list[str]) -> list[Embedding]:
        """Embed indexable documents."""

    def embed_query(self, text: str) -> Embedding:
        """Embed one retrieval query."""


class VectorStoreBackend(Protocol):
    """Store and retrieve job vectors without exposing backend details."""

    name: str

    def index_jobs(self, jobs: list[JobPosting], index_path: str | Path | None = None) -> Path:
        """Index structured jobs and return the persistence path."""

    def search_jobs(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        index_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Return retrieved jobs in the module's stable result format."""
