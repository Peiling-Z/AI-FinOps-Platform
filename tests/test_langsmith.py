"""Tests for LangSmith observability setup."""

from backend.config import Settings
from backend.observability.langsmith_setup import (
    configure_langsmith,
    get_langsmith_callbacks,
    observability_status,
)


def test_langsmith_disabled_without_api_key():
    settings = Settings(langchain_tracing_v2=True, langchain_api_key=None)
    assert configure_langsmith(settings) is False
    assert get_langsmith_callbacks(settings) == []


def test_langsmith_enabled_with_api_key(monkeypatch):
    settings = Settings(
        langchain_tracing_v2=True,
        langchain_api_key="test-key",
        langchain_project="test-project",
    )
    assert configure_langsmith(settings) is True
    callbacks = get_langsmith_callbacks(settings)
    assert len(callbacks) == 1


def test_observability_status():
    settings = Settings(
        mock_llm=False,
        llm_provider="vertex",
        vertex_ai_project="my-gcp-project",
        langchain_tracing_v2=True,
        langchain_api_key="test-key",
    )
    status = observability_status(settings)
    assert status["langsmith_enabled"] is True
    assert status["vertex_configured"] is True
    assert status["llm_provider"] == "vertex"
