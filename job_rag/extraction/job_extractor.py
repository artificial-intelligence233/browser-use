"""Rule-based MVP job extraction from page text."""

from __future__ import annotations

import re

from job_rag.crawler.url_utils import make_job_id, source_name_from_url
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


def extract_job_posting(page: PageContent) -> JobPosting:
    """Extract structured job posting from page content."""
    if page.status != "success" or not page.visible_text:
        return _invalid_job(page, page.error or "page crawl failed")

    text = page.visible_text
    lines = _lines(text)
    title = _extract_title(lines, page.title)
    company = _extract_label_value(lines, FIELD_LABELS["company"])
    location = _extract_label_value(lines, FIELD_LABELS["location"])
    salary = _extract_label_value(lines, FIELD_LABELS["salary"])
    job_type = _extract_label_value(lines, FIELD_LABELS["job_type"])
    education_required = _extract_label_value(lines, FIELD_LABELS["education_required"])
    experience_required = _extract_label_value(lines, FIELD_LABELS["experience_required"])

    responsibilities = _find_section(lines, SECTION_ALIASES["responsibilities"])
    requirements = _find_section(lines, SECTION_ALIASES["requirements"])
    skill_section = _find_section(lines, SECTION_ALIASES["skills"])
    skills = _extract_skills(text, skill_section)

    job = JobPosting(
        job_id=make_job_id(page.url, title, company),
        url=page.url,
        source=source_name_from_url(page.url),
        title=title,
        company=company,
        location=location,
        salary=salary,
        job_type=job_type,
        education_required=education_required,
        experience_required=experience_required,
        responsibilities=responsibilities,
        requirements=requirements,
        skills=skills,
        raw_text=text,
    )
    normalize_job(job)
    job.extraction_confidence = estimate_extraction_confidence(job)
    job.is_valid, job.validation_errors = validate_job_posting(job)
    if job.extraction_confidence < 0.45 and "low confidence extraction" not in job.validation_errors:
        job.validation_errors.append("low confidence extraction")
    return job


def extract_job_postings(pages: list[PageContent]) -> list[JobPosting]:
    """Extract structured postings from multiple pages."""
    return [extract_job_posting(page) for page in pages]
