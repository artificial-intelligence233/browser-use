"""Validation helpers for extracted job postings."""

from __future__ import annotations

from job_rag.schemas import JobPosting


def validate_job_posting(job: JobPosting) -> tuple[bool, list[str]]:
    """Validate required fields and return validation errors."""
    errors: list[str] = []
    if not job.url:
        errors.append("missing url")
    if not job.title:
        errors.append("missing title")
    if not job.raw_text:
        errors.append("missing raw_text")
    if not job.responsibilities and not job.requirements:
        errors.append("missing responsibilities and requirements")
    return len(errors) == 0, errors


def estimate_extraction_confidence(job: JobPosting) -> float:
    """Estimate extraction confidence based on field completeness."""
    score = 0.0
    if job.title:
        score += 0.25
    if job.company:
        score += 0.12
    if job.location or job.city:
        score += 0.10
    if job.salary:
        score += 0.05
    if job.responsibilities:
        score += 0.18
    if job.requirements:
        score += 0.18
    if job.skills:
        score += 0.12
    return round(min(score, 1.0), 2)

