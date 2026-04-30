"""Prompt templates for a future LLM-based job extractor."""


JOB_EXTRACTION_PROMPT = """You are a recruiting information extractor.
Extract job information from the page text below and return strict JSON only.
Do not add explanations. If a field is missing, use null. Do not infer or
invent fields from common sense.

Required fields:
title, company, location, salary, experience_required, education_required,
job_type, responsibilities, requirements, skills

Page text:
{page_text}
"""

