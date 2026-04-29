"""Pydantic models for resume parsing and job search results.

These models serve as the stable wire format between the six course-project
modules.  Every field has a default (empty string or empty list) so that
partial parses never break downstream consumers.

Key models:
- ResumeProfile: the core structured resume (output of parse step)
- JobLink: a single search result pointing to a job listing
- FinalResult: the top-level output written to final_result.json
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BasicInfo(BaseModel):
    """Candidate identity and contact details."""

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    phone: str = ""
    email: str = ""
    city: str = ""
    age: str = ""
    gender: str = ""


class Education(BaseModel):
    """A single education entry (school → degree → date range)."""

    model_config = ConfigDict(extra="forbid")

    school: str = ""
    degree: str = ""
    major: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""


class Skills(BaseModel):
    """Four-category skill taxonomy used by both LLM and rule parsers.

    The split into programming_languages / frameworks / tools / professional_skills
    lets the query generator pick representative keywords per category.
    """

    model_config = ConfigDict(extra="forbid")

    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    professional_skills: list[str] = Field(default_factory=list)


class Project(BaseModel):
    """A project entry from the resume — name, tech stack, and contributions."""

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class Internship(BaseModel):
    """An internship / work-experience entry."""

    model_config = ConfigDict(extra="forbid")

    company: str = ""
    position: str = ""
    start_date: str = ""
    end_date: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class JobIntention(BaseModel):
    """Candidate's stated or inferred job preference.

    target_position and target_city drive search-query generation; if absent
    they are inferred from skills / basic_info by the parser.
    """

    model_config = ConfigDict(extra="forbid")

    target_position: str = ""
    target_city: str = ""
    expected_salary: str = ""
    industry: str = ""


class ResumeProfile(BaseModel):
    """Stable structured resume — the single source of truth for downstream modules.

    Every downstream consumer (RAG, resume optimiser, browser-use scraper) reads
    this structure.  Field stability is critical: renaming or removing a field
    breaks the pipeline for other team members.
    """

    model_config = ConfigDict(extra="forbid")

    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    education: list[Education] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    projects: list[Project] = Field(default_factory=list)
    internships: list[Internship] = Field(default_factory=list)
    job_intention: JobIntention = Field(default_factory=JobIntention)
    keywords: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)


class JobLink(BaseModel):
    """A single search-result entry pointing to a job listing HTML page.

    url is the payload — the browser-use module will later scrape these pages.
    source_query records which search query produced this result (for debugging).
    """

    model_config = ConfigDict(extra="forbid")

    title: str = ""
    url: str = ""
    snippet: str = ""
    source_query: str = ""
    source: str = ""


class FinalMetadata(BaseModel):
    """Execution metadata — records how the pipeline ran so results are auditable.

    parser_type is either 'llm' or 'rule' — downstream consumers can decide
    whether to trust LLM-extracted fields or treat them as best-effort.
    task_id / created_at / output_file make repeated runs traceable and avoid
    confusing one run's output with another.
    """

    model_config = ConfigDict(extra="forbid")

    task_id: str = ""
    created_at: str = ""
    input_file: str = ""
    output_file: str = ""
    parser_type: str = "rule"
    total_queries: int = 0
    total_links: int = 0
    warnings: list[str] = Field(default_factory=list)


class FinalResult(BaseModel):
    """Top-level output written to final_result.json.

    Contains everything downstream modules need:
    - resume_profile → RAG / resume optimiser
    - job_links      → browser-use page scraper
    - metadata       → audit trail
    """

    model_config = ConfigDict(extra="forbid")

    resume_profile: ResumeProfile = Field(default_factory=ResumeProfile)
    search_queries: list[str] = Field(default_factory=list)
    job_links: list[JobLink] = Field(default_factory=list)
    metadata: FinalMetadata = Field(default_factory=FinalMetadata)


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    """Convenience wrapper — delegates to Pydantic's model_dump()."""
    return model.model_dump()
