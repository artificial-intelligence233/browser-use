"""Run the Job RAG MVP demo end to end."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from job_rag.config import EXAMPLES_DIR, OUTPUTS_DIR
from job_rag.crawler.browser_use_runner import crawl_pages
from job_rag.extraction.job_extractor import extract_job_postings
from job_rag.extraction.normalizer import deduplicate_jobs
from job_rag.indexing.vector_store import index_jobs
from job_rag.matching.retriever import retrieve_jobs
from job_rag.matching.scorer import rank_jobs


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


async def run() -> dict[str, Path]:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    resume_profile = read_json(EXAMPLES_DIR / "sample_resume_profile.json")
    candidate_payload = read_json(EXAMPLES_DIR / "sample_candidate_urls.json")
    urls = [item["url"] for item in candidate_payload.get("candidate_urls", []) if item.get("url")]

    pages = await crawl_pages(urls)
    page_contents_path = OUTPUTS_DIR / "page_contents.json"
    write_json(page_contents_path, [page.to_dict() for page in pages])

    postings = extract_job_postings(pages)
    job_postings_path = OUTPUTS_DIR / "job_postings.json"
    write_json(job_postings_path, [job.to_dict() for job in postings])

    clean_jobs = deduplicate_jobs([job for job in postings if job.is_valid])
    clean_jobs_path = OUTPUTS_DIR / "clean_job_postings.json"
    write_json(clean_jobs_path, [job.to_dict() for job in clean_jobs])

    vector_index_path = index_jobs(clean_jobs)

    retrieved = retrieve_jobs(resume_profile, top_k=5)
    retrieved_jobs_path = OUTPUTS_DIR / "retrieved_jobs.json"
    write_json(retrieved_jobs_path, retrieved)

    recommendations = rank_jobs(resume_profile, retrieved)
    recommendations_path = OUTPUTS_DIR / "job_recommendations.json"
    write_json(recommendations_path, [item.to_dict() for item in recommendations])

    return {
        "page_contents": page_contents_path,
        "job_postings": job_postings_path,
        "clean_job_postings": clean_jobs_path,
        "vector_index": vector_index_path,
        "retrieved_jobs": retrieved_jobs_path,
        "job_recommendations": recommendations_path,
    }


def main() -> None:
    outputs = asyncio.run(run())
    print("Job RAG demo completed.")
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
