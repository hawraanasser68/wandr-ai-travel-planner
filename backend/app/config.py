"""
Single source of truth for all configuration.
pydantic-settings reads values from the .env file and validates types at startup.
If a required variable is missing the app refuses to start — no silent failures.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Allow extra vars in .env without crashing
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    # ── Auth ──────────────────────────────────────────────────────────────────
    jwt_secret_key: str #Secret key used to sign and verify JWT tokens
    jwt_algorithm: str = "HS256"  # Algorithm used for JWT signing (default = HS256)
    jwt_expire_minutes: int = 1440  # 24 hours

    # ── LLM provider — set LLM_PROVIDER=groq or =gemini ─────────────────────
    # Groq free tier: https://console.groq.com  (no credit card required)
    # Gemini free tier: https://aistudio.google.com/app/apikey
    llm_provider: str = "groq"

    # Groq credentials (used when llm_provider=groq)
    groq_api_key: str = ""
    fast_model: str = "llama-3.1-8b-instant"
    synth_model: str = "llama-3.1-8b-instant"

    # Google Gemini credentials (used when llm_provider=gemini)
    google_api_key: str = ""

    # ── Live APIs ─────────────────────────────────────────────────────────────
    # Optional — app starts without it, live_tool.py logs a warning instead
    openweathermap_api_key: str = ""

    # ── Flight search APIs ────────────────────────────────────────────────────
    travelpayouts_token: str = ""   # travelpayouts.com (optional fallback)
    api_ninjas_key: str = ""        # api-ninjas.com (optional)
    rapidapi_key: str = ""          # rapidapi.com → Sky Scrapper (Skyscanner data)

    # ── Email webhook ─────────────────────────────────────────────────────────
    # Optional — app starts without it, webhook.py skips silently
    resend_api_key: str = ""
    resend_from_email: str = "onboarding@resend.dev"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"

    # ── LangSmith tracing ─────────────────────────────────────────────────────
    langchain_tracing_v2: str = "false"
    langchain_api_key: str = ""
    langchain_project: str = "ai-travel-planner"

    # ── ML artifacts ──────────────────────────────────────────────────────────
    ml_model_path: str = "artifacts/travel_model.joblib"
    ml_encoder_path: str = "artifacts/label_encoder.joblib"

    # ── RAG ───────────────────────────────────────────────────────────────────
    # all-MiniLM-L6-v2 produces 384-dim vectors — fast and good enough
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_chunk_size: int = 500
    rag_chunk_overlap: int = 50
    rag_top_k: int = 5


# lru_cache means Settings() is only instantiated once per process.
# Every module calls get_settings() — no globals scattered around.
@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    # LangSmith reads these directly from os.environ
    if settings.langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = settings.langchain_tracing_v2
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    return settings
