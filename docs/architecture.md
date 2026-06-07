# Architecture

## Overview

AI FinOps Platform is a **multi-agent household finance system** that ingests data from multiple sources (bank statements, bills, Plaid, CSV), routes each cognitive task to the most cost-effective LLM, and synthesizes actionable recommendations with full cost/ROI tracking.

```
┌─────────────────────────────────────────────────────────────────┐
│  Data Ingestion                                                 │
│  Bank PDF · Bills · Plaid API · CSV / Manual                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  LangGraph Orchestrator (State Machine)                         │
│  ingest → document → analysis → optimization → compliance       │
│                              → recommendation                    │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Model Router                                                   │
│  document_parse    → gemini-1.5-flash   (high volume, cheap)    │
│  anomaly_detection → claude-3-5-haiku    (fast reasoning)        │
│  deep_analysis     → gpt-4o              (complex judgment)      │
│  recommendation    → claude-3-5-sonnet   (quality output)        │
└────────────────────────────┬────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Dashboard + Savings Report                                     │
│  Streamlit MVP → Next.js (planned)                              │
└─────────────────────────────────────────────────────────────────┘

        ┌──────────────────────────────────┐
        │  LangSmith · Cost Tracker · Eval │  (observability sidebar)
        └──────────────────────────────────┘
```

## Agent Responsibilities

| Agent | Task Type | Vertex Model | Multi-Provider Model | Purpose |
|-------|-----------|--------------|----------------------|---------|
| Document | `document_parse` | gemini-2.0-flash-lite | gemini-1.5-flash | Parse PDF/CSV, classify, extract transactions |
| Analysis | `anomaly_detection`, `deep_analysis` | gemini-2.0-flash / gemini-1.5-pro | haiku / gpt-4o | Trends, anomalies, risk scoring |
| Optimization | `recommendation` | gemini-1.5-pro | claude-3-5-sonnet | Savings opportunities |
| Compliance | `compliance_check` | gemini-2.0-flash | claude-3-5-haiku | FSA/HSA flags, deduction hints |
| Recommendation | `recommendation` | gemini-1.5-pro | claude-3-5-sonnet | Prioritized action plan |

Set `LLM_PROVIDER=vertex` (default) for all-Gemini routing via Vertex AI, or `LLM_PROVIDER=multi` for cross-provider cost optimization.

## Model Router — Design Rationale

The router is the **differentiator** of this project:

1. **Task-aware routing** — Not every step needs GPT-4o. Parsing uses Flash; deep analysis uses GPT-4o.
2. **Per-call telemetry** — Every invocation records model, tokens, cost, quality score, estimated savings.
3. **ROI calculation** — `ROI = estimated_savings_usd / llm_cost_usd` aggregated per pipeline run.
4. **Mock mode** — `MOCK_LLM=true` enables local dev, CI, and demos without API keys.

## State Machine (LangGraph)

```python
FinOpsState = {
    raw_input, source,
    document_result, analysis_result,
    optimization_result, compliance_result,
    recommendation_result,
    errors[], cost_summary
}
```

Linear DAG with error accumulation — each node catches exceptions and appends to `errors[]` without halting downstream nodes (graceful degradation).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/router/rules` | Current routing table |
| GET | `/router/costs` | Accumulated cost/ROI |
| POST | `/analyze` | Run full pipeline on text |
| POST | `/ingest/pdf` | Upload PDF → pipeline |
| POST | `/ingest/csv` | Upload CSV → pipeline |
| GET | `/ingest/plaid/mock` | Sandbox Plaid transactions |
| GET | `/analytics/bigquery/status` | BigQuery sink configuration |

## BigQuery Cost Sink

Each LLM invocation writes one row to `{project}.finops_analytics.llm_usage`:

```
ModelRouter.invoke → CostTracker.record → BigQueryCostSink.insert
                              ↑
                   pipeline_run_id (LangGraph run context)
```

- **Partitioned** by `recorded_at` (daily)
- **Grouped** by `pipeline_run_id` for per-run ROI analysis
- **Fail-safe** — sink errors are logged, never break the agent pipeline
- **Sample queries** — `infra/bigquery/queries.sql`

## Deployment (GCP)

- **Cloud Run** — Stateless API container
- **Cloud Build** — CI/CD via `infra/cloudbuild.yaml`
- **Terraform** — IaC in `infra/terraform/`
- **Vertex AI** — Production LLM provider (Gemini)
- **BigQuery** — LLM cost / token analytics warehouse

## Roadmap

- [ ] Next.js frontend replacing Streamlit MVP
- [ ] Weaviate/Pinecone for transaction embedding & semantic search
- [ ] Real Plaid Link OAuth flow
- [ ] LangSmith eval datasets for agent quality regression
- [x] BigQuery sink for cost analytics
- [ ] BigQuery Looker Studio dashboard
