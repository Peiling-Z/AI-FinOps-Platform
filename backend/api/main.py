"""FastAPI endpoints for the AI FinOps Platform."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agents.orchestrator import run_pipeline
from backend.config import get_settings
from backend.evaluation.agent_eval import run_eval_suite
from backend.ingestion.csv_loader import load_csv_string
from backend.ingestion.pdf_parser import extract_text_from_bytes
from backend.ingestion.plaid_client import PlaidClient
from backend.analytics.bigquery_sink import get_bigquery_sink
from backend.observability.langsmith_setup import configure_langsmith, observability_status
from backend.router.model_router import RoutingRules, TaskType, get_shared_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    if configure_langsmith(settings):
        logger.info("LangSmith tracing active — project: %s", settings.langchain_project)
    else:
        logger.info("LangSmith tracing inactive")
    yield


app = FastAPI(
    title="AI FinOps Platform",
    description="Multi-agent household finance dashboard with cost-aware model routing",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., description="Raw financial text or transaction dump")
    source: str = Field(default="manual", description="Data source label")


class AnalyzeResponse(BaseModel):
    status: str
    recommendation: dict[str, Any]
    analysis: dict[str, Any]
    optimization: dict[str, Any]
    compliance: dict[str, Any]
    cost_summary: dict[str, Any]
    errors: list[str]


@app.get("/health")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "mock_llm": settings.mock_llm,
        "live_llm_ready": settings.live_llm_ready,
        **observability_status(settings),
        "bigquery_sink": get_bigquery_sink(settings).status(),
    }


@app.get("/observability/status")
def observability() -> dict[str, Any]:
    settings = get_settings()
    return {
        **observability_status(settings),
        "routing_rules": RoutingRules.active_rules(settings.llm_provider),
        "bigquery_sink": get_bigquery_sink(settings).status(),
    }


@app.get("/analytics/bigquery/status")
def bigquery_status() -> dict[str, Any]:
    return get_bigquery_sink().status()


@app.get("/router/rules")
def routing_rules() -> dict[str, str]:
    settings = get_settings()
    return RoutingRules.active_rules(settings.llm_provider)


@app.get("/router/costs")
def cost_summary() -> dict[str, Any]:
    return get_shared_router().summary()


@app.post("/router/costs/reset")
def reset_costs() -> dict[str, str]:
    from backend.router.model_router import reset_shared_router

    reset_shared_router()
    return {"status": "reset"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    state = run_pipeline(request.text, source=request.source, router=get_shared_router())
    return AnalyzeResponse(
        status="completed" if not state.get("errors") else "completed_with_errors",
        recommendation=state.get("recommendation_result", {}),
        analysis=state.get("analysis_result", {}),
        optimization=state.get("optimization_result", {}),
        compliance=state.get("compliance_result", {}),
        cost_summary=state.get("cost_summary", {}),
        errors=state.get("errors", []),
    )


@app.post("/evaluate")
def evaluate_pipeline(request: AnalyzeRequest) -> dict[str, Any]:
    """Run pipeline and return LangSmith-aware eval scores."""
    state = run_pipeline(request.text, source=request.source, router=get_shared_router())
    return {
        "pipeline_status": "completed" if not state.get("errors") else "completed_with_errors",
        "eval": run_eval_suite(state),
        "cost_summary": state.get("cost_summary", {}),
        "errors": state.get("errors", []),
    }


@app.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    try:
        text = extract_text_from_bytes(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state = run_pipeline(text, source=f"pdf:{file.filename}", router=get_shared_router())
    return {"filename": file.filename, "extracted_chars": len(text), "pipeline": state}


@app.post("/ingest/csv")
async def ingest_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    content = (await file.read()).decode("utf-8")
    try:
        transactions = load_csv_string(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    text = json.dumps({"transactions": transactions}, indent=2)
    state = run_pipeline(text, source=f"csv:{file.filename}", router=get_shared_router())
    return {"filename": file.filename, "transaction_count": len(transactions), "pipeline": state}


@app.get("/ingest/plaid/mock")
def ingest_plaid_mock() -> dict[str, Any]:
    client = PlaidClient()
    transactions = client.fetch_mock_as_list()
    text = json.dumps({"transactions": transactions, "source": "plaid_mock"}, indent=2)
    state = run_pipeline(text, source="plaid:sandbox", router=get_shared_router())
    return {"transaction_count": len(transactions), "pipeline": state}


@app.post("/agents/{task_type}")
def run_single_agent(task_type: TaskType, request: AnalyzeRequest) -> dict[str, Any]:
    router = get_shared_router()
    result = router.invoke(task_type, request.text)
    return {"task_type": task_type.value, "result": result}
