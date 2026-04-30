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
        reasons.append("岗位要求与简历技能存在重合：" + "、".join(matched[:6]) + "。")
    relevant_projects = score_detail.get("relevant_projects") or []
    if relevant_projects:
        reasons.append("简历项目与岗位职责/要求相关：" + "、".join(relevant_projects[:3]) + "。")
    target_roles = [role.lower() for role in resume_profile.get("target_roles") or []]
    if job.title and any(role in job.title.lower() or job.title.lower() in role for role in target_roles):
        reasons.append(f"岗位名称“{job.title}”与候选人的目标岗位方向匹配。")
    target_cities = [city.lower() for city in resume_profile.get("target_cities") or []]
    if job.city and job.city.lower() in target_cities:
        reasons.append(f"岗位城市为{job.city}，符合候选人的目标城市。")
    if score_detail.get("semantic_similarity", 0.0) >= 0.5:
        reasons.append("简历查询与岗位文本的语义检索相似度较高。")
    if not reasons and job.requirements:
        reasons.append("岗位要求字段完整，可用于后续简历对比和优化。")
    return reasons


def generate_mismatch_reasons(
    resume_profile: dict[str, Any],
    job: JobPosting,
    score_detail: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    missing = score_detail.get("missing_skills") or []
    if missing:
        reasons.append("岗位提到这些技能，但当前简历资料中未体现：" + "、".join(missing[:6]) + "。")
    target_cities = [city.lower() for city in resume_profile.get("target_cities") or []]
    if job.city and target_cities and job.city.lower() not in target_cities:
        reasons.append(f"岗位城市为{job.city}，不在候选人的目标城市列表中。")
    if score_detail.get("project_relevance", 0.0) < 0.2 and resume_profile.get("projects"):
        reasons.append("当前简历项目与岗位职责/要求的直接关联度不高。")
    if score_detail.get("education_or_experience_match", 0.5) < 0.5:
        reasons.append("岗位的学历或经验要求与当前简历资料匹配度偏低。")
    if not reasons:
        reasons.append("基于结构化简历和岗位字段，未发现明显不匹配项。")
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
            "如果真实具备相关经历，可在简历中补充这些技能的项目或实践证据："
            + "、".join(missing[:4])
            + "。"
        )
    matched = score_detail.get("matched_skills") or []
    if matched:
        focus.append(
            "在技能和项目描述中优先突出已匹配能力："
            + "、".join(matched[:4])
            + "。"
        )
    relevant_projects = score_detail.get("relevant_projects") or []
    if relevant_projects:
        focus.append("强化相关项目的成果、技术栈和岗位职责对应关系：" + "、".join(relevant_projects[:3]) + "。")
    if job.responsibilities:
        focus.append("可参考岗位职责措辞调整简历表达，但只写已有真实经历和证据。")
    return focus
