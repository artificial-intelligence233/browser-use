"""Optional LLM-based fallback extractor for non-standard job pages."""

from __future__ import annotations

import json
import re
from typing import Any

from job_rag.config import (
    LLM_API_BASE_URL,
    LLM_API_KEY,
    LLM_API_MODEL,
    LLM_API_TIMEOUT_SECONDS,
    LLM_EXTRACTION_ENABLED,
)
from job_rag.extraction.prompts import JOB_EXTRACTION_PROMPT, JOB_EXTRACTION_SYSTEM_PROMPT


LIST_FIELDS = {"responsibilities", "requirements", "skills"}
STRING_FIELDS = {
    "title",
    "company",
    "location",
    "salary",
    "experience_required",
    "education_required",
    "job_type",
}


class LLMExtractionUnavailable(RuntimeError):
    """Raised when LLM extraction is disabled, unconfigured, or fails."""


def normalize_openai_compatible_base_url(base_url: str | None) -> str | None:
    """Normalize provider root URLs to an OpenAI-compatible v1 base URL."""
    if not base_url:
        return None
    clean = base_url.strip().rstrip("/")
    if not clean:
        return None
    if clean.endswith("/v1"):
        return clean
    return clean + "/v1"


def is_llm_extraction_configured() -> bool:
    """Return True when local runtime env vars are sufficient for LLM extraction."""
    return bool(LLM_EXTRACTION_ENABLED and LLM_API_KEY and LLM_API_MODEL)


def normalize_llm_job_fields(data: dict[str, Any]) -> dict[str, Any]:
    """Coerce LLM JSON into the stable extractor field shape."""
    normalized: dict[str, Any] = {}
    for field in STRING_FIELDS:
        value = data.get(field)
        if value is None:
            normalized[field] = None
        elif isinstance(value, str):
            clean = re.sub(r"\s+", " ", value).strip()
            normalized[field] = clean or None
        else:
            normalized[field] = str(value).strip() or None

    for field in LIST_FIELDS:
        value = data.get(field)
        if value is None:
            normalized[field] = []
        elif isinstance(value, list):
            normalized[field] = [re.sub(r"\s+", " ", str(item)).strip() for item in value if str(item).strip()]
        elif isinstance(value, str):
            parts = re.split(r"[\n;；]+", value)
            normalized[field] = [part.strip(" -*\u2022") for part in parts if part.strip(" -*\u2022")]
        else:
            normalized[field] = []
    return normalized


def parse_llm_json(content: str) -> dict[str, Any]:
    """Parse a JSON object from a model response."""
    raw = (content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("LLM response is not a JSON object")
    return normalize_llm_job_fields(parsed)


def _chat_completion_content(client: Any, messages: list[dict[str, str]]) -> str:
    request: dict[str, Any] = {
        "model": LLM_API_MODEL,
        "messages": messages,
        "temperature": 0,
    }
    try:
        response = client.chat.completions.create(
            **request,
            response_format={"type": "json_object"},
        )
    except Exception:
        response = client.chat.completions.create(**request)

    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return str(response.get("choices", [{}])[0].get("message", {}).get("content") or "")
    return response.choices[0].message.content or ""


def extract_job_fields_with_llm(page_text: str) -> dict[str, Any]:
    """Extract job fields through an OpenAI-compatible chat model."""
    if not is_llm_extraction_configured():
        raise LLMExtractionUnavailable("LLM extraction is disabled or missing local runtime configuration")
    try:
        from openai import OpenAI

        client_options: dict[str, Any] = {
            "api_key": LLM_API_KEY,
            "timeout": LLM_API_TIMEOUT_SECONDS,
        }
        base_url = normalize_openai_compatible_base_url(LLM_API_BASE_URL)
        if base_url:
            client_options["base_url"] = base_url
        client = OpenAI(**client_options)
        content = _chat_completion_content(
            client,
            [
                {"role": "system", "content": JOB_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": JOB_EXTRACTION_PROMPT.format(page_text=page_text)},
            ],
        )
        return parse_llm_json(content)
    except LLMExtractionUnavailable:
        raise
    except Exception as exc:
        raise LLMExtractionUnavailable(f"LLM extraction failed: {exc}") from exc
