"""Extract estimated savings from LLM optimization output.

Models are inconsistent about the key and format they use for a savings figure
(`estimated_savings`, `estimated_annual_savings_usd`, `"$180"`, ...), so ROI must
not depend on one exact spelling. Anything unrecognized contributes 0 rather than
inflating the savings total.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from backend.agents.json_utils import parse_llm_json

SAVINGS_KEYS: tuple[str, ...] = (
    "estimated_savings_usd",
    "estimated_annual_savings_usd",
    "estimated_monthly_savings_usd",
    "estimated_savings",
    "estimated_annual_savings",
    "annual_savings_usd",
    "annual_savings",
    "monthly_savings_usd",
    "savings_usd",
    "savings",
)

ACTION_LIST_KEYS: tuple[str, ...] = ("actions", "action_plan", "opportunities", "recommendations")

_MONTHLY_KEYS = ("monthly",)
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def total_savings_usd(payload: Any) -> float:
    """Sum annualized savings across the action list in an LLM response payload."""
    actions = _find_actions(payload)
    return round(sum(_action_savings(a) for a in actions), 2)


def savings_from_content(content: str) -> float:
    """Parse an LLM response string and total its savings; 0.0 if unparseable."""
    try:
        payload = parse_llm_json(content)
    except (json.JSONDecodeError, ValueError):
        return 0.0
    return total_savings_usd(payload)


def _find_actions(payload: Any) -> list[Mapping[str, Any]]:
    if isinstance(payload, Mapping):
        for key in ACTION_LIST_KEYS:
            value = payload.get(key)
            if isinstance(value, Sequence) and not isinstance(value, str):
                return [item for item in value if isinstance(item, Mapping)]
            # Nested one level, e.g. {"recommendations": {"actions": [...]}}
            if isinstance(value, Mapping):
                nested = _find_actions(value)
                if nested:
                    return nested
        return []
    if isinstance(payload, Sequence) and not isinstance(payload, str):
        return [item for item in payload if isinstance(item, Mapping)]
    return []


def _action_savings(action: Mapping[str, Any]) -> float:
    for key in SAVINGS_KEYS:
        if key not in action:
            continue
        amount = _coerce_amount(action[key])
        if amount is None:
            continue
        # Normalize monthly figures so the total is always annualized.
        if any(token in key for token in _MONTHLY_KEYS):
            amount *= 12
        return amount
    return 0.0


def _coerce_amount(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = _NUMBER_RE.search(value.replace(",", ""))
        if match:
            return float(match.group())
    return None
