"""LangSmith tracing configuration and callback helpers."""

from __future__ import annotations

import logging
import os
from typing import Any

from backend.config import Settings, get_settings

logger = logging.getLogger(__name__)

_configured = False


def configure_langsmith(settings: Settings | None = None) -> bool:
    """Enable LangSmith tracing via environment variables (idempotent)."""
    global _configured
    settings = settings or get_settings()

    if not settings.langchain_api_key:
        logger.info("LangSmith disabled — LANGCHAIN_API_KEY not set")
        return False

    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_TRACING_V2"] = "true" if settings.langchain_tracing_v2 else "false"

    if settings.langchain_endpoint:
        os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint

    _configured = settings.langchain_tracing_v2
    if _configured:
        logger.info("LangSmith tracing enabled for project '%s'", settings.langchain_project)
    return _configured


def get_langsmith_callbacks(settings: Settings | None = None) -> list[Any]:
    """Return LangChain tracer callbacks when tracing is enabled."""
    settings = settings or get_settings()
    if not settings.langchain_tracing_v2 or not settings.langchain_api_key:
        return []

    try:
        from langchain_core.tracers.langchain import LangChainTracer
    except ImportError:
        logger.warning("LangChainTracer unavailable — install langsmith")
        return []

    return [LangChainTracer(project_name=settings.langchain_project)]


def build_invoke_config(
    task_type: str,
    *,
    llm_provider: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """LangChain invoke config with LangSmith metadata and tags."""
    settings = settings or get_settings()
    config: dict[str, Any] = {
        "metadata": {
            "task_type": task_type,
            "llm_provider": llm_provider,
            "project": settings.langchain_project,
        },
        "tags": ["ai-finops", task_type, llm_provider],
    }
    callbacks = get_langsmith_callbacks(settings)
    if callbacks:
        config["callbacks"] = callbacks
    return config


def observability_status(settings: Settings | None = None) -> dict[str, Any]:
    """Runtime observability flags for health checks."""
    settings = settings or get_settings()
    return {
        "langsmith_enabled": bool(
            settings.langchain_tracing_v2 and settings.langchain_api_key
        ),
        "langsmith_project": settings.langchain_project,
        "vertex_configured": bool(settings.vertex_ai_project),
        "llm_provider": settings.llm_provider,
    }
