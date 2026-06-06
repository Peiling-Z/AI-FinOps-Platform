"""Token usage tracking and ROI calculation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

# Per-million-token pricing (USD) — update as providers change rates
MODEL_PRICING: dict[str, dict[str, float]] = {
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "claude-3-5-sonnet": {"input": 3.00, "output": 15.00},
}


@dataclass
class UsageRecord:
    task_type: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    quality_score: float | None = None
    estimated_savings_usd: float = 0.0
    roi: float | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def model_dump(self) -> dict:
        return {
            "task_type": self.task_type,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "quality_score": self.quality_score,
            "estimated_savings_usd": self.estimated_savings_usd,
            "roi": self.roi,
            "timestamp": self.timestamp,
        }


class CostTracker:
    """Accumulates per-call usage and computes aggregate ROI."""

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    @staticmethod
    def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(model, {"input": 1.0, "output": 3.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    @staticmethod
    def compute_roi(cost_usd: float, estimated_savings_usd: float) -> float | None:
        if cost_usd <= 0:
            return None
        return round(estimated_savings_usd / cost_usd, 2)

    def record(
        self,
        *,
        task_type: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        quality_score: float | None = None,
        estimated_savings_usd: float = 0.0,
    ) -> UsageRecord:
        cost = self.compute_cost(model, input_tokens, output_tokens)
        roi = self.compute_roi(cost, estimated_savings_usd)
        record = UsageRecord(
            task_type=task_type,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            quality_score=quality_score,
            estimated_savings_usd=estimated_savings_usd,
            roi=roi,
        )
        self.records.append(record)
        return record

    def summary(self) -> dict:
        total_cost = sum(r.cost_usd for r in self.records)
        total_savings = sum(r.estimated_savings_usd for r in self.records)
        by_model: dict[str, dict] = {}
        for r in self.records:
            bucket = by_model.setdefault(r.model, {"calls": 0, "cost_usd": 0.0, "tokens": 0})
            bucket["calls"] += 1
            bucket["cost_usd"] += r.cost_usd
            bucket["tokens"] += r.input_tokens + r.output_tokens

        return {
            "total_calls": len(self.records),
            "total_cost_usd": round(total_cost, 4),
            "total_estimated_savings_usd": round(total_savings, 2),
            "aggregate_roi": self.compute_roi(total_cost, total_savings),
            "by_model": {k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in by_model.items()},
            "records": [r.model_dump() for r in self.records],
        }
