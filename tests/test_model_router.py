"""Tests for model router and cost tracker."""

from backend.config import Settings
from backend.router.cost_tracker import CostTracker
from backend.router.model_router import ModelRouter, RoutingRules, TaskType


def test_routing_rules_multi():
    assert RoutingRules.resolve(TaskType.DOCUMENT_PARSE, "multi") == "gemini-1.5-flash"
    assert RoutingRules.resolve(TaskType.DEEP_ANALYSIS, "multi") == "gpt-4o"
    assert RoutingRules.resolve(TaskType.RECOMMENDATION, "multi") == "claude-3-5-sonnet"


def test_routing_rules_vertex():
    assert RoutingRules.resolve(TaskType.DOCUMENT_PARSE, "vertex") == "gemini-2.0-flash-lite"
    assert RoutingRules.resolve(TaskType.DEEP_ANALYSIS, "vertex") == "gemini-1.5-pro"
    assert RoutingRules.resolve(TaskType.RECOMMENDATION, "vertex") == "gemini-1.5-pro"


def test_cost_tracker_roi():
    tracker = CostTracker()
    record = tracker.record(
        task_type="recommendation",
        model="claude-3-5-sonnet",
        input_tokens=1000,
        output_tokens=500,
        estimated_savings_usd=420.0,
    )
    assert record.cost_usd > 0
    assert record.roi is not None
    assert record.roi > 0


def test_model_router_mock_invoke_vertex():
    settings = Settings(mock_llm=True, llm_provider="vertex")
    router = ModelRouter(settings=settings)
    result = router.invoke(TaskType.DOCUMENT_PARSE, "Sample bank statement text")
    assert "content" in result
    assert result["model"] == "gemini-2.0-flash-lite"
    assert router.summary()["total_calls"] >= 1
