"""Integration tests for the LangGraph pipeline."""

from backend.agents.orchestrator import run_pipeline
from backend.evaluation.agent_eval import run_eval_suite


def test_full_pipeline_mock():
    sample = "05/01 Grocery Store -85.20\n05/04 Utility Bill -120.00"
    state = run_pipeline(sample, source="test")
    assert "recommendation_result" in state
    assert "cost_summary" in state
    eval_result = run_eval_suite(state)
    assert eval_result["overall_score"] >= 0.5
