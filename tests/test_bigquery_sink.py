"""Tests for BigQuery cost sink."""

from unittest.mock import MagicMock, patch

from backend.analytics.bigquery_sink import BigQueryCostSink, reset_bigquery_sink
from backend.analytics.pipeline_context import pipeline_run
from backend.config import Settings
from backend.router.cost_tracker import UsageRecord


def _sample_record() -> UsageRecord:
    return UsageRecord(
        task_type="document_parse",
        model="gemini-2.0-flash-lite",
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.00002,
        estimated_savings_usd=0.0,
        roi=None,
        timestamp="2026-06-07T12:00:00+00:00",
    )


def test_sink_disabled_by_default():
    sink = BigQueryCostSink(Settings(bigquery_enabled=False))
    assert sink.enabled is False
    sink.insert(_sample_record(), llm_provider="vertex")  # no-op


def test_sink_row_includes_pipeline_run_id():
    settings = Settings(
        bigquery_enabled=True,
        bigquery_project="test-project",
        bigquery_auto_create=False,
    )
    sink = BigQueryCostSink(settings)
    with pipeline_run("run-abc-123"):
        row = sink.record_to_row(_sample_record(), llm_provider="vertex")
    assert row["pipeline_run_id"] == "run-abc-123"
    assert row["task_type"] == "document_parse"
    assert row["total_tokens"] == 150
    assert row["llm_provider"] == "vertex"


@patch("backend.analytics.bigquery_sink.BigQueryCostSink._get_client")
def test_sink_insert_calls_bigquery(mock_get_client):
    mock_client = MagicMock()
    mock_client.insert_rows_json.return_value = []
    mock_get_client.return_value = mock_client

    settings = Settings(
        bigquery_enabled=True,
        bigquery_project="test-project",
        bigquery_auto_create=False,
    )
    sink = BigQueryCostSink(settings)
    sink._table_ready = True
    sink.insert(_sample_record(), llm_provider="vertex")

    mock_client.insert_rows_json.assert_called_once()
    table_id, rows = mock_client.insert_rows_json.call_args[0]
    assert table_id == "test-project.finops_analytics.llm_usage"
    assert rows[0]["model"] == "gemini-2.0-flash-lite"

    reset_bigquery_sink()
