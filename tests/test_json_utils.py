"""Tests for robust LLM JSON parsing (markdown fence tolerance)."""

import json

import pytest

from backend.agents.json_utils import parse_llm_json


def test_plain_json():
    assert parse_llm_json('{"a": 1}') == {"a": 1}


def test_json_code_fence():
    content = '```json\n{"transactions": [{"merchant": "Starbucks"}]}\n```'
    assert parse_llm_json(content) == {"transactions": [{"merchant": "Starbucks"}]}


def test_bare_code_fence():
    content = '```\n{"risk_score": 0.1}\n```'
    assert parse_llm_json(content) == {"risk_score": 0.1}


def test_json_array_fence():
    content = '```json\n[{"amount": -5.75}]\n```'
    assert parse_llm_json(content) == [{"amount": -5.75}]


def test_prose_wrapped_json_object():
    content = 'Here is the result:\n```json\n{"ok": true}\n```\nHope that helps!'
    assert parse_llm_json(content) == {"ok": True}


def test_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        parse_llm_json("Here's a plain english breakdown with no JSON at all.")
