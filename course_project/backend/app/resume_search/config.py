"""Settings loaded from environment / .env file.

All configuration is read from environment variables, with a fallback .env file
at course_project/.env.  No API keys or secrets are hardcoded.

When OPENAI_API_KEY is absent the pipeline automatically degrades to rule-based
parsing — no manual intervention needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# .env lives at course_project/.env relative to this file
_ENV_PATH = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_ENV_PATH)


class Settings:
    """Thin namespace over os.getenv with sensible defaults for local dev."""

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    DEFAULT_MAX_QUERIES: int = int(os.getenv("DEFAULT_MAX_QUERIES", "6"))
    DEFAULT_MAX_RESULTS_PER_QUERY: int = int(os.getenv("DEFAULT_MAX_RESULTS_PER_QUERY", "5"))


settings = Settings()
