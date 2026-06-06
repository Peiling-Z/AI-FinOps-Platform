"""Document Agent — parse, classify, and extract structured data from financial documents."""

from __future__ import annotations

import json
from typing import Any

from backend.router.model_router import ModelRouter, TaskType


class DocumentAgent:
    SYSTEM = (
        "You are a financial document parser. Extract transactions, dates, amounts, "
        "merchants, and document type. Return valid JSON only."
    )

    def __init__(self, router: ModelRouter | None = None) -> None:
        self.router = router or ModelRouter()

    def run(self, raw_text: str, source: str = "unknown") -> dict[str, Any]:
        prompt = f"Source: {source}\n\nDocument text:\n{raw_text[:8000]}"
        result = self.router.invoke(TaskType.DOCUMENT_PARSE, prompt, system=self.SYSTEM)
        try:
            parsed = json.loads(result["content"])
        except json.JSONDecodeError:
            parsed = {"raw": result["content"], "parse_error": True}
        return {
            "agent": "document",
            "source": source,
            "extracted": parsed,
            "model": result["model"],
            "usage": result["usage"],
        }
