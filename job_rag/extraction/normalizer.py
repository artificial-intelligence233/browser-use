"""Normalize and deduplicate extracted job postings."""

from __future__ import annotations

import re

from job_rag.crawler.url_utils import normalize_url
from job_rag.schemas import JobPosting


SKILL_CANONICAL = {
    "py": "Python",
    "python": "Python",
    "pytorch": "PyTorch",
    "torch": "PyTorch",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "llm": "LLM",
    "large language model": "LLM",
    "large language models": "LLM",
    "rag": "RAG",
    "retrieval augmented generation": "RAG",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "react": "React",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "playwright": "Playwright",
    "browser use": "Browser Use",
    "browser-use": "Browser Use",
    "selenium": "Selenium",
    "vector db": "Vector DB",
    "vector database": "Vector DB",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "sql": "SQL",
    "nlp": "NLP",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
}


def normalize_city(location: str | None) -> str | None:
    if not location:
        return None
    lower = location.lower()
    city_aliases = {
        "beijing": "Beijing",
        "shanghai": "Shanghai",
        "hangzhou": "Hangzhou",
        "shenzhen": "Shenzhen",
        "guangzhou": "Guangzhou",
        "remote": "Remote",
        "hybrid": "Hybrid",
    }
    for key, value in city_aliases.items():
        if key in lower:
            return value
    return location.strip()


def normalize_salary(salary: str | None) -> dict[str, float | str | None]:
    if not salary:
        return {"salary_min": None, "salary_max": None, "salary_unit": None}

    text = salary.lower().replace(",", "")
    unit = None
    if "day" in text or "/d" in text:
        unit = "day"
    elif "month" in text or "/m" in text:
        unit = "month"
    elif "year" in text or "/y" in text or "annual" in text:
        unit = "year"
    elif "hour" in text or "/h" in text:
        unit = "hour"

    numbers = [float(match) for match in re.findall(r"\d+(?:\.\d+)?", text)]
    if not numbers:
        return {"salary_min": None, "salary_max": None, "salary_unit": unit}

    multiplier = 1000 if re.search(r"\d\s*k\b", text) else 1
    salary_min = min(numbers[:2]) * multiplier
    salary_max = max(numbers[:2]) * multiplier if len(numbers) >= 2 else salary_min
    return {
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_unit": unit,
    }


def normalize_skills(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for skill in skills or []:
        clean = re.sub(r"\s+", " ", skill.strip())
        if not clean:
            continue
        canonical = SKILL_CANONICAL.get(clean.lower(), clean)
        key = canonical.lower()
        if key not in seen:
            seen.add(key)
            normalized.append(canonical)
    return normalized


def normalize_job(job: JobPosting) -> JobPosting:
    job.city = normalize_city(job.location)
    salary = normalize_salary(job.salary)
    job.salary_min = salary["salary_min"]  # type: ignore[assignment]
    job.salary_max = salary["salary_max"]  # type: ignore[assignment]
    job.salary_unit = salary["salary_unit"]  # type: ignore[assignment]
    job.skills = normalize_skills(job.skills)
    return job


def deduplicate_jobs(jobs: list[JobPosting]) -> list[JobPosting]:
    """Deduplicate by URL first, then company/title/city."""
    seen: set[str] = set()
    unique: list[JobPosting] = []
    for job in jobs:
        normalized = normalize_job(job)
        key = normalize_url(normalized.url)
        if not key:
            key = "|".join(
                (normalized.company or "").lower(),
            )
        fallback = "|".join(
            [
                (normalized.company or "").lower(),
                (normalized.title or "").lower(),
                (normalized.city or normalized.location or "").lower(),
            ]
        )
        dedupe_key = key or fallback
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        unique.append(normalized)
    return unique

