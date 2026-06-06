"""LangSmith integration and agent evaluation hooks."""

from __future__ import annotations

import os
from typing import Any

from backend.config import get_settings


def configure_langsmith() -> bool:
    """Enable LangSmith tracing if credentials are present."""
    settings = get_settings()
    if not settings.langchain_api_key:
        return False
    os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    return True


def evaluate_output(expected_keys: list[str], output: dict[str, Any]) -> dict[str, Any]:
    """Lightweight schema check for agent outputs (CI-friendly)."""
    missing = [k for k in expected_keys if k not in output]
    return {
        "passed": len(missing) == 0,
        "missing_keys": missing,
        "score": 1.0 if not missing else max(0.0, 1.0 - len(missing) / len(expected_keys)),
    }


def run_eval_suite(pipeline_result: dict[str, Any]) -> dict[str, Any]:
    """Run basic eval checks on a full pipeline result."""
    checks = {
        "recommendation": evaluate_output(
            ["agent", "action_plan"],
            pipeline_result.get("recommendation_result", {}),
        ),
        "analysis": evaluate_output(
            ["agent", "analysis"],
            pipeline_result.get("analysis_result", {}),
        ),
        "cost_tracking": evaluate_output(
            ["total_cost_usd", "aggregate_roi"],
            pipeline_result.get("cost_summary", {}),
        ),
    }
    scores = [c["score"] for c in checks.values()]
    return {
        "checks": checks,
        "overall_score": round(sum(scores) / len(scores), 3) if scores else 0.0,
        "langsmith_enabled": configure_langsmith(),
    }
