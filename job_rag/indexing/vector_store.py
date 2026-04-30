"""Vector store facade with a local JSON fallback backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from job_rag.config import OUTPUTS_DIR, VECTOR_BACKEND, VECTOR_INDEX_FILENAME
from job_rag.indexing.embedder import cosine_similarity, get_embedding_provider
from job_rag.indexing.interfaces import Embedding, EmbeddingProvider
from job_rag.schemas import JobPosting


def build_job_document(job: JobPosting) -> str:
    """Build embedding-ready document text from structured job posting."""
    parts = [
        job.title or "",
        job.company or "",
        job.location or "",
        job.job_type or "",
        "Skills: " + ", ".join(job.skills),
        "Responsibilities: " + " ".join(job.responsibilities),
        "Requirements: " + " ".join(job.requirements),
        job.raw_text or "",
    ]
    return "\n".join(part for part in parts if part.strip())


def _default_index_path() -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR / VECTOR_INDEX_FILENAME


def _passes_filters(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        if expected in (None, "", []):
            continue
        actual = metadata.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _score_embedding(query_embedding: Embedding, document_embedding: Embedding) -> float:
    if isinstance(query_embedding, dict) and isinstance(document_embedding, dict):
        return cosine_similarity(query_embedding, document_embedding)
    # Dense-vector providers will plug in here later; keep a deterministic
    # no-match score instead of guessing incompatible vector formats.
    return 0.0


class LocalJsonVectorStore:
    """JSON-backed vector store implementing the formal backend interface."""

    name = "local"

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()

    def index_jobs(self, jobs: list[JobPosting], index_path: str | Path | None = None) -> Path:
        """Write job documents and metadata to a local JSON vector store."""
        path = Path(index_path) if index_path else _default_index_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        documents = [build_job_document(job) for job in jobs]
        embeddings = self.embedding_provider.embed_documents(documents)
        records: list[dict[str, Any]] = []
        for job, document, embedding in zip(jobs, documents, embeddings):
            records.append(
                {
                    "job_id": job.job_id,
                    "document": document,
                    "embedding": embedding,
                    "embedding_provider": self.embedding_provider.name,
                    "vector_backend": self.name,
                    "metadata": {
                        "job_id": job.job_id,
                        "title": job.title,
                        "company": job.company,
                        "url": job.url,
                        "city": job.city,
                        "location": job.location,
                        "job_type": job.job_type,
                        "skills": job.skills,
                    },
                    "job": job.to_dict(),
                }
            )
        path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def search_jobs(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        index_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Search similar jobs from the local vector store."""
        path = Path(index_path) if index_path else _default_index_path()
        if not path.exists():
            return []
        records = json.loads(path.read_text(encoding="utf-8"))
        query_embedding = self.embedding_provider.embed_query(query)
        results: list[dict[str, Any]] = []
        for record in records:
            metadata = record.get("metadata", {})
            if not _passes_filters(metadata, filters):
                continue
            score = _score_embedding(query_embedding, record.get("embedding", {}))
            results.append(
                {
                    "job_id": record.get("job_id"),
                    "score": score,
                    "retrieval_score": score,
                    "metadata": metadata,
                    "job": record.get("job"),
                    "backend": record.get("vector_backend", self.name),
                    "embedding_provider": record.get("embedding_provider", self.embedding_provider.name),
                }
            )
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]


def get_vector_store_backend(backend: str | None = None) -> LocalJsonVectorStore:
    """Return a vector store backend by name.

    Chroma/OpenAI integration will be added behind this factory later. For now,
    unknown backend names fall back to the deterministic local JSON store.
    """
    backend_name = (backend or VECTOR_BACKEND or "local").lower()
    if backend_name in {"local", "json", "fallback"}:
        return LocalJsonVectorStore()
    return LocalJsonVectorStore()


def index_jobs(jobs: list[JobPosting], index_path: str | Path | None = None) -> Path:
    """Index jobs through the configured vector store backend."""
    return get_vector_store_backend().index_jobs(jobs, index_path=index_path)


def search_jobs(
    query: str,
    top_k: int = 10,
    filters: dict[str, Any] | None = None,
    index_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Search jobs through the configured vector store backend."""
    return get_vector_store_backend().search_jobs(query, top_k=top_k, filters=filters, index_path=index_path)
