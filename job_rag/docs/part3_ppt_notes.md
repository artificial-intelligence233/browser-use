# Part 3 PPT Notes

## Module Goal

Convert candidate job pages into structured, searchable, explainable job
recommendations based on a structured resume profile.

## Architecture

```mermaid
flowchart LR
    A[Candidate job URLs or local HTML] --> B[Crawl pages]
    B --> C[Extract visible text]
    C --> D[Extract JobPosting JSON]
    D --> E[Clean, normalize, deduplicate]
    E --> F[Build local vector index]
    G[ResumeProfile JSON] --> H[Build resume query]
    H --> I[Retrieve top-k jobs]
    F --> I
    I --> J[Score and rerank]
    J --> K[Match reasons, mismatch reasons, resume edit focus]
```

## Current MVP

- Uses local HTML job pages for stable demo input.
- Supports public HTTP/HTTPS pages through a conservative fallback crawler.
- Uses rule-based extraction as the no-LLM fallback.
- Uses a local JSON vector index based on token cosine similarity.
- Produces frontend/backend-ready JSON outputs.

## Demo Output Files

```text
job_rag/examples/outputs/page_contents.json
job_rag/examples/outputs/job_postings.json
job_rag/examples/outputs/clean_job_postings.json
job_rag/examples/outputs/retrieved_jobs.json
job_rag/examples/outputs/job_recommendations.json
```

