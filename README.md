# Agentic Procurement Intelligence & Operations Platform

> An agentic AI platform for enterprise procurement operations — natural-language investigation across databases and documents, with evidence-backed answers, anomaly detection, and human-in-the-loop approval workflows.

---

## Demo

**Evidence-backed investigation** — invoice, PO, contract, payment, and approval
evidence with citations and confidence:

![Invoice investigation](docs/assets/chat-investigation.png)

**Human-in-the-loop approvals** — pending payment requests with risk level and
Approve & Execute / Reject controls:

![Pending approvals](docs/assets/approvals-panel.png)

Regenerate screenshots with the frontend running on `:3000`:

```bash
cd frontend
node capture_screenshots.mjs ../docs/assets
```

## Project Status

**Phase: Working vertical slice.** The platform runs end-to-end on the UK Contracts Finder backbone with a deterministic, evidence-backed agent. No API keys are required for the core workflows.

| Capability | Status |
|---|---|
| Data pipeline (public data → synthetic enterprise layer) | ✅ Complete |
| PostgreSQL schema + migrations | ✅ Complete |
| LangGraph orchestration (intent routing, workflows) | ✅ Complete |
| Entity lookups: invoice, PO, contract, vendor, payment, approval | ✅ Complete |
| LLM planner (Claude Haiku 5.5 via OpenCode Go) | ✅ Complete (`PLANNER_MODE=llm`) |
| Planner decision audit trail | ✅ Complete (`GET /decisions`) |
| Evidence-backed investigation (invoice/PO/contract/payment) | ✅ Complete |
| Semantic metrics layer (governed SQL, 7 metrics) | ✅ Complete |
| Multi-turn conversation memory (Postgres checkpoints) | ✅ Complete |
| Clarification for missing/ambiguous identifiers | ✅ Complete |
| Deterministic anomaly detection (rules + duplicates) | ✅ Complete |
| Read-only SQL analytics templates | ✅ Complete |
| Document retrieval (policy/email/notes) | ✅ Complete |
| Human-in-the-loop approvals + execution via mock ERP | ✅ Complete |
| LangGraph checkpointing + interrupt/resume (Postgres) | ✅ Complete |
| pgvector embeddings + hybrid BM25/dense retrieval | ✅ Complete (384-dim local model) |
| Reproducible evaluation benchmarks | ✅ Complete (see [RESULTS.md](docs/evaluation/RESULTS.md)) |
| Prometheus metrics endpoint | ✅ Complete |
| Authentication (JWT) + role-based access control | ✅ Complete |
| Frontend login + chat + approvals panel | ✅ Complete (production build verified) |
| LLM narrative layer | ⚙️ Optional (disabled by default) |
| MCP server | ✅ stdio + streamable HTTP (:8001); API uses the shared mock ERP service |

---

## Quick Start

Prerequisites: Docker, Python 3.12+, [uv](https://docs.astral.sh/uv/).

```bash
# 1. Install dependencies (creates .venv automatically)
uv sync

# 2. Configure environment
cp .env.example .env

# 3. Start PostgreSQL (pgvector image)
docker compose up -d postgres

# 4. Create the schema
uv run alembic -c src/procurement_ai/database/migrations/alembic.ini upgrade head

# 5. Build the dataset (download the UK Contracts Finder export first)
uv run python scripts/download_public_data.py
uv run python scripts/generate_synthetic_data.py --limit-contracts 5000
uv run python scripts/generate_documents.py
uv run python scripts/inject_anomalies.py --limit 10000
uv run python scripts/build_evaluation_set.py

# 6. Load into PostgreSQL
uv run python scripts/load_data.py --database-url "postgresql+psycopg2://user:pass@localhost:5432/procurement"
uv run python scripts/load_documents.py --database-url "postgresql+psycopg2://user:pass@localhost:5432/procurement"
uv run python scripts/load_exceptions.py --database-url "postgresql+psycopg2://user:pass@localhost:5432/procurement"

# 7. Build document embeddings (adds 200 contract summaries + embeds corpus)
uv run python scripts/build_embeddings.py --contracts 200

# 8. Seed demo users (password: demo123)
uv run python scripts/seed_demo_users.py

# 9. Run the API
uv run uvicorn src.procurement_ai.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm start        # dev server on :3000
npm run build    # production build in frontend/build
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics

### Full Docker Compose Stack

```bash
# 1. Start PostgreSQL first (data loads run against it)
docker compose up -d postgres

# 2. Load data + seed users on the host (see Quick Start steps 5–8)
#    The API container runs migrations on startup.

# 3. Start the full stack
docker compose up --build -d
```

| Service | URL |
|---|---|
| Web UI | http://localhost:3000 |
| API / Swagger | http://localhost:8000 / `/docs` |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / `GRAFANA_ADMIN_PASSWORD`, default `admin`) |
| MCP (streamable HTTP) | http://localhost:8001 |
| PostgreSQL | localhost:5432 |

Grafana is provisioned automatically with the Prometheus datasource and the
**Procurement AI Platform** dashboard (request rate, workflow routes, node and
planner latency, tokens, tool calls, approvals, anomalies).

The container images install the full ML dependency set (including local
embeddings), so the first build downloads several GB and can take a while.

### Public Data

Place the flattened OCDS export at:

```
data/raw/united_kingdom_contracts_finder_releases_full.csv/full/{main,awards,awards_suppliers,parties}.csv
```

Source: [UK Contracts Finder](https://www.contractsfinder.service.gov.uk/) — Open Government Licence v3.0. See [docs/data/DATA_SOURCES.md](docs/data/DATA_SOURCES.md).

---

## Authentication & RBAC

All business endpoints require a JWT bearer token. `/health`, `/`, `/metrics`,
and `/auth/login` are public.

```bash
# Login (demo users are seeded by scripts/seed_demo_users.py)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"manager@example.com","password":"demo123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

curl http://localhost:8000/auth/me -H "Authorization: Bearer $TOKEN"
```

Demo users (password `demo123`, configurable via `DEMO_PASSWORD`):

| Email | Role |
|---|---|
| specialist@example.com | specialist |
| manager@example.com | manager |
| finance@example.com | finance |
| director@example.com | director |
| admin@example.com | admin |

Role permissions:

| Capability | Roles |
|---|---|
| Chat, entity lookups, anomalies | all authenticated roles |
| View approvals | all authenticated roles |
| Approve / reject approvals | manager, finance, director, admin |
| Planner decision audit (`/decisions`) | manager, finance, director, admin |
| Approve your own request | **never** (separation of duties) |

Configuration:

```bash
API_SECRET_KEY=change-me-in-production   # JWT signing key; change in production
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

## Example Queries

```bash
TOKEN="<access token from /auth/login>"

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message": "Why is invoice INV-000010 overdue?"}'
```

| Question | Workflow |
|---|---|
| Why is invoice INV-000010 overdue? | investigation |
| Does INV-000010 comply with its purchase order? | investigation |
| Show me PO-000001 | retrieval (entity lookup) |
| What is contract CF-2022-00011? | retrieval (entity lookup) |
| What are the payment terms for vendor Springer Nature? | retrieval (entity lookup) |
| Show payment PAY-000001 | retrieval (entity lookup) |
| Show approval APPR-000001 | retrieval (entity lookup) |
| Find potential duplicate invoices | detection |
| Find transactions that may violate procurement policy | detection |
| Show me spending by category | sql (semantic) |
| What is the exception rate by vendor? | sql (semantic) |
| Which contracts expire within 60 days? | sql (semantic) |
| What is the average approval cycle time by department? | sql (semantic) |
| What are the approval requirements for invoices over 50000? | retrieval |
| Request payment for INV-000003 | action |

Multi-turn follow-ups work within a session:

```bash
# Turn 1
"message": "What is the status of invoice INV-000010?", "session_id": "demo"
# Turn 2 — resolves "its" against the previous invoice
"message": "What about its payment?", "session_id": "demo"
```

### Approvals

```bash
# List pending approvals (any authenticated user)
curl "http://localhost:8000/approvals?status=pending" \
  -H "Authorization: Bearer $TOKEN"

# Approve — requires manager/finance/director/admin, executes via mock ERP
curl -X POST "http://localhost:8000/approvals/{id}/decide" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"decision": "approve", "comment": "Verified"}'
```

Approving is guarded: already-decided requests return `409`, duplicate payments
are blocked before execution, non-approver roles get `403`, and users cannot
decide their own requests.

Approval workflows created by the action graph are paused at a LangGraph `interrupt()` and checkpointed in PostgreSQL. Deciding the approval resumes the graph with `Command(resume=...)`, so the decision, payment execution, invoice update, and audit log happen inside the graph run. Approvals created before checkpointing existed fall back to direct execution.

---

## Architecture

```
Client (React UI)
      │
      ▼
FastAPI ──► LangGraph orchestrator
      │         ├── guardrails (injection / length / PII)
      │         ├── deterministic intent routing
      │         ├── retrieval   → documents table
      │         ├── SQL         → read-only templates
      │         ├── investigation → invoice/PO/contract/payments/approvals
      │         ├── detection   → rules + duplicate heuristics
      │         ├── action      → validation → approval request
      │         └── response validation (citations, confidence)
      │
      ├── PostgreSQL + pgvector
      ├── Mock ERP service ──► MCP server (stdio)
      └── Prometheus /metrics
```

- Full design: [docs/architecture/DESIGN.md](docs/architecture/DESIGN.md)
- Data generation: [docs/data/GENERATION.md](docs/data/GENERATION.md)
- Evaluation: [docs/evaluation/METRICS.md](docs/evaluation/METRICS.md)

---

## Evaluation Results

Measured by `uv run python scripts/run_benchmarks.py` against the loaded database
(274 documents, 384-dim embeddings, 41,986 invoices, 150 injected anomalies).
Full report: [docs/evaluation/RESULTS.md](docs/evaluation/RESULTS.md).

### Retrieval (K = 5, 48 queries)

| Method | Recall@5 | MRR | NDCG@5 |
|---|---|---|---|
| BM25 | 0.979 | 0.939 | 0.949 |
| Dense (pgvector) | 0.854 | 0.788 | 0.797 |
| **Hybrid (RRF)** | **1.000** | **0.952** | **0.964** |

### Routing

- 100/100 benchmark tasks routed to the expected workflow.

### Anomaly Detection

| Metric | Value |
|---|---|
| Recall | **1.000** (150/150 injected anomalies) |
| Precision | 0.811 |
| TP / FP / FN | 150 / 35 / 0 |

Remaining false positives are duplicate copies that also trip amount/approval
rules, plus two contract-end date edge cases.

## Observability

`GET /metrics` exposes Prometheus metrics:

| Metric | Type | Labels |
|---|---|---|
| `agent_requests_total` | Counter | HTTP method, path bucket |
| `agent_request_duration_seconds` | Histogram | path bucket |
| `agent_workflow_total` | Counter | workflow, intent |
| `agent_workflow_duration_seconds` | Histogram | workflow |
| `node_duration_seconds` | Histogram | LangGraph node |
| `tool_calls_total` / `tool_errors_total` | Counter | tool name |
| `llm_calls_total`, `llm_tokens_total` | Counter | provider / type |
| `approval_requests_total`, `anomalies_detected_total` | Counter | status / type |

Every graph node is timed, and the chat endpoint records the routed workflow,
tool calls, and end-to-end duration. Example scrape output after one request:

```text
agent_workflow_total{intent="investigate",workflow="investigation"} 1
node_duration_seconds_count{node="investigation_workflow"} 1
tool_calls_total{tool="run_anomaly_rules"} 1
```

## Data Access Model

Transactional records are **not** chunked or embedded. They change constantly,
so they are queried live through typed entity tools and governed SQL. Only
curated documents are embedded for semantic search (policies, notes, emails,
and contract summaries). This keeps the vector index small and avoids
re-embedding on every invoice, PO, or payment change.

Analytics run through the **semantic layer** (`src/procurement_ai/semantic/`):
metrics such as total spend, overdue rate, exception rate, and approval cycle
time have explicit definitions and allow-listed dimensions. No free-form SQL is
generated at runtime.

## LLM Planner

The planner converts natural language into a **validated structured route**:
workflow, entity reference, semantic metric, clarification, or fallback.

Two modes:

| Mode | Behavior |
|---|---|
| `deterministic` (default) | Keyword router, no API key, no network |
| `llm` | Claude Haiku 5.5 via OpenCode Go, with deterministic fallback |

Configuration (in `.env`, never committed):

```bash
PLANNER_MODE=llm
OPENCODE_GO_API_KEY=...
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=claude-haiku-5-5
OPENCODE_SESSION_ID=procurement-ai-planner
LLM_TIMEOUT_SECONDS=20
```

How a request flows with the planner:

```
Question + recent history
  → Claude Haiku returns strict JSON
      {workflow, intent, entity, metric, follow_up, clarification_message}
  → validation against allow-lists
      workflows, entity types/ID formats, metrics, dimensions, day ranges
  → same deterministic execution layer
      entity tools / semantic metrics / retrieval / detection / action
  → evidence validation → citations
```

Safety properties:

- The planner **cannot write SQL**; metrics must be named and use allow-listed dimensions.
- Transactional data is still queried live, never embedded.
- Invalid JSON, unknown workflows, malformed IDs, or timeouts fall back to the deterministic router.
- Payments still require human approval.
- Planner choices are persisted in state for observability and debugging.

Measured planner latency against OpenCode Go: **1.4–2.3 s** per request. Token and
latency metrics are exported as `llm_calls_total`, `llm_tokens_total`, and
`llm_request_duration_seconds`.

## Planner Decision Audit

Every chat request writes a durable decision record, whether the LLM planner or
the deterministic router handled it. The chat response includes `decision_id`.

```bash
# Query decisions by session, trace, workflow, mode, or fallback usage
curl "http://localhost:8000/decisions?session_id=s-audit-demo"
curl "http://localhost:8000/decisions?workflow=sql&planner_mode=llm"
curl "http://localhost:8000/decisions?fallback_used=true"
```

Recorded fields:

| Group | Fields |
|---|---|
| Request | `trace_id`, `session_id`, `user_id`, `question` |
| Planner | `planner_mode`, `model`, `validation_result`, `fallback_used`, `reason`, `raw_decision` |
| Route | `workflow`, `intent`, entity type/id/name, metric, dimension, days, follow-up, clarification |
| Cost | `input_tokens`, `output_tokens`, planner `latency_ms`, `total_latency_ms` |
| Time | `created_at` |

Example record:

```json
{
  "question": "Which vendor is generating the most exceptions?",
  "planner_mode": "llm",
  "model": "claude-haiku-5-5",
  "workflow": "sql",
  "intent": "analyze",
  "metric": "exception_count",
  "dimension": "vendor",
  "validation_result": "accepted",
  "fallback_used": false,
  "input_tokens": 1395,
  "output_tokens": 118,
  "latency_ms": 2197,
  "total_latency_ms": 2394
}
```

This makes misroutes, fallbacks, token usage, and planner latency inspectable
after the request finishes.

## Tech Stack

- **Language:** Python 3.12+
- **API:** FastAPI
- **Orchestration:** LangGraph
- **Database:** PostgreSQL + pgvector
- **Retrieval:** BM25 + pgvector dense + reciprocal rank fusion; optional cross-encoder
- **Embeddings:** sentence-transformers `all-MiniLM-L6-v2` (384 dims, local)
- **ML:** scikit-learn (anomaly features)
- **MCP:** MCP server over stdio + shared mock ERP service
- **Auth:** JWT (HS256) + role-based access control
- **Testing:** pytest (120 tests)
- **Packaging:** uv
- **Containers:** Docker Compose (PostgreSQL, API, frontend, MCP, Prometheus, Grafana)
- **Observability:** Prometheus metrics; OpenTelemetry scaffolding

---

## Testing & Benchmarks

```bash
# Unit + integration + evaluation tests
uv run pytest tests/ -q

# Reproducible benchmarks (requires loaded data + embeddings)
uv run python scripts/run_benchmarks.py

# Lint and type checks used in CI
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
```

---

## Design Principles

1. Deterministic logic where possible; LLM only where language reasoning adds value.
2. Every answer carries evidence/citations.
3. High-risk actions require human approval and are audited.
4. Synthetic data is seeded, reproducible, and referentially consistent.
5. Read-only tools are separated from write/action tools.

---

## Limitations

- Public procurement data is UK Contracts Finder, not a private ERP.
- Synthetic enterprise records are generated, not real company data.
- The mock ERP is in-process; the MCP server exposes the same service over stdio.
- Authentication is local JWT with seeded demo users; no SSO, refresh tokens, or multi-tenancy.
- LLM narrative is disabled by default; the planner is optional.
- Full contract/invoice text is not embedded (transactional data is queried live).

## License

MIT
