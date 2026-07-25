"""Integration tests for the LangGraph pipeline."""

from backend.agents.orchestrator import run_pipeline
from backend.config import Settings
from backend.evaluation.agent_eval import run_eval_suite
from backend.router.model_router import ModelRouter


def _mock_router() -> ModelRouter:
    return ModelRouter(settings=Settings(mock_llm=True, llm_provider="vertex"))


def test_savings_attributed_once_per_pipeline():
    """Only the optimization agent books savings, so ROI stays honest."""
    state = run_pipeline("05/01 Grocery Store -85.20", source="test", router=_mock_router())
    summary = state["cost_summary"]

    booked = [r for r in summary["records"] if r["estimated_savings_usd"] > 0]
    assert len(booked) == 1, "savings must be counted exactly once, not per agent"
    assert booked[0]["task_type"] == "recommendation"
    assert summary["total_estimated_savings_usd"] == 420.0
    assert summary["aggregate_roi"] > 0


def test_full_pipeline_mock():
    sample = "05/01 Grocery Store -85.20\n05/04 Utility Bill -120.00"
    state = run_pipeline(sample, source="test")
    assert "recommendation_result" in state
    assert "cost_summary" in state
    assert "pipeline_run_id" in state
    assert state["pipeline_run_id"]
    eval_result = run_eval_suite(state)
    assert eval_result["overall_score"] >= 0.5
