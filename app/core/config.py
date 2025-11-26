from __future__ import annotations

import os
from typing import List, Optional, Union

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


def _split_csv(val: Union[str, List[str], None]) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [v.strip() for v in val if v and str(v).strip()]
    return [p.strip() for p in str(val).split(",") if str(p).strip()]


class Settings(BaseSettings):
    # ---- Proje / API ----
    PROJECT_NAME: str = "Jetlink Memory Bot"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # CORS
    ALLOWED_ORIGINS: List[str] = _split_csv(os.getenv("ALLOWED_ORIGINS", "*"))

    # Basit API anahtarı
    API_KEY: Optional[str] = os.getenv("API_KEY")

    # ---- DB ----
    DB_PATH: str = os.getenv("DB_PATH", "./data/memory.db")

    # ---- LLM (Gemini) ----
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_ENDPOINT: Optional[str] = os.getenv("GEMINI_ENDPOINT")

    # ---- Embeddings ----
    GOOGLE_EMBED_API_KEY: Optional[str] = os.getenv("GOOGLE_EMBED_API_KEY")
    EMB_VERSION: str = os.getenv("EMB_VERSION", "text-embedding-004")
    EMB_MODEL: str = os.getenv("EMB_MODEL", "text-embedding-004")
    EMB_DIM: int = int(os.getenv("EMB_DIM", "768"))
    GOOGLE_EMBED_ENDPOINT: Optional[str] = os.getenv("GOOGLE_EMBED_ENDPOINT")

    # ---- Vector Store ----
    VECTORSTORE_BACKEND: str = os.getenv("VECTORSTORE_BACKEND", "faiss")
    VECTORSTORE_LOCAL_DIR: str = os.getenv(
        "VECTORSTORE_LOCAL_DIR",
        "./data/vectorstore_local",
    )
    VECTORSTORE_GLOBAL_DIR: str = os.getenv(
        "VECTORSTORE_GLOBAL_DIR",
        "./data/vectorstore_global",
    )

    # ---- Retrieval varsayılanları ----
    STM_MAX_TURNS_DEFAULT: int = int(os.getenv("STM_MAX_TURNS_DEFAULT", "8"))
    TOPK_LOCAL_DEFAULT: int = int(os.getenv("TOPK_LOCAL_DEFAULT", "8"))
    TOPK_GLOBAL_DEFAULT: int = int(os.getenv("TOPK_GLOBAL_DEFAULT", "8"))
    RETRIEVAL_BUDGET_TOKENS: int = int(os.getenv("RETRIEVAL_BUDGET_TOKENS", "400"))

    # Retrieval için minimum benzerlik eşiği (0–1 arası)
    RETRIEVAL_MIN_SIMILARITY: float = float(
        os.getenv("RETRIEVAL_MIN_SIMILARITY", "0.75")
    )

    # ---- Memory write-back politikası ----
    WRITEBACK_CONFIDENCE_THRESHOLD: float = float(
        os.getenv("WRITEBACK_CONFIDENCE_THRESHOLD", "0.6")
    )

    # ---- Rate limit / Server ----
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "60/minute")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # ---- Pydantic v2 config ----
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Validators ----
    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def _val_allowed_origins(cls, v):
        lst = _split_csv(v)
        return ["*"] if lst == ["*"] else lst

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _val_log_level(cls, v):
        return str(v).upper() if v else "INFO"


settings = Settings()
