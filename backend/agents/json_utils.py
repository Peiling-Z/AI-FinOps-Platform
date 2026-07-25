"""Robust JSON parsing for LLM responses.

Live models (e.g. Gemini via Vertex) often wrap JSON in markdown code fences
(```json ... ```), which breaks a naive json.loads. Mock responses return clean
JSON, so this gap only surfaces in live mode. This helper strips fences and, as a
last resort, extracts the outermost JSON object/array before parsing.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def parse_llm_json(content: str) -> Any:
    """Parse JSON from an LLM string, tolerating markdown code fences.

    Raises json.JSONDecodeError if no valid JSON can be recovered, so callers
    can keep their existing ``except json.JSONDecodeError`` fallbacks.
    """
    if not isinstance(content, str):
        raise json.JSONDecodeError("content is not a string", str(content), 0)

    cleaned = _strip_code_fences(content).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        snippet = _extract_json_span(cleaned)
        if snippet is not None:
            return json.loads(snippet)
        raise


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        # Drop the opening fence line (``` or ```json) and any trailing fence.
        stripped = _FENCE_RE.sub("", stripped)
    return stripped


def _extract_json_span(text: str) -> str | None:
    """Return the substring from the first { or [ to its matching close, if any."""
    start = _first_json_start(text)
    if start is None:
        return None
    open_char = text[start]
    close_char = "}" if open_char == "{" else "]"
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _first_json_start(text: str) -> int | None:
    for i, ch in enumerate(text):
        if ch in "{[":
            return i
    return None
