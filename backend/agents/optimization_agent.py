"""Optimization Agent — savings opportunities and alternatives."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.json_utils import parse_llm_json
from backend.router.model_router import ModelRouter, TaskType


class OptimizationAgent:
    SYSTEM = (
        "You are a personal finance optimizer. Identify concrete savings opportunities "
        "with estimated annual savings in USD. Return valid JSON with an 'actions' list."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, spending_profile: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Spending profile:\n{json.dumps(spending_profile, indent=2)[:6000]}"
        estimated_savings = float(spending_profile.get("optimization_potential_usd", 420.0))
        result = self.router.invoke(
            TaskType.RECOMMENDATION,
            prompt,
            system=self.SYSTEM,
            estimated_savings_usd=estimated_savings,
        )
        try:
            recommendations = parse_llm_json(result["content"])
        except json.JSONDecodeError:
            recommendations = {"actions": [], "raw": result["content"]}
        return {
            "agent": "optimization",
            "recommendations": recommendations,
            "model": result["model"],
            "usage": result["usage"],
        }
