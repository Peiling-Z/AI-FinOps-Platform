"""BigQuery sink for LLM usage / cost records."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.analytics.pipeline_context import get_pipeline_run_id
from backend.config import Settings, get_settings
from backend.router.cost_tracker import UsageRecord

logger = logging.getLogger(__name__)

LLM_USAGE_SCHEMA: list[dict[str, str]] = [
    {"name": "record_id", "type": "STRING", "mode": "REQUIRED"},
    {"name": "pipeline_run_id", "type": "STRING", "mode": "NULLABLE"},
    {"name": "task_type", "type": "STRING", "mode": "REQUIRED"},
    {"name": "model", "type": "STRING", "mode": "REQUIRED"},
    {"name": "llm_provider", "type": "STRING", "mode": "REQUIRED"},
    {"name": "input_tokens", "type": "INT64", "mode": "REQUIRED"},
    {"name": "output_tokens", "type": "INT64", "mode": "REQUIRED"},
    {"name": "total_tokens", "type": "INT64", "mode": "REQUIRED"},
    {"name": "cost_usd", "type": "FLOAT64", "mode": "REQUIRED"},
    {"name": "quality_score", "type": "FLOAT64", "mode": "NULLABLE"},
    {"name": "estimated_savings_usd", "type": "FLOAT64", "mode": "NULLABLE"},
    {"name": "roi", "type": "FLOAT64", "mode": "NULLABLE"},
    {"name": "recorded_at", "type": "TIMESTAMP", "mode": "REQUIRED"},
]


class BigQueryCostSink:
    """Stream LLM usage records into BigQuery for FinOps analytics."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: Any = None
        self._table_ready = False

    @property
    def project(self) -> str | None:
        return self.settings.bigquery_project or self.settings.vertex_ai_project

    @property
    def table_id(self) -> str:
        return f"{self.project}.{self.settings.bigquery_dataset}.{self.settings.bigquery_table}"

    @property
    def enabled(self) -> bool:
        return bool(self.settings.bigquery_enabled and self.project)

    def status(self) -> dict[str, Any]:
        return {
            "bigquery_enabled": self.enabled,
            "project": self.project,
            "dataset": self.settings.bigquery_dataset,
            "table": self.settings.bigquery_table,
            "table_id": self.table_id if self.enabled else None,
            "auto_create": self.settings.bigquery_auto_create,
        }

    def _get_client(self) -> Any:
        if self._client is None:
            from google.cloud import bigquery

            self._client = bigquery.Client(project=self.project)
        return self._client

    def ensure_table(self) -> None:
        """Create dataset and table if they do not exist."""
        if not self.enabled or self._table_ready or not self.settings.bigquery_auto_create:
            return

        from google.cloud import bigquery

        client = self._get_client()
        dataset_ref = bigquery.Dataset(f"{self.project}.{self.settings.bigquery_dataset}")
        dataset_ref.location = self.settings.bigquery_location
        client.create_dataset(dataset_ref, exists_ok=True)

        schema = [bigquery.SchemaField(**field) for field in LLM_USAGE_SCHEMA]
        table_ref = bigquery.Table(self.table_id, schema=schema)
        table_ref.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="recorded_at",
        )
        client.create_table(table_ref, exists_ok=True)
        self._table_ready = True
        logger.info("BigQuery table ready: %s", self.table_id)

    def record_to_row(self, record: UsageRecord, *, llm_provider: str) -> dict[str, Any]:
        return {
            "record_id": str(uuid.uuid4()),
            "pipeline_run_id": get_pipeline_run_id(),
            "task_type": record.task_type,
            "model": record.model,
            "llm_provider": llm_provider,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "total_tokens": record.input_tokens + record.output_tokens,
            "cost_usd": record.cost_usd,
            "quality_score": record.quality_score,
            "estimated_savings_usd": record.estimated_savings_usd,
            "roi": record.roi,
            "recorded_at": record.timestamp or datetime.now(UTC).isoformat(),
        }

    def insert(self, record: UsageRecord, *, llm_provider: str) -> None:
        """Insert one usage record. Failures are logged, not raised."""
        if not self.enabled:
            return

        try:
            self.ensure_table()
            client = self._get_client()
            row = self.record_to_row(record, llm_provider=llm_provider)
            errors = client.insert_rows_json(self.table_id, [row])
            if errors:
                logger.error("BigQuery insert errors: %s", errors)
            else:
                logger.debug("BigQuery insert ok: task=%s model=%s", record.task_type, record.model)
        except Exception as exc:  # noqa: BLE001 — analytics must not break the pipeline
            logger.warning("BigQuery sink failed: %s", exc)


_sink: BigQueryCostSink | None = None


def get_bigquery_sink(settings: Settings | None = None) -> BigQueryCostSink:
    global _sink
    if _sink is None or (settings is not None):
        _sink = BigQueryCostSink(settings)
    return _sink


def reset_bigquery_sink() -> None:
    global _sink
    _sink = None
