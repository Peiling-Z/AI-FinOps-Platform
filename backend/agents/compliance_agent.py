"""Compliance Agent — FSA eligibility, deductions, and regulatory flags."""

from __future__ import annotations

import json
from typing import Any

from backend.agents.json_utils import parse_llm_json
from backend.router.model_router import ModelRouter, TaskType


class ComplianceAgent:
    SYSTEM = (
        "You are a US tax and benefits compliance assistant. Flag FSA/HSA eligible items, "
        "potential deduction issues, and compliance warnings. Return valid JSON only. "
        "This is informational — not professional tax advice."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, transactions: list[dict[str, Any]]) -> dict[str, Any]:
        prompt = f"Review for compliance:\n{json.dumps(transactions, indent=2)[:6000]}"
        result = self.router.invoke(TaskType.COMPLIANCE_CHECK, prompt, system=self.SYSTEM)
        try:
            compliance = parse_llm_json(result["content"])
        except json.JSONDecodeError:
            compliance = {"flags": [], "raw": result["content"]}
        return {
            "agent": "compliance",
            "compliance": compliance,
            "model": result["model"],
            "usage": result["usage"],
        }
