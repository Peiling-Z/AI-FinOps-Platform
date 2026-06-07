"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LlmProvider = Literal["multi", "vertex"]


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

    # LLM — mock mode for local dev / CI without credentials
    mock_llm: bool = True
    llm_provider: LlmProvider = "vertex"

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    google_application_credentials: str | None = None
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
    langchain_endpoint: str | None = None

    # BigQuery — LLM cost analytics sink
    bigquery_enabled: bool = False
    bigquery_project: str | None = None
    bigquery_dataset: str = "finops_analytics"
    bigquery_table: str = "llm_usage"
    bigquery_location: str = "US"
    bigquery_auto_create: bool = True

    @property
    def vertex_ready(self) -> bool:
        return bool(self.vertex_ai_project) and not self.mock_llm

    @property
    def live_llm_ready(self) -> bool:
        if self.mock_llm:
            return False
        if self.llm_provider == "vertex":
            return self.vertex_ready
        return bool(
            self.openai_api_key
            or self.anthropic_api_key
            or self.vertex_ai_project
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
