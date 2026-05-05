"""Prompt templates for the optional LLM-based job extractor."""


JOB_EXTRACTION_SYSTEM_PROMPT = """You are a careful recruiting information extractor.
Extract only information that is explicitly present in the provided page text.
Do not infer, guess, or fabricate company names, salary, location, skills, or requirements.
If a field is missing or uncertain, use null or an empty list.
Return strict JSON only, with no markdown and no explanation.
"""


JOB_EXTRACTION_PROMPT = """Extract job information from the page text below.

Rules:
- Use only the provided page text.
- The page may be a formal job description, forum post, article, or informal recruiting post.
- If a field is missing, use null for string fields and [] for list fields.
- Keep responsibilities and requirements grounded in the original text.
- If a forum post has no explicit company name, use the explicit team/company description only if present; otherwise null.
- Do not invent resume facts, job facts, salary, or credentials.

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
