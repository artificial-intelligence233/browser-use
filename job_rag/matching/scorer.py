"""Scoring and ranking logic for resume-job matches."""

from __future__ import annotations

import re
from typing import Any

from job_rag.extraction.normalizer import normalize_skills
from job_rag.matching.reason_generator import (
    generate_match_reasons,
    generate_mismatch_reasons,
    generate_resume_edit_focus,
)
from job_rag.schemas import JobMatchResult, JobPosting


def compute_skill_match(resume_skills: list[str], job_skills: list[str]) -> dict[str, Any]:
    resume_norm = normalize_skills(resume_skills)
    job_norm = normalize_skills(job_skills)
    resume_keys = {skill.lower(): skill for skill in resume_norm}
    matched = [skill for skill in job_norm if skill.lower() in resume_keys]
    missing = [skill for skill in job_norm if skill.lower() not in resume_keys]
    ratio = len(matched) / len(job_norm) if job_norm else 0.0
    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "skill_match": round(ratio, 4),
        "skill_match_ratio": round(ratio, 4),
    }


def _role_match(resume_profile: dict[str, Any], job: JobPosting) -> float:
    if not job.title:
        return 0.0
    title = job.title.lower()
    for role in resume_profile.get("target_roles") or []:
        role_lower = role.lower()
        if role_lower in title or title in role_lower:
            return 1.0
        role_tokens = {token for token in role_lower.split() if len(token) > 2}
        title_tokens = {token for token in title.split() if len(token) > 2}
        if role_tokens and title_tokens and role_tokens & title_tokens:
            return 0.5
    return 0.0


def _city_match(resume_profile: dict[str, Any], job: JobPosting) -> float:
    preferred = [city.lower() for city in resume_profile.get("target_cities") or []]
    if not preferred or not job.city:
        return 0.0
    return 1.0 if job.city.lower() in preferred else 0.0


def _norm_text(value: str | None) -> str:
    return (value or "").lower()


def _tokenize_text(value: str | None) -> set[str]:
    return {token.lower() for token in re.findall(r"[\w\-\+\.#]+", value or "") if len(token) >= 2}


def _job_comparison_text(job: JobPosting) -> str:
    parts = [
        job.title,
        job.company,
        job.location,
        job.city,
        job.job_type,
        job.education_required,
        job.experience_required,
        " ".join(job.responsibilities),
        " ".join(job.requirements),
        " ".join(job.skills),
    ]
    return " ".join(part for part in parts if part)


def _project_relevance(resume_profile: dict[str, Any], job: JobPosting) -> tuple[float, list[str]]:
    job_text = _job_comparison_text(job)
    job_lower = job_text.lower()
    job_tokens = _tokenize_text(job_text)
    relevant_projects: list[str] = []
    best_score = 0.0

    for project in resume_profile.get("projects") or []:
        name = str(project.get("name") or "").strip()
        description = str(project.get("description") or "").strip()
        tech_stack = [str(item).strip() for item in project.get("tech_stack") or [] if str(item).strip()]
        project_terms = [term for term in [name, description, *tech_stack] if term]
        if not project_terms:
            continue

        tech_matches = [term for term in tech_stack if term.lower() in job_lower]
        project_tokens = set()
        for term in project_terms:
            project_tokens.update(_tokenize_text(term))
        token_overlap = len(project_tokens & job_tokens) / len(project_tokens) if project_tokens else 0.0

        score = min(1.0, 0.2 * len(tech_matches) + 0.8 * token_overlap)
        if score >= 0.2 and name:
            relevant_projects.append(name)
        best_score = max(best_score, score)

    return round(best_score, 4), relevant_projects[:3]


def _education_or_experience_match(resume_profile: dict[str, Any], job: JobPosting) -> float:
    if not job.education_required and not job.experience_required:
        return 0.5

    score_parts: list[float] = []
    education_text = " ".join(
        str(value)
        for item in resume_profile.get("education") or []
        for value in item.values()
        if value
    ).lower()
    if job.education_required:
        required = job.education_required.lower()
        degree_aliases = {
            "本科": ["本科", "bachelor"],
            "硕士": ["硕士", "master"],
            "博士": ["博士", "phd", "doctor"],
            "大专": ["大专", "college"],
        }
        matched = any(alias in required and alias in education_text for aliases in degree_aliases.values() for alias in aliases)
        score_parts.append(1.0 if matched else (0.6 if education_text else 0.0))

    if job.experience_required:
        internships = resume_profile.get("internships") or []
        required = job.experience_required.lower()
        if any(word in required for word in ("不限", "无需", "no experience", "entry", "intern")):
            score_parts.append(1.0)
        else:
            score_parts.append(0.8 if internships else 0.4)

    return round(sum(score_parts) / len(score_parts), 4) if score_parts else 0.5


def _job_type_or_salary_match(resume_profile: dict[str, Any], job: JobPosting) -> float:
    score_parts: list[float] = []
    roles = " ".join(resume_profile.get("target_roles") or []).lower()
    job_type = _norm_text(job.job_type)
    title = _norm_text(job.title)
    if job_type:
        if job_type in roles or job_type in title:
            score_parts.append(1.0)
        elif "实习" in job_type and ("实习" in roles or "intern" in roles):
            score_parts.append(1.0)
        elif "intern" in job_type and ("实习" in roles or "intern" in roles):
            score_parts.append(1.0)
        else:
            score_parts.append(0.5)

    salary_expectation = _norm_text(resume_profile.get("salary_expectation"))
    if salary_expectation:
        if "面议" in salary_expectation or "negotiable" in salary_expectation:
            score_parts.append(0.8)
        elif job.salary and salary_expectation in _norm_text(job.salary):
            score_parts.append(1.0)
        else:
            score_parts.append(0.5)

    return round(sum(score_parts) / len(score_parts), 4) if score_parts else 0.5


def score_job_match(
    resume_profile: dict[str, Any],
    job: JobPosting,
    retrieval_score: float,
    rank: int = 0,
) -> JobMatchResult:
    skill_detail = compute_skill_match(resume_profile.get("skills") or [], job.skills)
    role_score = _role_match(resume_profile, job)
    city_score = _city_match(resume_profile, job)
    semantic_similarity = round(min(max(retrieval_score, 0.0), 1.0), 4)
    project_relevance, relevant_projects = _project_relevance(resume_profile, job)
    education_or_experience_match = _education_or_experience_match(resume_profile, job)
    job_type_or_salary_match = _job_type_or_salary_match(resume_profile, job)
    score_detail = {
        **skill_detail,
        "semantic_similarity": semantic_similarity,
        "project_relevance": project_relevance,
        "relevant_projects": relevant_projects,
        "role_score": role_score,
        "city_match": city_score,
        "city_score": city_score,
        "education_or_experience_match": education_or_experience_match,
        "job_type_or_salary_match": job_type_or_salary_match,
        "retrieval_score": retrieval_score,
    }
    weighted_score = (
        0.35 * semantic_similarity
        + 0.25 * skill_detail["skill_match"]
        + 0.20 * project_relevance
        + 0.10 * city_score
        + 0.05 * education_or_experience_match
        + 0.05 * job_type_or_salary_match
    )
    match_score = int(round(max(0.0, min(weighted_score * 100, 100.0))))
    return JobMatchResult(
        job_id=job.job_id,
        rank=rank,
        title=job.title,
        company=job.company,
        url=job.url,
        match_score=match_score,
        retrieval_score=retrieval_score,
        matched_skills=skill_detail["matched_skills"],
        missing_skills=skill_detail["missing_skills"],
        match_reasons=generate_match_reasons(resume_profile, job, score_detail),
        mismatch_reasons=generate_mismatch_reasons(resume_profile, job, score_detail),
        resume_edit_focus=generate_resume_edit_focus(resume_profile, job, score_detail),
        score_detail=score_detail,
    )


def rank_jobs(resume_profile: dict[str, Any], retrieved_jobs: list[dict[str, Any]]) -> list[JobMatchResult]:
    """Score and rank retrieved jobs."""
    scored: list[JobMatchResult] = []
    for item in retrieved_jobs:
        job_data = item.get("job")
        if not job_data:
            continue
        job = JobPosting.from_dict(job_data)
        scored.append(score_job_match(resume_profile, job, float(item.get("score") or 0.0)))
    scored.sort(key=lambda result: result.match_score, reverse=True)
    for index, result in enumerate(scored, start=1):
        result.rank = index
    return scored
