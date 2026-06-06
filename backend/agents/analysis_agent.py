"""Analysis Agent — trends, anomalies, and risk scoring."""

from __future__ import annotations

import json
from typing import Any

from backend.router.model_router import ModelRouter, TaskType


class AnalysisAgent:
    SYSTEM = (
        "You are a financial analyst. Detect spending trends, anomalies, and assign "
        "a risk score between 0 and 1. Return valid JSON only."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, transactions: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = f"Analyze these transactions:\n{json.dumps(transactions, indent=2)[:6000]}"
        result = self.router.invoke(TaskType.ANOMALY_DETECTION, prompt, system=self.SYSTEM)
        try:
            analysis = json.loads(result["content"])
        except json.JSONDecodeError:
            analysis = {"summary": result["content"]}
        return {
            "agent": "analysis",
            "analysis": analysis,
            "model": result["model"],
            "usage": result["usage"],
        }

    def deep_analysis(self, context: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Perform deep financial analysis:\n{json.dumps(context, indent=2)[:6000]}"
        result = self.router.invoke(TaskType.DEEP_ANALYSIS, prompt, system=self.SYSTEM)
        try:
            analysis = json.loads(result["content"])
        except json.JSONDecodeError:
            analysis = {"summary": result["content"]}
        return {
            "agent": "analysis_deep",
            "analysis": analysis,
            "model": result["model"],
            "usage": result["usage"],
        }
