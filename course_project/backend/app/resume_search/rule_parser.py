"""Rule-based resume parser — a deterministic fallback when no LLM is available.

This parser uses regex for contact fields and keyword matching for skills and
education.  It is intentionally coarse: the goal is stability and zero-cost
execution, not perfect accuracy.

Key design decisions:
- Position inference uses an ordered SKILL_TO_POSITION table: the first
  matching skill cluster wins.  Order matters — we check more specific roles
  (大模型应用工程师) before general ones (AI算法工程师).
- inferred_fields records the rationale for every inferred value so that
  downstream consumers can audit the decision.
- All skill lists are exhaustive closed sets; unknown skills are silently
  ignored.  This keeps the output stable across resume formats.
"""

from __future__ import annotations

import re

from course_project.backend.app.resume_search.schema import (
    BasicInfo,
    Education,
    Internship,
    JobIntention,
    Project,
    ResumeProfile,
    Skills,
)

# --- Closed sets for keyword matching ---
# These are the only values the rule parser can produce.  Unknown terms
# are dropped — this is by design, not a bug.

CITIES = [
    "北京", "上海", "杭州", "深圳", "广州", "南京", "苏州", "成都",
    "武汉", "西安", "重庆", "天津", "宁波", "厦门", "长沙", "郑州",
    "青岛", "合肥", "无锡", "东莞",
]

DEGREES = ["专科", "本科", "硕士", "博士", "研究生"]

PROGRAMMING_LANGUAGES = [
    "Python", "Java", "C\\+\\+", "C", "JavaScript", "TypeScript",
    "Go", "Rust", "SQL", "MATLAB",
]

FRAMEWORKS = [
    "Spring Boot", "Django", "Flask", "FastAPI", "Vue", "React",
    "PyTorch", "TensorFlow", "LangChain", "LlamaIndex",
]

TOOLS = [
    "Git", "Docker", "Linux", "MySQL", "Redis", "MongoDB",
    "PostgreSQL", "Kubernetes", "Elasticsearch", "Nginx",
]

PROFESSIONAL_SKILLS = [
    "机器学习", "深度学习", "自然语言处理", "计算机视觉",
    "后端开发", "前端开发", "数据分析", "推荐系统",
    "RAG", "Agent", "大模型", "LLM",
]

# Position inference table — evaluated top-to-bottom, first match wins.
# Order: more specific roles first so that candidates with RAG/LLM skills
# are classified as 大模型应用工程师 rather than the broader AI算法工程师.
SKILL_TO_POSITION = [
    ({"RAG", "Agent", "LangChain", "LlamaIndex", "大模型", "LLM", "自然语言处理"}, "大模型应用工程师"),
    ({"PyTorch", "TensorFlow", "机器学习", "深度学习", "计算机视觉"}, "AI算法工程师"),
    ({"Spring Boot", "Java", "MySQL", "Redis"}, "后端开发工程师"),
    ({"Vue", "React", "JavaScript", "TypeScript"}, "前端开发工程师"),
]


def parse_resume_with_rules(resume_text: str) -> ResumeProfile:
    """Extract structured resume fields using regex and keyword matching.

    Returns a ResumeProfile with every field populated to its default (empty
    string / list) when no match is found.  This function never raises — the
    output is always a valid ResumeProfile.
    """
    inferred: list[str] = []

    # --- BasicInfo: regex extraction for email, phone; keyword for city ---
    email = _extract_first(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", resume_text)
    phone = _extract_first(r"1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}", resume_text)

    city = ""
    for c in CITIES:
        if c in resume_text:
            city = c
            break

    name = _guess_name(resume_text)

    basic_info = BasicInfo(name=name, phone=phone, email=email, city=city)

    # --- Education: any line containing a school keyword ---
    education: list[Education] = []
    for line in resume_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if _has_school_keyword(line):
            degree = ""
            for d in DEGREES:
                if d in line:
                    degree = d
                    break
            education.append(Education(school=line, degree=degree))

    # --- Skills: closed-set keyword matching across four categories ---
    skills = Skills(
        programming_languages=_match_any(resume_text, PROGRAMMING_LANGUAGES),
        frameworks=_match_any(resume_text, FRAMEWORKS),
        tools=_match_any(resume_text, TOOLS),
        professional_skills=_match_any(resume_text, PROFESSIONAL_SKILLS),
    )

    # --- Projects: blocks starting with "项目" (captures up to 6 following lines) ---
    projects: list[Project] = []
    lines = resume_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "项目" in line and len(line) < 80:
            name = line
            desc_lines: list[str] = []
            i += 1
            while i < len(lines) and "项目" not in lines[i]:
                desc_lines.append(lines[i].strip())
                i += 1
                if len(desc_lines) >= 6:
                    break
            projects.append(Project(name=name, description="; ".join(desc_lines[:3])))
        else:
            i += 1

    # --- Internships: blocks starting with "实习" ---
    internships: list[Internship] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "实习" in line and len(line) < 80:
            internships.append(Internship(company=line, position=line))
            i += 1
        else:
            i += 1

    # --- JobIntention: infer from skills, use parsed city ---
    target_position = _infer_position(skills, inferred)
    target_city = city or "全国"

    # Keywords feed into search query generation
    keywords: list[str] = []
    keywords.extend(skills.programming_languages)
    keywords.extend(skills.frameworks)
    keywords.extend(skills.tools)
    keywords.extend(skills.professional_skills)
    if target_position:
        keywords.append(target_position)
    if target_city != "全国":
        keywords.append(target_city)
    keywords = list(dict.fromkeys(keywords))  # dedup preserving order

    job_intention = JobIntention(target_position=target_position, target_city=target_city)

    return ResumeProfile(
        basic_info=basic_info,
        education=education,
        skills=skills,
        projects=projects,
        internships=internships,
        job_intention=job_intention,
        keywords=keywords,
        inferred_fields=inferred,
    )


# ------------------------------------------------------------------ helpers


def _extract_first(pattern: str, text: str) -> str:
    """Return the first regex match, with spaces and hyphens stripped."""
    m = re.search(pattern, text)
    return m.group(0).replace(" ", "").replace("-", "") if m else ""


def _has_school_keyword(line: str) -> bool:
    """Return True if *line* contains a Chinese or English academic institution keyword."""
    kw = ["大学", "学院", "研究所", "Institute", "University", "College"]
    return any(k in line for k in kw)


def _guess_name(text: str) -> str:
    """Guess the candidate's name: first line that is 1-4 pure Chinese characters."""
    for line in text.splitlines():
        line = line.strip()
        if 1 <= len(line) <= 4 and re.fullmatch(r"[一-鿿·]+", line):
            return line
    return ""


def _match_any(text: str, candidates: list[str]) -> list[str]:
    """Return candidate keywords that appear in *text* (case-insensitive)."""
    found: list[str] = []
    for c in candidates:
        literal = c.replace("\\", "")  # strip regex escapes for literal matching
        if literal.lower() in text.lower():
            if literal not in found:
                found.append(literal)
    return found


def _infer_position(skills: Skills, inferred: list[str]) -> str:
    """Map detected skills to a target position using SKILL_TO_POSITION.

    First match wins — the table is ordered from most-specific to least-specific.
    Falls back to "软件开发工程师" when no skill cluster matches.
    """
    all_skills = set(
        skills.programming_languages
        + skills.frameworks
        + skills.tools
        + skills.professional_skills
    )
    for trigger_set, pos in SKILL_TO_POSITION:
        matched = trigger_set & all_skills
        if matched:
            inferred.append(f"根据技能 {matched} 推断岗位为 {pos}")
            return pos
    inferred.append("无明确技能信号，默认软件开发工程师")
    return "软件开发工程师"
