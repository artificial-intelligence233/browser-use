"""Vector store facade with a local JSON fallback backend."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from job_rag.config import CHROMA_COLLECTION_NAME, CHROMA_INDEX_DIR, OUTPUTS_DIR, VECTOR_BACKEND, VECTOR_INDEX_FILENAME
from job_rag.indexing.embedder import cosine_similarity, get_embedding_provider
from job_rag.indexing.interfaces import Embedding, EmbeddingProvider
from job_rag.schemas import JobPosting


CHROMA_HASH_DIMENSIONS = 384


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


def _embedding_to_dense_vector(embedding: Embedding, dimensions: int = CHROMA_HASH_DIMENSIONS) -> list[float]:
    """Convert sparse local embeddings into dense vectors accepted by Chroma."""
    if isinstance(embedding, list):
        return [float(value) for value in embedding]
    vector = [0.0] * dimensions
    for token, value in embedding.items():
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        bucket = int(token_hash[:8], 16) % dimensions
        vector[bucket] += float(value)
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 8) for value in vector]


def _metadata_from_job(job: JobPosting) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "title": job.title,
        "company": job.company,
        "url": job.url,
        "city": job.city,
        "location": job.location,
        "job_type": job.job_type,
        "skills": job.skills,
    }


def _metadata_for_chroma(job: JobPosting) -> dict[str, str | int | float | bool]:
    metadata: dict[str, str | int | float | bool] = {}
    for key, value in _metadata_from_job(job).items():
        if value is None:
            continue
        if isinstance(value, list):
            metadata[key] = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        else:
            metadata[key] = str(value)
    return metadata


def _distance_to_score(distance: float | int | None) -> float:
    if distance is None:
        return 0.0
    score = 1.0 - float(distance)
    return round(max(0.0, min(1.0, score)), 4)


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
                    "metadata": _metadata_from_job(job),
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


class ChromaVectorStoreBackend:
    """Persistent Chroma vector store backend for job postings."""

    name = "chroma"

    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        persist_dir: str | Path | None = None,
        collection_name: str = CHROMA_COLLECTION_NAME,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.persist_dir = Path(persist_dir) if persist_dir else CHROMA_INDEX_DIR
        self.collection_name = collection_name

    def index_jobs(self, jobs: list[JobPosting], index_path: str | Path | None = None) -> Path:
        """Persist job vectors and metadata into a local Chroma collection."""
        path = Path(index_path) if index_path else self.persist_dir
        path.mkdir(parents=True, exist_ok=True)
        client = self._client(path)
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass
        collection = client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        documents = [build_job_document(job) for job in jobs]
        embeddings = [_embedding_to_dense_vector(embedding) for embedding in self.embedding_provider.embed_documents(documents)]
        if jobs:
            collection.upsert(
                ids=[job.job_id for job in jobs],
                documents=documents,
                embeddings=embeddings,
                metadatas=[_metadata_for_chroma(job) for job in jobs],
            )
        self._write_sidecar_jobs(path, jobs)
        return path

    def search_jobs(
        self,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
        index_path: str | Path | None = None,
    ) -> list[dict[str, Any]]:
        """Search persisted Chroma vectors and return the stable module result shape."""
        path = Path(index_path) if index_path else self.persist_dir
        if not path.exists():
            return []
        client = self._client(path)
        try:
            collection = client.get_collection(name=self.collection_name, embedding_function=None)
        except Exception:
            return []
        query_embedding = _embedding_to_dense_vector(self.embedding_provider.embed_query(query))
        n_results = max(top_k * 5, top_k, 1)
        response = collection.query(query_embeddings=[query_embedding], n_results=n_results)
        ids = response.get("ids", [[]])[0]
        distances = response.get("distances", [[]])[0]
        sidecar_jobs = self._read_sidecar_jobs(path)
        results: list[dict[str, Any]] = []
        for job_id, distance in zip(ids, distances):
            job_data = sidecar_jobs.get(job_id)
            if not job_data:
                continue
            job = JobPosting.from_dict(job_data)
            metadata = _metadata_from_job(job)
            if not _passes_filters(metadata, filters):
                continue
            score = _distance_to_score(distance)
            results.append(
                {
                    "job_id": job_id,
                    "score": score,
                    "retrieval_score": score,
                    "metadata": metadata,
                    "job": job.to_dict(),
                    "backend": self.name,
                    "embedding_provider": self.embedding_provider.name,
                }
            )
            if len(results) >= top_k:
                break
        return results

    def _client(self, path: Path) -> Any:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("chromadb is required for JOB_RAG_VECTOR_BACKEND=chroma") from exc
        return chromadb.PersistentClient(path=str(path))

    def _sidecar_path(self, path: Path) -> Path:
        return path / "jobs.json"

    def _write_sidecar_jobs(self, path: Path, jobs: list[JobPosting]) -> None:
        sidecar = {job.job_id: job.to_dict() for job in jobs}
        self._sidecar_path(path).write_text(json.dumps(sidecar, indent=2, ensure_ascii=False), encoding="utf-8")

    def _read_sidecar_jobs(self, path: Path) -> dict[str, dict[str, Any]]:
        sidecar_path = self._sidecar_path(path)
        if not sidecar_path.exists():
            return {}
        return json.loads(sidecar_path.read_text(encoding="utf-8"))


def get_vector_store_backend(backend: str | None = None) -> LocalJsonVectorStore | ChromaVectorStoreBackend:
    """Return a vector store backend by name.

    Unknown backend names fall back to the deterministic local JSON store.
    """
    backend_name = (backend or VECTOR_BACKEND or "local").lower()
    if backend_name in {"local", "json", "fallback"}:
        return LocalJsonVectorStore()
    if backend_name in {"chroma", "chromadb"}:
        return ChromaVectorStoreBackend()
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
