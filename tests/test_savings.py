"""Tests for savings extraction — the numerator of the pipeline ROI story."""

from backend.agents.savings import savings_from_content, total_savings_usd


def test_legacy_estimated_savings_key():
    payload = {"actions": [{"estimated_savings": 240}, {"estimated_savings": 180}]}
    assert total_savings_usd(payload) == 420.0


def test_live_annual_savings_key():
    payload = {
        "actions": [
            {"estimated_annual_savings_usd": 180},
            {"estimated_annual_savings_usd": 120},
            {"estimated_annual_savings_usd": 120},
        ]
    }
    assert total_savings_usd(payload) == 420.0


def test_monthly_savings_annualized():
    payload = {"actions": [{"estimated_monthly_savings_usd": 10}]}
    assert total_savings_usd(payload) == 120.0


def test_currency_string_is_parsed():
    payload = {"actions": [{"estimated_annual_savings_usd": "$1,200"}]}
    assert total_savings_usd(payload) == 1200.0


def test_action_plan_key_supported():
    payload = {"action_plan": [{"savings_usd": 50}]}
    assert total_savings_usd(payload) == 50.0


def test_bare_list_payload():
    assert total_savings_usd([{"savings": 25}, {"savings": 25}]) == 50.0


def test_unrecognized_shape_contributes_zero():
    payload = {"actions": [{"action": "Do a thing", "priority": 1}]}
    assert total_savings_usd(payload) == 0.0


def test_no_actions_is_zero():
    assert total_savings_usd({"summary": "nothing to do"}) == 0.0


def test_savings_from_fenced_content():
    content = '```json\n{"actions": [{"estimated_annual_savings_usd": 300}]}\n```'
    assert savings_from_content(content) == 300.0


def test_savings_from_unparseable_content_is_zero():
    assert savings_from_content("No JSON here, just prose.") == 0.0
