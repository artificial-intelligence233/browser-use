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
CHROMA_COLLECTION_NAME = os.getenv("JOB_RAG_CHROMA_COLLECTION", "job_postings")
EMBEDDING_API_BASE_URL = os.getenv("JOB_RAG_EMBEDDING_BASE_URL")
EMBEDDING_API_MODEL = os.getenv("JOB_RAG_EMBEDDING_MODEL")
EMBEDDING_API_KEY = os.getenv("JOB_RAG_EMBEDDING_API_KEY")
EMBEDDING_API_TIMEOUT_SECONDS = int(os.getenv("JOB_RAG_EMBEDDING_TIMEOUT_SECONDS", "30"))
EMBEDDING_API_ALLOW_FALLBACK = os.getenv("JOB_RAG_EMBEDDING_ALLOW_FALLBACK", "1").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LLM_EXTRACTION_ENABLED = os.getenv("JOB_RAG_ENABLE_LLM_EXTRACTION", "0").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
LLM_API_BASE_URL = os.getenv("JOB_RAG_LLM_BASE_URL")
LLM_API_MODEL = os.getenv("JOB_RAG_LLM_MODEL")
LLM_API_KEY = os.getenv("JOB_RAG_LLM_API_KEY")
LLM_API_TIMEOUT_SECONDS = int(os.getenv("JOB_RAG_LLM_TIMEOUT_SECONDS", "45"))

BROWSER_USE_ENABLED = os.getenv("JOB_RAG_ENABLE_BROWSER_USE", "0").lower() in {"1", "true", "yes", "on"}
BROWSER_USE_HEADLESS = os.getenv("JOB_RAG_BROWSER_USE_HEADLESS", "1").lower() not in {"0", "false", "no", "off"}
BROWSER_USE_TIMEOUT_SECONDS = int(os.getenv("JOB_RAG_BROWSER_USE_TIMEOUT_SECONDS", "25"))
BROWSER_USE_WORK_DIR = Path(os.getenv("JOB_RAG_BROWSER_USE_WORK_DIR", str(PROJECT_ROOT / ".browseruse"))).resolve()
PLAYWRIGHT_BROWSERS_PATH = Path(os.getenv("PLAYWRIGHT_BROWSERS_PATH", r"D:\agent_part3")).resolve()
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
