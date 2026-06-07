"""Pipeline-scoped context for analytics (e.g. BigQuery run grouping)."""

from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager

pipeline_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "pipeline_run_id",
    default=None,
)


def new_run_id() -> str:
    return str(uuid.uuid4())


@contextmanager
def pipeline_run(run_id: str | None = None):
    """Bind a pipeline run ID for the duration of a graph execution."""
    token = pipeline_run_id.set(run_id or new_run_id())
    try:
        yield pipeline_run_id.get()
    finally:
        pipeline_run_id.reset(token)


def get_pipeline_run_id() -> str | None:
    return pipeline_run_id.get()
