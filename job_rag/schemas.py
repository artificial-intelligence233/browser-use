"""Core data structures for the Job RAG module.

The MVP intentionally uses the Python standard library so the demo can run in a
fresh environment. These dataclasses can be migrated to Pydantic later without
changing the public field names.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


PageStatus = Literal["success", "failed"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class PageContent:
    url: str
    status: PageStatus
    title: str | None = None
    visible_text: str | None = None
    html: str | None = None
    screenshot_path: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PageContent":
        return cls(**{key: data.get(key) for key in cls.__dataclass_fields__})


@dataclass
class EducationItem:
    school: str | None = None
    degree: str | None = None
    major: str | None = None


@dataclass
class ProjectItem:
    name: str | None = None
    description: str | None = None
    tech_stack: list[str] = field(default_factory=list)


@dataclass
class ResumeProfile:
    name: str | None = None
    education: list[dict[str, Any]] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    projects: list[dict[str, Any]] = field(default_factory=list)
    internships: list[dict[str, Any]] = field(default_factory=list)
    target_roles: list[str] = field(default_factory=list)
    target_cities: list[str] = field(default_factory=list)
    salary_expectation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResumeProfile":
        allowed = cls.__dataclass_fields__
        return cls(**{key: data.get(key) for key in allowed})


@dataclass
class JobPosting:
    job_id: str
    url: str
    source: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    city: str | None = None
    salary: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_unit: str | None = None
    job_type: str | None = None
    education_required: str | None = None
    experience_required: str | None = None
    responsibilities: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    raw_text: str | None = None
    extraction_confidence: float = 0.0
    crawled_at: str = field(default_factory=utc_now_iso)
    is_valid: bool = True
    validation_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobPosting":
        allowed = cls.__dataclass_fields__
        values = {key: data.get(key) for key in allowed}
        for list_key in ("responsibilities", "requirements", "skills", "validation_errors"):
            values[list_key] = values.get(list_key) or []
        return cls(**values)


@dataclass
class JobMatchResult:
    job_id: str
    rank: int
    title: str | None
    company: str | None
    url: str
    match_score: int
    retrieval_score: float
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    match_reasons: list[str] = field(default_factory=list)
    mismatch_reasons: list[str] = field(default_factory=list)
    resume_edit_focus: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JobMatchResult":
        allowed = cls.__dataclass_fields__
        values = {key: data.get(key) for key in allowed}
        for list_key in ("matched_skills", "missing_skills", "match_reasons", "mismatch_reasons", "resume_edit_focus"):
            values[list_key] = values.get(list_key) or []
        return cls(**values)
