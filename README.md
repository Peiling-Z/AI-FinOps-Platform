# AI FinOps Platform

> **Multi-agent household finance dashboard** with cost-aware LLM routing — built for FinTech AI engineering portfolios.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/orchestration-LangGraph-purple.svg)](https://github.com/langchain-ai/langgraph)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green.svg)](https://fastapi.tiangolo.com/)
[![GCP](https://img.shields.io/badge/deploy-Cloud%20Run-4285F4.svg)](https://cloud.google.com/run)

---

## Why This Project?

Most "AI agent" demos force multi-agent patterns onto trivial tasks. **Household finance is different** — it naturally spans multiple data sources (bank feeds, PDF bills, manual CSV), requires specialized cognitive tasks (parsing, anomaly detection, compliance, optimization), and has a measurable ROI story (LLM cost vs. savings found).

This project demonstrates skills relevant to **AI Platform Engineer**, **AI Agent Engineer**, and **FinTech AI Engineer** roles:

| Capability | Implementation |
|------------|----------------|
| Multi-Agent Orchestration | LangGraph state machine with 5 specialized agents |
| Cost-Aware Model Routing | Task-type → model mapping with token/cost/ROI tracking |
| Regulated Workflow Automation | Compliance agent (FSA/HSA flags, deduction hints) |
| Data Pipeline | PDF/CSV/Plaid ingestion → structured transactions |
| Cloud-Native Deployment | Docker, Cloud Run, Cloud Build, Terraform |
| Observability | LangSmith hooks, per-call cost tracker, eval suite |

---

## Architecture

```
Bank PDF · Bills · Plaid · CSV
            │
            ▼
   LangGraph Orchestrator ──► Model Router ──► Vertex AI / OpenAI / Anthropic
            │                        │
   Document → Analysis → Optimization → Compliance → Recommendation
            │                        │
            ▼                        ▼
     Dashboard + Savings Report   Cost Tracker + ROI
```

See [docs/architecture.md](docs/architecture.md) for full design details.

---

## Model Router (Core Differentiator)

Routes each task to the optimal model — balancing **cost vs. quality**:

| Task Type | Model | Rationale |
|-----------|-------|-----------|
| `document_parse` | gemini-1.5-flash | High volume, low cost |
| `anomaly_detection` | claude-3-5-haiku | Fast reasoning |
| `deep_analysis` | gpt-4o | Complex financial judgment |
| `recommendation` | claude-3-5-sonnet | High-quality action plans |
| `compliance_check` | claude-3-5-haiku | Structured rule matching |

Every call records: **model, tokens, cost, quality score, estimated savings → ROI**.

Example ROI output from a pipeline run:

```json
{
  "total_cost_usd": 0.0042,
  "total_estimated_savings_usd": 420.0,
  "aggregate_roi": 100000.0,
  "by_model": {
    "gemini-1.5-flash": {"calls": 1, "cost_usd": 0.0001, "tokens": 230},
    "claude-3-5-sonnet": {"calls": 2, "cost_usd": 0.0038, "tokens": 890}
  }
}
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- (Optional) API keys for live LLM inference

### 1. Clone & Install

```bash
git clone https://github.com/Peiling-Z/AI-FinOps-Platform.git
cd AI-FinOps-Platform
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Run API (Mock Mode — no API keys needed)

```bash
uvicorn backend.api.main:app --reload --port 8000
```

Open http://localhost:8000/docs for Swagger UI.

### 3. Run Dashboard

```bash
streamlit run frontend/app.py
```

### 4. Run Tests

```bash
pytest -v
```

### 5. Enable Live LLMs (Vertex AI + LangSmith)

**Step 1 — GCP setup**

```bash
# Authenticate (pick one)
gcloud auth application-default login
# OR set a service account key path:
# GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json

# Enable Vertex AI API in your GCP project
gcloud services enable aiplatform.googleapis.com --project=YOUR_GCP_PROJECT
```

**Step 2 — Configure `.env`**

```env
MOCK_LLM=false
LLM_PROVIDER=vertex
VERTEX_AI_PROJECT=your-gcp-project
VERTEX_AI_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json

# LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_...
LANGCHAIN_PROJECT=ai-finops-platform
```

**Step 3 — Verify**

```bash
curl http://localhost:8000/health
curl http://localhost:8000/observability/status
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"text": "05/01 Whole Foods -127.43", "source": "manual"}'
```

Open [LangSmith](https://smith.langchain.com) → project `ai-finops-platform` to view traces tagged by `task_type`.

**Multi-provider mode** (optional — routes across Gemini, Claude, GPT):

```env
LLM_PROVIDER=multi
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
VERTEX_AI_PROJECT=your-gcp-project
```

---

### 6. BigQuery Cost Sink (LLM FinOps Analytics)

Every LLM call is streamed to BigQuery for token spend analysis, ROI tracking, and anomaly detection.

**Enable in `.env`:**

```env
BIGQUERY_ENABLED=true
BIGQUERY_PROJECT=your-gcp-project
BIGQUERY_DATASET=finops_analytics
BIGQUERY_TABLE=llm_usage
GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\service-account.json
```

**Setup (one-time):**

```bash
gcloud services enable bigquery.googleapis.com --project=YOUR_GCP_PROJECT
# Optional manual schema — or let the app auto-create on first pipeline run
# See infra/bigquery/schema.sql
```

**Verify:**

```bash
curl http://localhost:8000/analytics/bigquery/status
# Run a pipeline, then query BigQuery:
# See sample queries in infra/bigquery/queries.sql
```

**What gets stored per LLM call:**

| Column | Description |
|--------|-------------|
| `task_type` | document_parse, deep_analysis, etc. |
| `model` | gemini-2.0-flash-lite, gemini-1.5-pro, ... |
| `input_tokens` / `output_tokens` | Token economy metrics |
| `cost_usd` | Computed from model pricing table |
| `pipeline_run_id` | Groups 6 calls from one pipeline run |
| `roi` | estimated_savings / cost |

---

## API Examples

**Full pipeline:**

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "05/01 Whole Foods -127.43\n05/03 Netflix -15.99", "source": "manual"}'
```

**View routing rules:**

```bash
curl http://localhost:8000/router/rules
```

**Mock Plaid ingestion:**

```bash
curl http://localhost:8000/ingest/plaid/mock
```

---

## Project Structure

```
AI-FinOps-Platform/
├── backend/
│   ├── agents/           # LangGraph orchestrator + 5 specialized agents
│   ├── router/           # Model router + cost/ROI tracker
│   ├── ingestion/        # PDF, CSV, Plaid parsers
│   ├── evaluation/       # LangSmith + eval hooks
│   └── api/              # FastAPI endpoints
├── frontend/             # Streamlit MVP dashboard
├── infra/                # Docker, Cloud Build, Terraform
├── tests/
├── docs/
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent Orchestration | LangGraph |
| LLM Providers | Vertex AI (Gemini), OpenAI, Anthropic |
| Backend | FastAPI + Python |
| Frontend | Streamlit (MVP) → Next.js (planned) |
| Vector DB | Weaviate / Pinecone (planned) |
| Deployment | Cloud Run + GCP |
| Observability | LangSmith, custom cost tracker |

---

## Deployment (GCP)

```bash
# Build & deploy via Cloud Build
gcloud builds submit --config infra/cloudbuild.yaml

# Or Terraform
cd infra/terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT"
```

---

## Roadmap

- [ ] Next.js production frontend
- [ ] Weaviate vector store for semantic transaction search
- [ ] Real Plaid Link OAuth integration
- [ ] LangSmith eval datasets for regression testing
- [x] BigQuery sink for LLM cost analytics
- [ ] Cloud Run production deployment

---

## Author

Built by a FinTech + Cloud SaaS engineer transitioning into **AI Platform / Agent Engineering**.

**Skills demonstrated:** LangGraph · LangChain · Vertex AI · Model Routing · Cost Optimization · FastAPI · GCP Cloud Run · FinTech Compliance Automation

---

## License

MIT
