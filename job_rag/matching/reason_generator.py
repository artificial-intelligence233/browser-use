"""Generate grounded match explanations."""

from __future__ import annotations

from typing import Any

from job_rag.schemas import JobPosting


def generate_match_reasons(
    resume_profile: dict[str, Any],
    job: JobPosting,
    score_detail: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    matched = score_detail.get("matched_skills") or []
    if matched:
        reasons.append(
            "Resume skills overlap with the JD on: " + ", ".join(matched[:6]) + "."
        )
    target_roles = [role.lower() for role in resume_profile.get("target_roles") or []]
    if job.title and any(role in job.title.lower() or job.title.lower() in role for role in target_roles):
        reasons.append("The job title is aligned with the resume target roles.")
    target_cities = [city.lower() for city in resume_profile.get("target_cities") or []]
    if job.city and job.city.lower() in target_cities:
        reasons.append(f"The job city matches the preferred city: {job.city}.")
    if not reasons and job.requirements:
        reasons.append("The JD requirements are available for downstream resume comparison.")
    return reasons


def generate_mismatch_reasons(
    resume_profile: dict[str, Any],
    job: JobPosting,
    score_detail: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    missing = score_detail.get("missing_skills") or []
    if missing:
        reasons.append("The JD mentions skills not found in the resume: " + ", ".join(missing[:6]) + ".")
    target_cities = [city.lower() for city in resume_profile.get("target_cities") or []]
    if job.city and target_cities and job.city.lower() not in target_cities:
        reasons.append(f"The job city ({job.city}) is outside the preferred cities.")
    if not reasons:
        reasons.append("No major mismatch was found from the structured resume and JD fields.")
    return reasons


def generate_resume_edit_focus(
    resume_profile: dict[str, Any],
    job: JobPosting,
    score_detail: dict[str, Any],
) -> list[str]:
    focus: list[str] = []
    missing = score_detail.get("missing_skills") or []
    if missing:
        focus.append(
            "If truthful, add concrete project or experience evidence for: "
            + ", ".join(missing[:4])
            + "."
        )
    matched = score_detail.get("matched_skills") or []
    if matched:
        focus.append(
            "Make existing relevant experience easier to scan by foregrounding: "
            + ", ".join(matched[:4])
            + "."
        )
    if job.responsibilities:
        focus.append("Mirror the JD responsibility wording only where the resume has real supporting evidence.")
    return focus

