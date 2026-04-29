"""LLM-based resume parser using OpenAI-compatible API.

This is the primary parser.  It sends the full resume text to an LLM with a
structured prompt that constrains the output to JSON matching ResumeProfile.

Error handling contract:
- RuntimeError if OPENAI_API_KEY is missing (caller should fallback to rule parser)
- ValueError if the LLM returns non-JSON garbage

The pipeline in pipeline.py handles both cases transparently.
"""

from __future__ import annotations

import json

from openai import OpenAI

from course_project.backend.app.resume_search.config import settings
from course_project.backend.app.resume_search.schema import ResumeProfile
from course_project.backend.app.resume_search.utils import strip_json_markdown

# System prompt instructs the LLM to output ONLY valid JSON matching the
# ResumeProfile schema.  The example JSON structure serves as a few-shot
# template that keeps the model on-schema.
SYSTEM_PROMPT = """你是一个专业的简历信息抽取助手。请从下面的简历文本中抽取结构化信息，并严格按照指定 JSON 格式输出。

要求：
1. 只能输出 JSON，不要输出任何解释或说明文字；
2. 如果某个字段在简历中没有出现，填写空字符串 "" 或空数组 []；
3. 不要编造简历中没有的信息；
4. 技能要分类整理到 skills.programming_languages / frameworks / tools / professional_skills 中；
5. 项目经历要提取项目名称、技术栈、职责和成果；
6. 求职方向如果没有明确写出，可以根据专业、项目和技能合理推断，但必须把推断依据写入 inferred_fields 数组；
7. 输出 JSON 必须符合以下结构：
{
  "basic_info": {"name": "", "phone": "", "email": "", "city": "", "age": "", "gender": ""},
  "education": [{"school": "", "degree": "", "major": "", "start_date": "", "end_date": "", "gpa": ""}],
  "skills": {"programming_languages": [], "frameworks": [], "tools": [], "professional_skills": []},
  "projects": [{"name": "", "description": "", "technologies": [], "responsibilities": [], "achievements": []}],
  "internships": [{"company": "", "position": "", "start_date": "", "end_date": "", "responsibilities": [], "achievements": []}],
  "job_intention": {"target_position": "", "target_city": "", "expected_salary": "", "industry": ""},
  "keywords": [],
  "inferred_fields": []
}
"""


def parse_resume_with_llm(resume_text: str) -> ResumeProfile:
    """Call an OpenAI-compatible LLM to parse resume text into ResumeProfile.

    Uses temperature=0 for deterministic output.  Supports custom base_url
    (OPENAI_BASE_URL) for proxies and alternative providers.

    Raises RuntimeError if OPENAI_API_KEY is unset, and ValueError if the
    LLM response can't be parsed as valid ResumeProfile JSON.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set — cannot use LLM parser")

    client_kwargs: dict = {"api_key": settings.OPENAI_API_KEY}
    if settings.OPENAI_BASE_URL:
        client_kwargs["base_url"] = settings.OPENAI_BASE_URL

    client = OpenAI(**client_kwargs)  # type: ignore[arg-type]

    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text},
        ],
        temperature=0.0,
    )

    raw = response.choices[0].message.content or ""
    clean = strip_json_markdown(raw)

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

    # Pydantic validation gives us a second layer of defence against
    # hallucinated fields or wrong types
    return ResumeProfile(**data)
