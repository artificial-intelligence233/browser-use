"""Rule-based MVP job extraction from page text."""

from __future__ import annotations

import re
from typing import Any, Callable

from job_rag.crawler.url_utils import make_job_id, source_name_from_url
from job_rag.extraction.llm_extractor import (
    LLMExtractionUnavailable,
    extract_job_fields_with_llm,
    is_llm_extraction_configured,
)
from job_rag.extraction.normalizer import normalize_job, normalize_skills
from job_rag.extraction.validators import estimate_extraction_confidence, validate_job_posting
from job_rag.schemas import JobPosting, PageContent


KNOWN_SKILL_PATTERNS = [
    "Python",
    "PyTorch",
    "TensorFlow",
    "Machine Learning",
    "LLM",
    "RAG",
    "Vector DB",
    "Vector Database",
    "FastAPI",
    "Django",
    "Flask",
    "React",
    "TypeScript",
    "JavaScript",
    "Playwright",
    "Browser Use",
    "browser-use",
    "Selenium",
    "SQL",
    "PostgreSQL",
    "Docker",
    "Kubernetes",
    "NLP",
    "LangChain",
    "OpenAI",
]

FIELD_LABELS = {
    "title": ("job title", "title", "position", "role"),
    "company": ("company", "employer"),
    "location": ("location", "city", "work location"),
    "salary": ("salary", "compensation", "pay"),
    "job_type": ("job type", "employment type", "type"),
    "education_required": ("education", "degree"),
    "experience_required": ("experience", "years"),
}

SECTION_ALIASES = {
    "responsibilities": (
        "responsibilities",
        "job responsibilities",
        "what you will do",
        "duties",
    ),
    "requirements": (
        "requirements",
        "qualifications",
        "what we are looking for",
        "preferred qualifications",
    ),
    "skills": ("skills", "tech stack", "technical skills"),
}


def _lines(text: str) -> list[str]:
    return [line.strip(" -*\u2022") for line in (text or "").splitlines() if line.strip(" -*\u2022")]


def _extract_label_value(lines: list[str], labels: tuple[str, ...]) -> str | None:
    for line in lines:
        lower = line.lower()
        for label in labels:
            if lower.startswith(label + ":") or lower.startswith(label + " -"):
                return line.split(":", 1)[-1].split(" - ", 1)[-1].strip()
            pattern = rf"^{re.escape(label)}\s+(.+)$"
            match = re.match(pattern, lower)
            if match and len(line) <= 120:
                return line[match.start(1) :].strip()
    return None


def _extract_title(lines: list[str], page_title: str | None) -> str | None:
    labeled = _extract_label_value(lines, FIELD_LABELS["title"])
    if labeled:
        return labeled
    for line in lines[:8]:
        lower = line.lower()
        if any(word in lower for word in ("intern", "engineer", "developer", "scientist", "analyst", "manager")):
            return line
    return page_title


def _find_section(lines: list[str], aliases: tuple[str, ...]) -> list[str]:
    start = None
    headings = {alias.lower() for group in SECTION_ALIASES.values() for alias in group}
    for index, line in enumerate(lines):
        clean = line.strip(":").lower()
        if clean in aliases or any(clean.startswith(alias + ":") for alias in aliases):
            start = index + 1
            tail = line.split(":", 1)
            section_lines = [tail[1].strip()] if len(tail) == 2 and tail[1].strip() else []
            break
    else:
        return []

    for line in lines[start:]:
        clean = line.strip(":").lower()
        if clean in headings:
            break
        if len(line) > 2:
            section_lines.append(line)
    return section_lines[:12]


def _extract_skills(text: str, section_lines: list[str]) -> list[str]:
    found: list[str] = []
    lower_text = text.lower()
    for skill in KNOWN_SKILL_PATTERNS:
        if re.search(rf"\b{re.escape(skill.lower())}\b", lower_text):
            found.append(skill)

    for line in section_lines:
        for part in re.split(r"[,;/|]", line):
            clean = part.strip(" .")
            if 1 < len(clean) <= 40:
                found.append(clean)
    return normalize_skills(found)


def _invalid_job(page: PageContent, reason: str) -> JobPosting:
    job = JobPosting(
        job_id=make_job_id(page.url),
        url=page.url,
        source=source_name_from_url(page.url),
        raw_text=page.visible_text,
        is_valid=False,
        validation_errors=[reason],
    )
    return job


def _finalize_job(job: JobPosting) -> JobPosting:
    normalize_job(job)
    job.extraction_confidence = estimate_extraction_confidence(job)
    job.is_valid, job.validation_errors = validate_job_posting(job)
    if job.extraction_confidence < 0.45 and "low confidence extraction" not in job.validation_errors:
        job.validation_errors.append("low confidence extraction")
    return job


def _build_job_from_fields(page: PageContent, fields: dict[str, Any], raw_text: str) -> JobPosting:
    title = fields.get("title")
    company = fields.get("company")
    job = JobPosting(
        job_id=make_job_id(page.url, title, company),
        url=page.url,
        source=source_name_from_url(page.url),
        title=title,
        company=company,
        location=fields.get("location"),
        salary=fields.get("salary"),
        job_type=fields.get("job_type"),
        education_required=fields.get("education_required"),
        experience_required=fields.get("experience_required"),
        responsibilities=fields.get("responsibilities") or [],
        requirements=fields.get("requirements") or [],
        skills=fields.get("skills") or [],
        raw_text=raw_text,
    )
    return _finalize_job(job)


def _extract_job_posting_by_rules(page: PageContent) -> JobPosting:
    text = page.visible_text or ""
    lines = _lines(text)
    responsibilities = _find_section(lines, SECTION_ALIASES["responsibilities"])
    requirements = _find_section(lines, SECTION_ALIASES["requirements"])
    skill_section = _find_section(lines, SECTION_ALIASES["skills"])
    fields = {
        "title": _extract_title(lines, page.title),
        "company": _extract_label_value(lines, FIELD_LABELS["company"]),
        "location": _extract_label_value(lines, FIELD_LABELS["location"]),
        "salary": _extract_label_value(lines, FIELD_LABELS["salary"]),
        "job_type": _extract_label_value(lines, FIELD_LABELS["job_type"]),
        "education_required": _extract_label_value(lines, FIELD_LABELS["education_required"]),
        "experience_required": _extract_label_value(lines, FIELD_LABELS["experience_required"]),
        "responsibilities": responsibilities,
        "requirements": requirements,
        "skills": _extract_skills(text, skill_section),
    }
    return _build_job_from_fields(page, fields, text)


def _should_try_llm_fallback(job: JobPosting, llm_extractor: Callable[[str], dict[str, Any]] | None) -> bool:
    needs_fallback = (not job.is_valid) or job.extraction_confidence < 0.55
    if llm_extractor is not None:
        return needs_fallback
    if not is_llm_extraction_configured():
        return False
    return needs_fallback


def _try_llm_fallback(
    page: PageContent,
    rule_job: JobPosting,
    llm_extractor: Callable[[str], dict[str, Any]] | None,
) -> JobPosting:
    if not _should_try_llm_fallback(rule_job, llm_extractor):
        return rule_job
    text = page.visible_text or ""
    try:
        fields = llm_extractor(text) if llm_extractor else extract_job_fields_with_llm(text)
        llm_job = _build_job_from_fields(page, fields, text)
        if llm_job.is_valid or llm_job.extraction_confidence > rule_job.extraction_confidence:
            return llm_job
    except LLMExtractionUnavailable as exc:
        if "llm extraction unavailable" not in rule_job.validation_errors:
            rule_job.validation_errors.append(f"llm extraction unavailable: {exc}")
    except Exception as exc:
        if "llm extraction failed" not in rule_job.validation_errors:
            rule_job.validation_errors.append(f"llm extraction failed: {exc}")
    return rule_job


def extract_job_posting(
    page: PageContent,
    llm_extractor: Callable[[str], dict[str, Any]] | None = None,
) -> JobPosting:
    """Extract structured job posting from page content."""
    if page.status != "success" or not page.visible_text:
        return _invalid_job(page, page.error or "page crawl failed")

    rule_job = _extract_job_posting_by_rules(page)
    return _try_llm_fallback(page, rule_job, llm_extractor)


def extract_job_postings(
    pages: list[PageContent],
    llm_extractor: Callable[[str], dict[str, Any]] | None = None,
) -> list[JobPosting]:
    """Extract structured postings from multiple pages."""
    return [extract_job_posting(page, llm_extractor=llm_extractor) for page in pages]
