"""FastAPI endpoints for the AI FinOps Platform."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agents.orchestrator import run_pipeline
from backend.config import get_settings
from backend.ingestion.csv_loader import load_csv_string
from backend.ingestion.pdf_parser import extract_text_from_bytes
from backend.ingestion.plaid_client import PlaidClient
from backend.router.model_router import ModelRouter, RoutingRules, TaskType

app = FastAPI(
    title="AI FinOps Platform",
    description="Multi-agent household finance dashboard with cost-aware model routing",
    version="0.1.0",
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
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "mock_llm": str(settings.mock_llm),
        "project": "ai-finops-platform",
    }


@app.get("/router/rules")
def routing_rules() -> dict[str, str]:
    return {k.value: v for k, v in RoutingRules.RULES.items()}


@app.get("/router/costs")
def cost_summary() -> dict[str, Any]:
    return ModelRouter().summary()


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    state = run_pipeline(request.text, source=request.source)
    return AnalyzeResponse(
        status="completed" if not state.get("errors") else "completed_with_errors",
        recommendation=state.get("recommendation_result", {}),
        analysis=state.get("analysis_result", {}),
        optimization=state.get("optimization_result", {}),
        compliance=state.get("compliance_result", {}),
        cost_summary=state.get("cost_summary", {}),
        errors=state.get("errors", []),
    )


@app.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    content = await file.read()
    try:
        text = extract_text_from_bytes(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state = run_pipeline(text, source=f"pdf:{file.filename}")
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
    state = run_pipeline(text, source=f"csv:{file.filename}")
    return {"filename": file.filename, "transaction_count": len(transactions), "pipeline": state}


@app.get("/ingest/plaid/mock")
def ingest_plaid_mock() -> dict[str, Any]:
    client = PlaidClient()
    transactions = client.fetch_mock_as_list()
    text = json.dumps({"transactions": transactions, "source": "plaid_mock"}, indent=2)
    state = run_pipeline(text, source="plaid:sandbox")
    return {"transaction_count": len(transactions), "pipeline": state}


@app.post("/agents/{task_type}")
def run_single_agent(task_type: TaskType, request: AnalyzeRequest) -> dict[str, Any]:
    router = ModelRouter()
    result = router.invoke(task_type, request.text)
    return {"task_type": task_type.value, "result": result}
