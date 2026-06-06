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

### 5. Enable Live LLMs

Edit `.env`:

```env
MOCK_LLM=false
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
VERTEX_AI_PROJECT=your-gcp-project
```

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
- [ ] BigQuery analytics for LLM cost optimization

---

## Author

Built by a FinTech + Cloud SaaS engineer transitioning into **AI Platform / Agent Engineering**.

**Skills demonstrated:** LangGraph · LangChain · Vertex AI · Model Routing · Cost Optimization · FastAPI · GCP Cloud Run · FinTech Compliance Automation

---

## License

MIT
