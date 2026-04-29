"""FastAPI entry point for Module 1: 简历信息提取 + 搜索候选岗位网页.

Provides three business endpoints plus a root health/docs endpoint.
All endpoints delegate to the resume_search subpackage — this file is
a thin HTTP adapter with upload handling.

Start with:
    uvicorn course_project.backend.main:app --reload

Then visit http://127.0.0.1:8000/docs for interactive Swagger docs.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from course_project.backend.app.resume_search.pipeline import run_resume_search_pipeline
from course_project.backend.app.resume_search.rule_parser import parse_resume_with_rules
from course_project.backend.app.resume_search.schema import FinalResult, ResumeProfile
from course_project.backend.app.resume_search.query_generator import generate_search_queries
from course_project.backend.app.resume_search.search_api import search_job_links

app = FastAPI(title="简历信息提取 + 岗位搜索", version="1.0.0")

# Uploads directory relative to this file: course_project/uploads/
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root() -> dict:
    """Return module description and available endpoints for discovery."""
    return {
        "module": "简历信息提取 + 搜索候选岗位网页",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload_resume": "上传简历文件，运行完整 pipeline（提取→解析→搜索→输出）",
            "POST /parse_resume": "仅上传并解析简历，不执行搜索",
            "POST /search_jobs": "传入 ResumeProfile JSON，生成 queries 并搜索岗位链接",
        },
    }


@app.post("/upload_resume", response_model=FinalResult)
async def upload_resume(
    file: UploadFile = File(...),
    use_llm: bool = Form(True),
    max_queries: int = Form(6),
    max_results_per_query: int = Form(5),
) -> FinalResult:
    """Upload a resume file (.pdf / .docx / .txt) and run the full pipeline.

    Returns FinalResult with resume_profile, search_queries, job_links, and metadata.
    This is the primary integration endpoint for downstream modules.
    """
    _validate_file(file)
    saved = await _save_upload(file)
    try:
        return run_resume_search_pipeline(
            file_path=saved,
            use_llm=use_llm,
            max_queries=max_queries,
            max_results_per_query=max_results_per_query,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/parse_resume", response_model=ResumeProfile)
async def parse_resume(
    file: UploadFile = File(...),
    use_llm: bool = Form(True),
) -> ResumeProfile:
    """Upload a resume file and return only the parsed ResumeProfile.

    Does NOT execute job search — useful when the caller only needs structured
    resume data (e.g., for RAG or resume optimisation modules).
    """
    _validate_file(file)
    saved = await _save_upload(file)
    from course_project.backend.app.resume_search.extract_text import extract_text

    text = extract_text(saved)
    if use_llm:
        try:
            from course_project.backend.app.resume_search.llm_parser import parse_resume_with_llm

            return parse_resume_with_llm(text)
        except Exception:
            pass  # fall through to rule parser
    return parse_resume_with_rules(text)


@app.post("/search_jobs")
async def search_jobs(profile: ResumeProfile, max_queries: int = 6, max_results_per_query: int = 5) -> dict:
    """Accept a pre-parsed ResumeProfile, generate queries, and return job links.

    This endpoint lets other modules feed in a manually constructed or modified
    ResumeProfile without going through file upload.
    """
    queries = generate_search_queries(profile, max_queries=max_queries)
    links = search_job_links(queries, max_results_per_query=max_results_per_query)
    return {
        "search_queries": queries,
        "job_links": [link.model_dump() for link in links],
    }


# ------------------------------------------------------------------ helpers


def _validate_file(file: UploadFile) -> None:
    """Reject uploads with missing filenames or unsupported extensions."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".txt"):
        raise HTTPException(status_code=400, detail=f"Unsupported format: {suffix}. Use .pdf, .docx, or .txt")


async def _save_upload(file: UploadFile) -> Path:
    """Write an UploadFile to disk under course_project/uploads/.

    The saved filename is prefixed with timestamp + short UUID so repeated
    uploads named "resume.pdf" do not overwrite each other.
    """
    assert file.filename is not None
    original_name = Path(file.filename).name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_name = f"{timestamp}_{uuid4().hex[:8]}_{original_name}"
    dest = UPLOAD_DIR / unique_name
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return dest
