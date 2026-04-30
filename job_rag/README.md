# Job RAG

Part 3 module for Browser Use based job page crawling, job information
extraction, retrieval, matching, and recommendation explanations.

## Scope

This module receives candidate job URLs and a structured resume profile. It
crawls public job pages or local demo HTML files, extracts job description,
company, location, salary, responsibilities, requirements, and skills, stores
the cleaned jobs in a local retrieval index, and returns match scores,
matching reasons, mismatch reasons, and resume edit focus.

## Boundaries

This module does not extract structured resume data, generate search queries,
call a search API, build the frontend UI, rewrite the final resume text, or
orchestrate the whole application pipeline.

Compliance rules:

- Only process public pages or local demo HTML.
- Do not bypass login, captcha, paywalls, access limits, or anti-bot systems.
- Do not perform high-frequency or commercial scraping.
- Do not invent education, work experience, projects, awards, or skills.
- Use resume content only for job matching and resume improvement guidance.

## MVP Flow

```text
candidate_urls.json
-> crawl pages
-> page_contents.json
-> extract job_postings.json
-> clean_job_postings.json
-> local vector index
-> retrieved_jobs.json
-> job_recommendations.json
```

Run the demo:

```bash
python job_rag/examples/run_demo.py
```

## Optional Browser Use

The default demo uses local HTML fixtures and safe HTTP fallback so it works
without browser credentials, paid APIs, or a live browser. To try the optional
Browser Use crawler for public `http/https` job pages, install `browser-use`
in an isolated environment and enable it explicitly:

```bash
set JOB_RAG_ENABLE_BROWSER_USE=1
python job_rag/examples/run_demo.py
```

Useful optional settings:

```text
JOB_RAG_BROWSER_USE_HEADLESS=1
JOB_RAG_BROWSER_USE_TIMEOUT_SECONDS=25
JOB_RAG_BROWSER_USE_WORK_DIR=.browseruse
PLAYWRIGHT_BROWSERS_PATH=D:\agent_part3
```

If Browser Use is unavailable or fails to open a page, the crawler falls back
to the existing local/HTTP reader and preserves structured error information.

## Retrieval Backend Interface

The retrieval layer exposes stable interfaces for future embedding and vector
database upgrades:

```text
EmbeddingProvider -> embed_documents / embed_query
VectorStoreBackend -> index_jobs / search_jobs
```

The current default is still dependency-free:

```text
JOB_RAG_EMBEDDING_PROVIDER=local
JOB_RAG_VECTOR_BACKEND=local
```

To use the local persistent Chroma backend:

```text
JOB_RAG_VECTOR_BACKEND=chroma
JOB_RAG_CHROMA_DIR=job_rag/examples/outputs/chroma_index
JOB_RAG_CHROMA_COLLECTION=job_postings
```

To use an OpenAI-compatible embedding service, configure only local environment
variables. Do not commit real service URLs, model names, or API keys:

```text
JOB_RAG_EMBEDDING_PROVIDER=openai_compatible
JOB_RAG_EMBEDDING_BASE_URL=<set locally>
JOB_RAG_EMBEDDING_MODEL=<set locally>
JOB_RAG_EMBEDDING_API_KEY=<set locally>
```
