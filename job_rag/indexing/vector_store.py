"""Local JSON vector store fallback for demo and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from job_rag.config import OUTPUTS_DIR, VECTOR_INDEX_FILENAME
from job_rag.indexing.embedder import cosine_similarity, embed_text
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


def index_jobs(jobs: list[JobPosting], index_path: str | Path | None = None) -> Path:
    """Write job documents and metadata to a local JSON vector store."""
    path = Path(index_path) if index_path else _default_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for job in jobs:
        document = build_job_document(job)
        records.append(
            {
                "job_id": job.job_id,
                "document": document,
                "embedding": embed_text(document),
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


def search_jobs(
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
    query_embedding = embed_text(query)
    results: list[dict[str, Any]] = []
    for record in records:
        metadata = record.get("metadata", {})
        if not _passes_filters(metadata, filters):
            continue
        score = cosine_similarity(query_embedding, record.get("embedding", {}))
        results.append(
            {
                "job_id": record.get("job_id"),
                "score": score,
                "metadata": metadata,
                "job": record.get("job"),
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[:top_k]

