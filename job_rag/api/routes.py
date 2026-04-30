"""API-style functions and optional FastAPI routes."""

from __future__ import annotations

import asyncio
from typing import Any

from job_rag.crawler.browser_use_runner import crawl_pages
from job_rag.extraction.job_extractor import extract_job_postings
from job_rag.extraction.normalizer import deduplicate_jobs
from job_rag.indexing.vector_store import index_jobs
from job_rag.matching.retriever import retrieve_jobs
from job_rag.matching.scorer import rank_jobs


async def crawl_jobs(payload: dict[str, Any]) -> dict[str, Any]:
    """Crawl candidate URLs and return extracted jobs."""
    run_id = payload.get("run_id")
    candidates = payload.get("candidate_urls") or []
    urls = [item.get("url") for item in candidates if item.get("url")]
    pages = await crawl_pages(urls)
    postings = extract_job_postings(pages)
    clean_jobs = deduplicate_jobs([job for job in postings if job.is_valid])
    failed_urls = [
        {"url": page.url, "error": page.error}
        for page in pages
        if page.status == "failed"
    ]
    return {
        "run_id": run_id,
        "status": "success" if clean_jobs else "failed",
        "jobs": [job.to_dict() for job in clean_jobs],
        "failed_urls": failed_urls,
    }


def recommend_jobs(payload: dict[str, Any]) -> dict[str, Any]:
    """Recommend indexed jobs for a structured resume profile."""
    run_id = payload.get("run_id")
    resume_profile = payload.get("resume_profile") or {}
    top_k = int(payload.get("top_k") or 5)
    retrieved = retrieve_jobs(resume_profile, top_k=top_k)
    ranked = rank_jobs(resume_profile, retrieved)
    return {
        "run_id": run_id,
        "recommendations": [item.to_dict() for item in ranked],
    }


def crawl_and_index_jobs(payload: dict[str, Any]) -> dict[str, Any]:
    """Synchronous helper for demos or simple backends."""
    result = asyncio.run(crawl_jobs(payload))
    jobs = result.get("jobs") or []
    if jobs:
        from job_rag.schemas import JobPosting

        index_jobs([JobPosting.from_dict(job) for job in jobs])
    return result


try:
    from fastapi import FastAPI

    app = FastAPI(title="Job RAG API")

    @app.post("/crawl_jobs")
    async def crawl_jobs_route(payload: dict[str, Any]) -> dict[str, Any]:
        return await crawl_jobs(payload)

    @app.post("/recommend_jobs")
    async def recommend_jobs_route(payload: dict[str, Any]) -> dict[str, Any]:
        return recommend_jobs(payload)

except ImportError:
    app = None

