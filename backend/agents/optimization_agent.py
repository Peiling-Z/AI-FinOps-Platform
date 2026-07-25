"""Optimization Agent — savings opportunities and alternatives."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.json_utils import parse_llm_json
from backend.agents.savings import savings_from_content
from backend.router.model_router import ModelRouter, TaskType


class OptimizationAgent:
    """Sole source of truth for how much money the pipeline claims to find."""

    SYSTEM = (
        "You are a personal finance optimizer. Identify concrete savings opportunities "
        "with estimated annual savings in USD. Return valid JSON with an 'actions' list, "
        "where each action includes an 'estimated_annual_savings_usd' number."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, spending_profile: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Spending profile:\n{json.dumps(spending_profile, indent=2)[:6000]}"
        result = self.router.invoke(
            TaskType.RECOMMENDATION,
            prompt,
            system=self.SYSTEM,
            savings_extractor=savings_from_content,
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
