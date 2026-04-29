"""Generate Bing-style search queries from a structured resume profile.

Queries are composed from three components:
1. city       — from job_intention.target_city or basic_info.city, else "全国"
2. position   — from job_intention.target_position, else "软件开发工程师"
3. keywords   — up to 5 skill terms from the four skill categories

We produce a fixed set of templates that cover major Chinese recruitment
platforms (BOSS直聘, 猎聘, 拉勾, 前程无忧) plus generic web search.
The site: prefix tells DuckDuckGo to return results from a specific domain.
"""

from __future__ import annotations

from course_project.backend.app.resume_search.schema import ResumeProfile


def generate_search_queries(profile: ResumeProfile, max_queries: int = 6) -> list[str]:
    """Produce a deduplicated list of job-search query strings.

    Each query is a space-joined template of city + position + keywords.
    Queries are deduplicated and truncated to max_queries.
    """
    position = profile.job_intention.target_position or "软件开发工程师"
    city = profile.job_intention.target_city or profile.basic_info.city or "全国"

    keywords: list[str] = _pick_keywords(profile, max_count=5)
    kw_str = " ".join(keywords) if keywords else ""

    # Build templates — with and without keyword enrichment
    templates: list[str] = []
    if kw_str:
        templates = [
            f"{city} {position} {kw_str} 招聘",
            f"{city} {position} {kw_str} JD",
            f"site:zhipin.com {city} {position} {kw_str}",
            f"site:liepin.com {city} {position} {kw_str}",
            f"site:lagou.com {city} {position} {kw_str}",
            f"site:jobs.51job.com {city} {position} {kw_str}",
        ]
    else:
        templates = [
            f"{city} {position} 招聘",
            f"{city} {position} JD",
            f"site:zhipin.com {city} {position}",
            f"site:liepin.com {city} {position}",
            f"site:lagou.com {city} {position}",
            f"site:jobs.51job.com {city} {position}",
        ]

    # Deduplicate while preserving template order
    seen: set[str] = set()
    queries: list[str] = []
    for q in templates:
        if q not in seen:
            seen.add(q)
            queries.append(q)
        if len(queries) >= max_queries:
            break

    return queries


def _pick_keywords(profile: ResumeProfile, max_count: int = 5) -> list[str]:
    """Select up to *max_count* skill terms from all four skill categories.

    Categories are concatenated in priority order: programming_languages first
    (most discriminative), then frameworks, tools, and professional_skills.
    """
    skills = profile.skills
    pool = (
        skills.programming_languages
        + skills.frameworks
        + skills.tools
        + skills.professional_skills
    )
    seen: set[str] = set()
    result: list[str] = []
    for kw in pool:
        if kw not in seen:
            seen.add(kw)
            result.append(kw)
        if len(result) >= max_count:
            break
    return result
