"""Recommendation Agent — synthesize agent outputs into a prioritized action plan."""

from __future__ import annotations

import json
from typing import Any

from backend.router.model_router import ModelRouter, TaskType


class RecommendationAgent:
    SYSTEM = (
        "You are a financial advisor synthesizer. Combine analysis, optimization, and "
        "compliance findings into a prioritized action plan with scores 1-5. "
        "Return valid JSON with 'action_plan' list."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, agent_outputs: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Synthesize these agent outputs:\n{json.dumps(agent_outputs, indent=2)[:8000]}"
        savings = self._estimate_total_savings(agent_outputs)
        result = self.router.invoke(
            TaskType.RECOMMENDATION,
            prompt,
            system=self.SYSTEM,
            estimated_savings_usd=savings,
        )
        try:
            plan = json.loads(result["content"])
        except json.JSONDecodeError:
            plan = {"action_plan": [], "raw": result["content"]}
        return {
            "agent": "recommendation",
            "action_plan": plan,
            "model": result["model"],
            "usage": result["usage"],
        }

    @staticmethod
    def _estimate_total_savings(outputs: dict[str, Any]) -> float:
        opt = outputs.get("optimization", {}).get("recommendations", {})
        actions = opt.get("actions", [])
        return sum(float(a.get("estimated_savings", 0)) for a in actions)
