"""Configuration constants for the Job RAG MVP."""

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
EXAMPLES_DIR = PACKAGE_ROOT / "examples"
OUTPUTS_DIR = EXAMPLES_DIR / "outputs"
LOCAL_JOBS_DIR = EXAMPLES_DIR / "local_jobs"

DEFAULT_TOP_K = 5
MAX_PAGE_TEXT_CHARS = 12000
VECTOR_INDEX_FILENAME = "vector_index.json"

EMBEDDING_PROVIDER = os.getenv("JOB_RAG_EMBEDDING_PROVIDER", "local").lower()
VECTOR_BACKEND = os.getenv("JOB_RAG_VECTOR_BACKEND", "local").lower()
CHROMA_INDEX_DIR = Path(os.getenv("JOB_RAG_CHROMA_DIR", str(OUTPUTS_DIR / "chroma_index"))).resolve()

BROWSER_USE_ENABLED = os.getenv("JOB_RAG_ENABLE_BROWSER_USE", "0").lower() in {"1", "true", "yes", "on"}
BROWSER_USE_HEADLESS = os.getenv("JOB_RAG_BROWSER_USE_HEADLESS", "1").lower() not in {"0", "false", "no", "off"}
BROWSER_USE_TIMEOUT_SECONDS = int(os.getenv("JOB_RAG_BROWSER_USE_TIMEOUT_SECONDS", "25"))
BROWSER_USE_WORK_DIR = Path(os.getenv("JOB_RAG_BROWSER_USE_WORK_DIR", str(PROJECT_ROOT / ".browseruse"))).resolve()
BROWSER_USE_CONFIG_DIR = Path(
    os.getenv("BROWSER_USE_CONFIG_DIR", str(BROWSER_USE_WORK_DIR / "config"))
).resolve()
BROWSER_USE_HOME_DIR = Path(os.getenv("BROWSER_USE_HOME", str(BROWSER_USE_WORK_DIR / "home"))).resolve()
BROWSER_USE_PROFILE_DIR = Path(
    os.getenv("JOB_RAG_BROWSER_USE_PROFILE_DIR", str(BROWSER_USE_WORK_DIR / "profiles" / "job_rag"))
).resolve()
BROWSER_USE_DOWNLOADS_DIR = Path(
    os.getenv("JOB_RAG_BROWSER_USE_DOWNLOADS_DIR", str(BROWSER_USE_WORK_DIR / "downloads"))
).resolve()
