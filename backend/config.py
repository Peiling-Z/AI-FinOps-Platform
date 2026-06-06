"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # LLM — use mock mode when keys are absent (local dev / CI)
    mock_llm: bool = True
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    vertex_ai_project: str | None = None
    vertex_ai_location: str = "us-central1"

    # Plaid
    plaid_client_id: str | None = None
    plaid_secret: str | None = None
    plaid_env: str = "sandbox"

    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "ai-finops-platform"


@lru_cache
def get_settings() -> Settings:
    return Settings()
