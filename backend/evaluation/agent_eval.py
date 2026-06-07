"""LangSmith integration and agent evaluation hooks."""

from __future__ import annotations

from typing import Any

from backend.observability.langsmith_setup import configure_langsmith, observability_status


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
        **observability_status(),
    }
