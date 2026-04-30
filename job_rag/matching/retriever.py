"""Build resume queries and retrieve candidate jobs."""

from __future__ import annotations

from typing import Any

from job_rag.config import DEFAULT_TOP_K
from job_rag.indexing.vector_store import search_jobs


def build_resume_query(resume_profile: dict[str, Any]) -> str:
    """Convert structured resume profile into a retrieval query."""
    parts: list[str] = []
    parts.extend(resume_profile.get("target_roles") or [])
    parts.extend(resume_profile.get("skills") or [])
    for project in resume_profile.get("projects") or []:
        parts.append(project.get("name") or "")
        parts.append(project.get("description") or "")
        parts.extend(project.get("tech_stack") or [])
    for internship in resume_profile.get("internships") or []:
        parts.append(internship.get("title") or "")
        parts.append(internship.get("description") or "")
    return " ".join(part for part in parts if part)


def retrieve_jobs(
    resume_profile: dict[str, Any],
    top_k: int = DEFAULT_TOP_K,
    filters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve candidate jobs from the local vector store."""
    query = build_resume_query(resume_profile)
    return search_jobs(query, top_k=top_k, filters=filters)

