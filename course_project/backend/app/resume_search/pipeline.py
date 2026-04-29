"""Main pipeline orchestrator: extract → parse → generate queries → search → save.

This is the primary entry point called by both the CLI and FastAPI layers.
It implements a six-stage linear pipeline with one branch point:

    extract_text()
         │
         ▼
    use_llm=True? ──yes──▶ parse_resume_with_llm()
         │                        │
         │                    on error: fallback
         │                        │
         ▼                        ▼
    parse_resume_with_rules() ◀──┘
         │
         ▼
    generate_search_queries()
         │
         ▼
    search_job_links()
         │
         ▼
    Save FinalResult JSON (if output_path set)

The LLM → rule fallback is transparent: the caller sees the same FinalResult
structure regardless of which parser ran.  parser_type in metadata records
which path was taken.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from course_project.backend.app.resume_search.config import settings
from course_project.backend.app.resume_search.extract_text import extract_text
from course_project.backend.app.resume_search.llm_parser import parse_resume_with_llm
from course_project.backend.app.resume_search.query_generator import generate_search_queries
from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules
from course_project.backend.app.resume_search.schema import FinalMetadata, FinalResult, ResumeProfile
from course_project.backend.app.resume_search.search_api import search_job_links_with_warnings
from course_project.backend.app.resume_search.utils import save_json

logger = logging.getLogger(__name__)


def run_resume_search_pipeline(
    file_path: str | Path,
    use_llm: bool = True,
    max_queries: int | None = None,
    max_results_per_query: int | None = None,
    output_path: str | Path | None = None,
    task_id: str | None = None,
) -> FinalResult:
    """Run the complete resume-to-job-links pipeline.

    Args:
        file_path: Path to a .pdf / .docx / .txt resume file.
        use_llm: If True, attempt LLM parsing first (falls back to rules on error).
        max_queries: Max search queries to generate (None → env default).
        max_results_per_query: Max links per query (None → env default).
        output_path: If set, write FinalResult JSON to this path.
        task_id: Optional caller-provided run id. If omitted, the pipeline
            creates one so repeated runs can be traced independently.

    Returns:
        FinalResult with resume_profile, search_queries, job_links, and metadata.

    Raises:
        FileNotFoundError: Resume file does not exist.
        ValueError: Resume file type is unsupported or extracted text is empty.
    """
    task_id = task_id or uuid4().hex[:12]
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")
    resolved_output_path = str(Path(output_path).resolve()) if output_path is not None else ""

    max_queries = max_queries if max_queries is not None else settings.DEFAULT_MAX_QUERIES
    max_results_per_query = (
        max_results_per_query
        if max_results_per_query is not None
        else settings.DEFAULT_MAX_RESULTS_PER_QUERY
    )

    # Stage 1: Extract plain text from the resume file
    text = extract_text(file_path)

    # Stage 2: Parse into structured ResumeProfile
    # LLM path is best-effort: any failure falls through to rule parser
    parser_type: str = "rule"
    warning_messages: list[str] = []
    profile: ResumeProfile

    if use_llm:
        try:
            profile = parse_resume_with_llm(text)
            parser_type = "llm"
        except Exception as exc:
            warning = f"LLM parsing failed ({type(exc).__name__}: {exc}); falling back to rule parser"
            logger.warning(warning)
            warning_messages.append(warning)
            profile = parse_resume_with_rules(text)
    else:
        profile = parse_resume_with_rules(text)

    # Stage 3: Generate search queries from the structured profile
    queries = generate_search_queries(profile, max_queries=max_queries)

    # Stage 4: Execute searches and collect deduplicated job links
    job_links, search_warnings = search_job_links_with_warnings(
        queries,
        max_results_per_query=max_results_per_query,
    )
    warning_messages.extend(search_warnings)

    # Stage 5: Assemble final result with execution metadata
    metadata = FinalMetadata(
        task_id=task_id,
        created_at=created_at,
        input_file=str(Path(file_path).resolve()),
        output_file=resolved_output_path,
        parser_type=parser_type,
        total_queries=len(queries),
        total_links=len(job_links),
        warnings=warning_messages,
    )

    result = FinalResult(
        resume_profile=profile,
        search_queries=queries,
        job_links=job_links,
        metadata=metadata,
    )

    # Stage 6: Persist to disk if output path specified
    if output_path is not None:
        save_json(result.model_dump(), output_path)

    return result
