-- BigQuery schema for LLM usage / cost analytics
-- Dataset: finops_analytics  Table: llm_usage

CREATE SCHEMA IF NOT EXISTS `{project}.finops_analytics`
OPTIONS (
  location = "US",
  description = "AI FinOps Platform — LLM cost and token analytics"
);

CREATE TABLE IF NOT EXISTS `{project}.finops_analytics.llm_usage` (
  record_id             STRING    NOT NULL,
  pipeline_run_id       STRING,
  task_type             STRING    NOT NULL,
  model                 STRING    NOT NULL,
  llm_provider          STRING    NOT NULL,
  input_tokens          INT64     NOT NULL,
  output_tokens         INT64     NOT NULL,
  total_tokens          INT64     NOT NULL,
  cost_usd              FLOAT64   NOT NULL,
  quality_score         FLOAT64,
  estimated_savings_usd FLOAT64,
  roi                   FLOAT64,
  recorded_at           TIMESTAMP NOT NULL
)
PARTITION BY DATE(recorded_at)
OPTIONS (
  description = "Per-call LLM usage records from the cost-aware model router"
);
