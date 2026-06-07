"""Cost-aware model router — routes tasks to the optimal LLM by complexity."""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from typing import Any

from backend.config import Settings, get_settings
from backend.router.cost_tracker import CostTracker, UsageRecord

logger = logging.getLogger(__name__)


class TaskType(StrEnum):
    DOCUMENT_PARSE = "document_parse"
    ANOMALY_DETECTION = "anomaly_detection"
    DEEP_ANALYSIS = "deep_analysis"
    RECOMMENDATION = "recommendation"
    COMPLIANCE_CHECK = "compliance_check"


class RoutingRules:
    """Static routing table — the core cost/quality tradeoff."""

    RULES: dict[TaskType, str] = {
        TaskType.DOCUMENT_PARSE: "gemini-1.5-flash",
        TaskType.ANOMALY_DETECTION: "claude-3-5-haiku",
        TaskType.DEEP_ANALYSIS: "gpt-4o",
        TaskType.RECOMMENDATION: "claude-3-5-sonnet",
        TaskType.COMPLIANCE_CHECK: "claude-3-5-haiku",
    }

    @classmethod
    def resolve(cls, task_type: TaskType | str) -> str:
        key = TaskType(task_type) if isinstance(task_type, str) else task_type
        return cls.RULES[key]


class ModelRouter:
    """Select model by task type, invoke (or mock), and record usage."""

    def __init__(
        self,
        settings: Settings | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cost_tracker = cost_tracker or CostTracker()

    def select_model(self, task_type: TaskType | str) -> str:
        return RoutingRules.resolve(task_type)

    def invoke(
        self,
        task_type: TaskType | str,
        prompt: str,
        *,
        system: str | None = None,
        quality_score: float | None = None,
        estimated_savings_usd: float = 0.0,
    ) -> dict[str, Any]:
        model = self.select_model(task_type)
        task_key = TaskType(task_type).value if isinstance(task_type, TaskType) else task_type

        if self.settings.mock_llm:
            content, input_tokens, output_tokens = self._mock_response(task_key, prompt)
        else:
            content, input_tokens, output_tokens = self._live_invoke(model, prompt, system)

        record = self.cost_tracker.record(
            task_type=task_key,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            quality_score=quality_score,
            estimated_savings_usd=estimated_savings_usd,
        )

        return {
            "content": content,
            "model": model,
            "task_type": task_key,
            "usage": record.model_dump(),
        }

    def _mock_response(self, task_type: str, prompt: str) -> tuple[str, int, int]:
        """Deterministic mock for local dev, demos, and CI."""
        snippets = {
            "document_parse": {
                "transactions": [
                    {"date": "2026-05-01", "merchant": "Whole Foods", "amount": -127.43, "category": "groceries"},
                    {"date": "2026-05-03", "merchant": "Netflix", "amount": -15.99, "category": "entertainment"},
                ],
                "document_type": "bank_statement",
            },
            "anomaly_detection": {
                "anomalies": [
                    {"description": "Duplicate charge at Amazon ($49.99)", "severity": "medium", "amount": 49.99},
                ],
                "risk_score": 0.32,
            },
            "deep_analysis": {
                "monthly_trend": "spending up 12% vs prior month",
                "top_categories": ["housing", "groceries", "transport"],
                "cash_flow": "positive",
            },
            "recommendation": {
                "actions": [
                    {"title": "Switch to high-yield savings", "priority": 1, "estimated_savings": 240},
                    {"title": "Consolidate streaming subscriptions", "priority": 2, "estimated_savings": 180},
                ],
            },
            "compliance_check": {
                "fsa_eligible": [{"item": "Contact lenses", "amount": 89.0}],
                "flags": [],
            },
        }
        payload = snippets.get(task_type, {"summary": "processed", "input_chars": len(prompt)})
        content = json.dumps(payload, indent=2)
        return content, max(len(prompt) // 4, 50), max(len(content) // 4, 80)

    def _live_invoke(
        self,
        model: str,
        prompt: str,
        system: str | None,
    ) -> tuple[str, int, int]:
        """Route to the appropriate provider SDK."""
        if model.startswith("gpt"):
            return self._invoke_openai(model, prompt, system)
        if model.startswith("claude"):
            return self._invoke_anthropic(model, prompt, system)
        if model.startswith("gemini"):
            return self._invoke_vertex(model, prompt, system)
        raise ValueError(f"Unsupported model: {model}")

    def _invoke_openai(self, model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=model, api_key=self.settings.openai_api_key)
        messages = []
        if system:
            messages.append(("system", system))
        messages.append(("human", prompt))
        response = llm.invoke(messages)
        usage = response.response_metadata.get("token_usage", {})
        return (
            response.content,
            usage.get("prompt_tokens", 0),
            usage.get("completion_tokens", 0),
        )

    def _invoke_anthropic(self, model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model=model, api_key=self.settings.anthropic_api_key)
        kwargs: dict[str, Any] = {"messages": [("human", prompt)]}
        if system:
            kwargs["system"] = system
        response = llm.invoke(prompt if not system else prompt)
        usage = response.response_metadata.get("usage", {})
        return (
            response.content,
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
        )

    def _invoke_vertex(self, model: str, prompt: str, system: str | None) -> tuple[str, int, int]:
        from langchain_google_vertexai import ChatVertexAI

        llm = ChatVertexAI(
            model_name=model,
            project=self.settings.vertex_ai_project,
            location=self.settings.vertex_ai_location,
        )
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = llm.invoke(full_prompt)
        meta = response.response_metadata or {}
        return (
            response.content,
            meta.get("input_tokens", len(full_prompt) // 4),
            meta.get("output_tokens", len(response.content) // 4),
        )

    def summary(self) -> dict[str, Any]:
        return self.cost_tracker.summary()


# Process-level singleton — accumulates costs across API requests
_shared_router: ModelRouter | None = None


def get_shared_router() -> ModelRouter:
    """Return the API-scoped router so /router/costs reflects pipeline runs."""
    global _shared_router
    if _shared_router is None:
        _shared_router = ModelRouter()
    return _shared_router


def reset_shared_router() -> None:
    """Reset accumulated costs (useful for tests)."""
    global _shared_router
    _shared_router = None
