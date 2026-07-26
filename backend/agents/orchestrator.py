"""LangGraph orchestrator — state machine for the multi-agent FinOps pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.compliance_agent import ComplianceAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.optimization_agent import OptimizationAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.analytics.pipeline_context import pipeline_run
from backend.router.model_router import ModelRouter


class FinOpsState(TypedDict):
    """Shared state passed between agent nodes."""

    raw_input: str
    source: str
    document_result: dict[str, Any]
    analysis_result: dict[str, Any]
    optimization_result: dict[str, Any]
    compliance_result: dict[str, Any]
    recommendation_result: dict[str, Any]
    errors: Annotated[list[str], operator.add]
    cost_summary: dict[str, Any]


def extract_transactions(document_result: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull transactions from document agent output.

    Returns an empty list when parsing failed or the model omitted transactions.
    Callers must treat empty as a hard stop — never invent Sample Merchant data.
    """
    extracted = document_result.get("extracted") or {}
    if not isinstance(extracted, dict):
        return []
    txs = extracted.get("transactions") or []
    if not isinstance(txs, list):
        return []
    return [tx for tx in txs if isinstance(tx, dict)]


def _document_extract_error(document_result: dict[str, Any]) -> str:
    if not document_result:
        return "document_agent: document step did not produce a result"
    extracted = document_result.get("extracted") or {}
    if isinstance(extracted, dict) and extracted.get("parse_error"):
        return "document_agent: failed to parse LLM output as JSON with transactions"
    return "document_agent: no transactions extracted from input"


def build_finops_graph(router: ModelRouter | None = None) -> StateGraph:
    """Construct the LangGraph state machine."""
    shared_router = router or ModelRouter()
    document_agent = DocumentAgent(shared_router)
    analysis_agent = AnalysisAgent(shared_router)
    optimization_agent = OptimizationAgent(shared_router)
    compliance_agent = ComplianceAgent(shared_router)
    recommendation_agent = RecommendationAgent(shared_router)

    graph = StateGraph(FinOpsState)

    def ingest_node(state: FinOpsState) -> dict[str, Any]:
        return {"errors": []}

    def document_node(state: FinOpsState) -> dict[str, Any]:
        try:
            result = document_agent.run(state["raw_input"], source=state.get("source", "text"))
            update: dict[str, Any] = {"document_result": result}
            if not extract_transactions(result):
                update["errors"] = [_document_extract_error(result)]
            return update
        except Exception as exc:  # noqa: BLE001 — surface agent failures in state
            return {"errors": [f"document_agent: {exc}"]}

    def abort_node(state: FinOpsState) -> dict[str, Any]:
        """Stop before expensive agents when document extraction failed."""
        errors: list[str] = []
        if not state.get("errors"):
            errors = [_document_extract_error(state.get("document_result", {}))]
        return {
            "errors": errors,
            "cost_summary": shared_router.summary(),
        }

    def analysis_node(state: FinOpsState) -> dict[str, Any]:
        try:
            txs = extract_transactions(state.get("document_result", {}))
            result = analysis_agent.run(txs)
            deep = analysis_agent.deep_analysis({"transactions": txs, "analysis": result["analysis"]})
            result["deep_analysis"] = deep["analysis"]
            return {"analysis_result": result}
        except Exception as exc:
            return {"errors": [f"analysis_agent: {exc}"]}

    def optimization_node(state: FinOpsState) -> dict[str, Any]:
        try:
            profile = {
                "transactions": extract_transactions(state.get("document_result", {})),
                "analysis": state.get("analysis_result", {}).get("analysis", {}),
            }
            result = optimization_agent.run(profile)
            return {"optimization_result": result}
        except Exception as exc:
            return {"errors": [f"optimization_agent: {exc}"]}

    def compliance_node(state: FinOpsState) -> dict[str, Any]:
        try:
            txs = extract_transactions(state.get("document_result", {}))
            result = compliance_agent.run(txs)
            return {"compliance_result": result}
        except Exception as exc:
            return {"errors": [f"compliance_agent: {exc}"]}

    def recommendation_node(state: FinOpsState) -> dict[str, Any]:
        try:
            outputs = {
                "document": state.get("document_result", {}),
                "analysis": state.get("analysis_result", {}),
                "optimization": state.get("optimization_result", {}),
                "compliance": state.get("compliance_result", {}),
            }
            result = recommendation_agent.run(outputs)
            return {
                "recommendation_result": result,
                "cost_summary": shared_router.summary(),
            }
        except Exception as exc:
            return {"errors": [f"recommendation_agent: {exc}"]}

    def route_after_document(state: FinOpsState) -> Literal["analysis", "abort"]:
        if extract_transactions(state.get("document_result", {})):
            return "analysis"
        return "abort"

    graph.add_node("ingest", ingest_node)
    graph.add_node("document", document_node)
    graph.add_node("abort", abort_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("optimization", optimization_node)
    graph.add_node("compliance", compliance_node)
    graph.add_node("recommendation", recommendation_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "document")
    graph.add_conditional_edges(
        "document",
        route_after_document,
        {"analysis": "analysis", "abort": "abort"},
    )
    graph.add_edge("abort", END)
    graph.add_edge("analysis", "optimization")
    graph.add_edge("optimization", "compliance")
    graph.add_edge("compliance", "recommendation")
    graph.add_edge("recommendation", END)

    return graph


def run_pipeline(
    raw_input: str,
    source: str = "manual",
    router: ModelRouter | None = None,
) -> dict[str, Any]:
    """Execute the full agent pipeline and return final state."""
    graph = build_finops_graph(router).compile()
    initial: FinOpsState = {
        "raw_input": raw_input,
        "source": source,
        "document_result": {},
        "analysis_result": {},
        "optimization_result": {},
        "compliance_result": {},
        "recommendation_result": {},
        "errors": [],
        "cost_summary": {},
    }
    with pipeline_run() as run_id:
        final_state = graph.invoke(initial)
    final_state["pipeline_run_id"] = run_id
    return final_state
