"""Integration tests for the LangGraph pipeline."""

import json

from backend.agents.document_agent import DocumentAgent
from backend.agents.orchestrator import extract_transactions, run_pipeline
from backend.config import Settings
from backend.evaluation.agent_eval import run_eval_suite
from backend.router.model_router import ModelRouter


def _mock_router() -> ModelRouter:
    return ModelRouter(settings=Settings(mock_llm=True, llm_provider="vertex"))


def test_extract_transactions_returns_empty_without_fallback():
    assert extract_transactions({}) == []
    assert extract_transactions({"extracted": {"parse_error": True, "raw": "prose"}}) == []
    assert extract_transactions({"extracted": {"transactions": "not-a-list"}}) == []


def test_extract_transactions_keeps_dict_rows_only():
    doc = {
        "extracted": {
            "transactions": [
                {"merchant": "Starbucks", "amount": -5.75},
                "skip-me",
                {"merchant": "Netflix", "amount": -15.99},
            ]
        }
    }
    txs = extract_transactions(doc)
    assert len(txs) == 2
    assert txs[0]["merchant"] == "Starbucks"


def test_pipeline_aborts_when_document_has_no_transactions(monkeypatch):
    def fake_run(self, raw_text, source="unknown"):
        return {
            "agent": "document",
            "source": source,
            "extracted": {"raw": "Here is a prose breakdown with no JSON.", "parse_error": True},
            "model": "mock",
            "usage": {},
        }

    monkeypatch.setattr(DocumentAgent, "run", fake_run)
    state = run_pipeline("garbage input", source="test", router=_mock_router())

    assert state["errors"]
    assert any("no transactions" in e or "failed to parse" in e for e in state["errors"])
    assert not state.get("analysis_result")
    assert not state.get("recommendation_result")
    dumped = json.dumps(state)
    assert "Sample Merchant" not in dumped
    assert "cost_summary" in state


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
    state = run_pipeline(sample, source="test", router=_mock_router())
    assert extract_transactions(state["document_result"])
    assert "recommendation_result" in state
    assert "cost_summary" in state
    assert "pipeline_run_id" in state
    assert state["pipeline_run_id"]
    assert not state.get("errors")
    eval_result = run_eval_suite(state)
    assert eval_result["overall_score"] >= 0.5
