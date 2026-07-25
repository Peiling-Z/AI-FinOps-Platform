"""Recommendation Agent — synthesize agent outputs into a prioritized action plan."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.json_utils import parse_llm_json
from backend.router.model_router import ModelRouter, TaskType


class RecommendationAgent:
    """Prioritizes existing findings only.

    Savings are attributed to the optimization agent, so this synthesis step
    records cost with zero savings to keep pipeline ROI from double counting the
    same opportunities.
    """

    SYSTEM = (
        "You are a financial advisor synthesizer. Combine analysis, optimization, and "
        "compliance findings into a prioritized action plan with scores 1-5. "
        "Return valid JSON with 'action_plan' list."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, agent_outputs: dict[str, Any]) -> dict[str, Any]:
        prompt = f"Synthesize these agent outputs:\n{json.dumps(agent_outputs, indent=2)[:8000]}"
        result = self.router.invoke(
            TaskType.RECOMMENDATION,
            prompt,
            system=self.SYSTEM,
        )
        try:
            plan = parse_llm_json(result["content"])
        except json.JSONDecodeError:
            plan = {"action_plan": [], "raw": result["content"]}
        return {
            "agent": "recommendation",
            "action_plan": plan,
            "model": result["model"],
            "usage": result["usage"],
        }
