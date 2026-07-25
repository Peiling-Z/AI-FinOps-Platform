"""Cost-aware model router — routes tasks to the optimal LLM by complexity."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import Settings, get_settings
from backend.observability.langsmith_setup import build_invoke_config
from backend.router.cost_tracker import CostTracker, UsageRecord

logger = logging.getLogger(__name__)


class TaskType(StrEnum):
    DOCUMENT_PARSE = "document_parse"
    ANOMALY_DETECTION = "anomaly_detection"
    DEEP_ANALYSIS = "deep_analysis"
    RECOMMENDATION = "recommendation"
    COMPLIANCE_CHECK = "compliance_check"


class RoutingRules:
    """Task-type → model mapping for multi-provider and Vertex-only modes."""

    MULTI: dict[TaskType, str] = {
        TaskType.DOCUMENT_PARSE: "gemini-1.5-flash",
        TaskType.ANOMALY_DETECTION: "claude-3-5-haiku",
        TaskType.DEEP_ANALYSIS: "gpt-4o",
        TaskType.RECOMMENDATION: "claude-3-5-sonnet",
        TaskType.COMPLIANCE_CHECK: "claude-3-5-haiku",
    }

    VERTEX: dict[TaskType, str] = {
        TaskType.DOCUMENT_PARSE: "gemini-2.5-flash-lite",
        TaskType.ANOMALY_DETECTION: "gemini-2.5-flash",
        TaskType.DEEP_ANALYSIS: "gemini-2.5-pro",
        TaskType.RECOMMENDATION: "gemini-2.5-pro",
        TaskType.COMPLIANCE_CHECK: "gemini-2.5-flash",
    }

    # Backward-compatible alias used in docs/tests
    RULES = MULTI

    @classmethod
    def resolve(cls, task_type: TaskType | str, provider: str = "multi") -> str:
        key = TaskType(task_type) if isinstance(task_type, str) else task_type
        table = cls.VERTEX if provider == "vertex" else cls.MULTI
        return table[key]

    @classmethod
    def active_rules(cls, provider: str) -> dict[str, str]:
        table = cls.VERTEX if provider == "vertex" else cls.MULTI
        return {k.value: v for k, v in table.items()}


def build_cost_tracker(settings: Settings | None = None) -> CostTracker:
    """Build in-memory tracker with optional BigQuery sink."""
    from backend.analytics.bigquery_sink import get_bigquery_sink

    settings = settings or get_settings()
    sink = get_bigquery_sink(settings)
    if sink.enabled:
        provider = settings.llm_provider
        return CostTracker(on_record=lambda record: sink.insert(record, llm_provider=provider))
    return CostTracker()


class ModelRouter:
    """Select model by task type, invoke (or mock), and record usage."""

    def __init__(
        self,
        settings: Settings | None = None,
        cost_tracker: CostTracker | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cost_tracker = cost_tracker or build_cost_tracker(self.settings)
        self._ensure_google_credentials()

    def _ensure_google_credentials(self) -> None:
        creds = self.settings.google_application_credentials
        if creds and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds

    def select_model(self, task_type: TaskType | str) -> str:
        return RoutingRules.resolve(task_type, self.settings.llm_provider)

    def invoke(
        self,
        task_type: TaskType | str,
        prompt: str,
        *,
        system: str | None = None,
        quality_score: float | None = None,
        estimated_savings_usd: float = 0.0,
        savings_extractor: Callable[[str], float] | None = None,
    ) -> dict[str, Any]:
        model = self.select_model(task_type)
        task_key = TaskType(task_type).value if isinstance(task_type, TaskType) else task_type

        if self.settings.mock_llm:
            content, input_tokens, output_tokens = self._mock_response(task_key, prompt)
        else:
            content, input_tokens, output_tokens = self._live_invoke(
                model, prompt, system, task_key
            )

        if savings_extractor is not None:
            try:
                estimated_savings_usd = savings_extractor(content)
            except Exception as exc:  # noqa: BLE001 — bad savings math must not fail the call
                logger.warning("Savings extraction failed for %s: %s", task_key, exc)

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
            # Mirrors the field names live Gemini actually returns, so mock runs
            # exercise the same parsing path as production.
            "recommendation": {
                "actions": [
                    {
                        "action": "Switch to high-yield savings",
                        "priority": 1,
                        "estimated_annual_savings_usd": 240,
                    },
                    {
                        "action": "Consolidate streaming subscriptions",
                        "priority": 2,
                        "estimated_annual_savings_usd": 180,
                    },
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
        task_type: str,
    ) -> tuple[str, int, int]:
        """Route to the appropriate provider SDK with LangSmith callbacks."""
        if model.startswith("gpt"):
            return self._invoke_openai(model, prompt, system, task_type)
        if model.startswith("claude"):
            return self._invoke_anthropic(model, prompt, system, task_type)
        if model.startswith("gemini"):
            return self._invoke_vertex(model, prompt, system, task_type)
        raise ValueError(f"Unsupported model: {model}")

    def _invoke_config(self, task_type: str) -> dict[str, Any]:
        return build_invoke_config(
            task_type,
            llm_provider=self.settings.llm_provider,
            settings=self.settings,
        )

    @staticmethod
    def _extract_token_usage(response: Any, fallback_input: int, fallback_output: int) -> tuple[int, int]:
        meta = getattr(response, "response_metadata", None) or {}
        usage = meta.get("usage_metadata") or meta.get("token_usage") or meta.get("usage") or {}
        input_tokens = (
            usage.get("input_tokens")
            or usage.get("prompt_tokens")
            or usage.get("input_token_count")
            or fallback_input
        )
        output_tokens = (
            usage.get("output_tokens")
            or usage.get("completion_tokens")
            or usage.get("output_token_count")
            or fallback_output
        )
        return int(input_tokens), int(output_tokens)

    def _build_messages(self, prompt: str, system: str | None) -> list[Any]:
        messages: list[Any] = []
        if system:
            messages.append(SystemMessage(content=system))
        messages.append(HumanMessage(content=prompt))
        return messages

    def _invoke_openai(
        self, model: str, prompt: str, system: str | None, task_type: str
    ) -> tuple[str, int, int]:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI models")

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(model=model, api_key=self.settings.openai_api_key)
        messages = self._build_messages(prompt, system)
        response = llm.invoke(messages, config=self._invoke_config(task_type))
        in_t, out_t = self._extract_token_usage(response, len(prompt) // 4, len(response.content) // 4)
        return response.content, in_t, out_t

    def _invoke_anthropic(
        self, model: str, prompt: str, system: str | None, task_type: str
    ) -> tuple[str, int, int]:
        if not self.settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic models")

        from langchain_anthropic import ChatAnthropic

        llm = ChatAnthropic(model=model, api_key=self.settings.anthropic_api_key)
        messages = self._build_messages(prompt, system)
        response = llm.invoke(messages, config=self._invoke_config(task_type))
        in_t, out_t = self._extract_token_usage(response, len(prompt) // 4, len(response.content) // 4)
        return response.content, in_t, out_t

    def _invoke_vertex(
        self, model: str, prompt: str, system: str | None, task_type: str
    ) -> tuple[str, int, int]:
        if not self.settings.vertex_ai_project:
            raise ValueError("VERTEX_AI_PROJECT is required for Vertex AI models")

        from langchain_google_vertexai import ChatVertexAI

        llm = ChatVertexAI(
            model_name=model,
            project=self.settings.vertex_ai_project,
            location=self.settings.vertex_ai_location,
            temperature=0.2,
        )
        messages = self._build_messages(prompt, system)
        response = llm.invoke(messages, config=self._invoke_config(task_type))
        in_t, out_t = self._extract_token_usage(response, len(prompt) // 4, len(response.content) // 4)
        return response.content, in_t, out_t

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
