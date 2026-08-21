"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _as_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _as_list(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:pg123456@postgres:5432/gsk"
)
ES_HOST = os.getenv("ES_HOST", "http://elasticsearch:9200")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", "infini_rag_flow")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = _as_int("REDIS_PORT", 6379)
REDIS_DB = _as_int("REDIS_DB", 0)
TEMPORARY_DOCUMENT_TTL_SECONDS = _as_int("TEMPORARY_DOCUMENT_TTL_SECONDS", 7200)
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/data/uploads")).resolve()
MAX_UPLOAD_BYTES = _as_int("MAX_UPLOAD_BYTES", 5 * 1024 * 1024)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL = os.getenv(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "dashscope").strip().lower()
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-in-production")
CORS_ORIGINS = _as_list(
    "CORS_ORIGINS", "http://localhost:5181,http://127.0.0.1:5181"
)
SUPPORTED_KNOWLEDGE_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx", ".txt", ".md", ".markdown", ".html", ".htm"
}
SUPPORTED_TEMPORARY_EXTENSIONS = {".pdf", ".docx", ".txt"}

