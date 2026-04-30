"""Scoring and ranking logic for resume-job matches."""

from __future__ import annotations

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


def score_job_match(
    resume_profile: dict[str, Any],
    job: JobPosting,
    retrieval_score: float,
    rank: int = 0,
) -> JobMatchResult:
    skill_detail = compute_skill_match(resume_profile.get("skills") or [], job.skills)
    role_score = _role_match(resume_profile, job)
    city_score = _city_match(resume_profile, job)
    raw = (
        45 * skill_detail["skill_match_ratio"]
        + 30 * min(max(retrieval_score, 0.0), 1.0)
        + 15 * role_score
        + 10 * city_score
    )
    match_score = int(round(max(0.0, min(raw, 100.0))))
    score_detail = {
        **skill_detail,
        "role_score": role_score,
        "city_score": city_score,
        "retrieval_score": retrieval_score,
    }
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
