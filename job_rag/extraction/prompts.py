"""Prompt templates for the optional LLM-based job extractor."""


JOB_EXTRACTION_SYSTEM_PROMPT = """You are a careful recruiting information extractor.
Extract only information that is explicitly present in the provided page text.
Do not infer, guess, or fabricate company names, salary, location, skills, or requirements.
If a field is missing or uncertain, use null or an empty list.
Return strict JSON only, with no markdown and no explanation.
Do not use unescaped straight double quotes inside string values; use Chinese quotation marks or escape them.
"""


JOB_EXTRACTION_PROMPT = """Extract job information from the page text below.

Rules:
- Use only the provided page text.
- The page may be a formal job description, forum post, article, or informal recruiting post.
- If a field is missing, use null for string fields and [] for list fields.
- Keep responsibilities and requirements grounded in the original text.
- If a forum post has no explicit company name, use the explicit team/company description only if present; otherwise null.
- Do not invent resume facts, job facts, salary, or credentials.
- Return parseable JSON. Do not wrap it in markdown fences.
- Do not use unescaped straight double quotes inside string values.
- If the source text contains quoted phrases, rewrite the quotes as Chinese quotation marks like “...”.

Required fields:
{{
  "title": string or null,
  "company": string or null,
  "location": string or null,
  "salary": string or null,
  "experience_required": string or null,
  "education_required": string or null,
  "job_type": string or null,
  "responsibilities": list of strings,
  "requirements": list of strings,
  "skills": list of strings
}}

Page text:
{page_text}
"""
