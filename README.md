# Agentic Procurement Intelligence & Operations Platform

> An agentic AI platform for enterprise procurement operations — natural-language investigation across databases and documents, with evidence-backed answers, anomaly detection, and human-in-the-loop approval workflows.

---

## Demo

**Agent-first anomaly triage** — the agent reads the exception store and
explains all 150 open records across 10 exception types:

![Agent anomaly summary](docs/assets/chat-agent-anomalies.png)

**Exception drill-down** — the follow-up “show me the top 5 invoices that
exceed PO” uses several tools to return invoice, PO, vendor, contract, and
overage details:

![Agent exception detail](docs/assets/chat-agent-exception-detail.png)

**Open-ended prioritization** — “what should I focus on this week?” is answered
by combining pending approvals, exceptions, overdue invoices, spend, and
policy context:

![Agent focus summary](docs/assets/chat-agent-focus.png)

**Evidence-backed investigation** — invoice, PO, contract, payment, and approval
evidence with citations and confidence:

![Invoice investigation](docs/assets/chat-investigation.png)

**Human-in-the-loop approvals** — illustrative pending payment request with
risk level and Approve & Execute / Reject controls:

![Pending approvals](docs/assets/approvals-panel.png)

**Observability** — provisioned Grafana dashboard showing request rate, workflow
routes, node/LLM latency, tokens, tool calls, approvals, and open exceptions:

![Grafana dashboard](docs/assets/grafana-dashboard.png)

Regenerate screenshots with the local services running:

```bash
cd frontend
node capture_agent_demo.mjs ../docs/assets    # agent-first UI (:3000)
node capture_grafana.mjs ../docs/assets       # Grafana (:3001)
```

## Project Status

**Phase: Working vertical slice.** The platform runs end-to-end on the UK Contracts Finder backbone in **agent-first** mode: read-only questions are handled by a tool-calling agent that can query SQL, semantic metrics, documents, exceptions, and entity records. Controlled actions remain deterministic and require human approval. Hybrid mode with deterministic fast paths is still available. Core hybrid workflows need no API key; the agent and LLM planner use Claude Haiku 5.5 via OpenCode Go.

| Capability | Status |
|---|---|
| Data pipeline (public data → synthetic enterprise layer) | ✅ Complete |
| PostgreSQL schema + migrations | ✅ Complete |
| LangGraph orchestration (intent routing, workflows) | ✅ Complete |
| Entity lookups: invoice, PO, contract, vendor, payment, approval | ✅ Complete |
| LLM planner (Claude Haiku 5.5 via OpenCode Go) | ✅ Complete (`PLANNER_MODE=llm`) |
| Planner decision audit trail | ✅ Complete (`GET /decisions`) |
| Evidence-backed investigation (invoice/PO/contract/payment) | ✅ Complete |
| Semantic metrics layer (governed SQL + list queries) | ✅ Complete |
| Agent-first orchestration (open-ended read-only questions) | ✅ Default (`ORCHESTRATION_MODE=agent_first`) |
| Open-ended tool-calling agent (schema, read-only SQL, metrics, documents, exceptions, entity lookups) | ✅ Complete, locally verified |
| Hybrid mode (deterministic fast paths + agent fallback) | ✅ Optional (`ORCHESTRATION_MODE=hybrid`) |
| SQL guardrails (SELECT-only, denylist, row cap, timeout, read-only transaction) | ✅ Complete |
| Multi-turn conversation memory (Postgres checkpoints) | ✅ Complete |
| Clarification for missing/ambiguous identifiers | ✅ Complete |
| Deterministic anomaly detection (rules + duplicates) | ✅ Retained for hybrid mode; agent uses `list_exceptions` |
| Read-only SQL analytics templates | ✅ Retained for hybrid mode |
| Document retrieval (policy/email/notes) | ✅ Complete |
| Human-in-the-loop approvals + execution via mock ERP | ✅ Complete |
| LangGraph checkpointing + interrupt/resume (Postgres) | ✅ Complete |
| pgvector embeddings + hybrid BM25/dense retrieval | ✅ Complete (384-dim local model) |
| Reproducible evaluation benchmarks | ✅ Complete (see [RESULTS.md](docs/evaluation/RESULTS.md)) |
| Prometheus metrics endpoint | ✅ Complete |
| Authentication (JWT) + role-based access control | ✅ Complete |
| Frontend login + chat + approvals panel | ✅ Complete (production build verified) |
| Full Docker Compose stack (6 services) | ✅ Verified for the deterministic stack; rebuild pending for the agent version |
| LLM planner / agent | ⚙️ Optional; fast paths remain deterministic |
| MCP server | ✅ stdio + streamable HTTP (:8001), tool calls verified |

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

> **PyTorch builds:** a plain `uv sync` installs the default PyPI wheel (CUDA on
> Linux/WSL). Use `uv sync --extra cu130` for the official CUDA 13.0 wheels, or
> `uv sync --extra cpu` for CPU-only. The Docker images always build with the
> `cpu` extra to keep image size down.

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
**Procurement AI Platform** dashboard (request rate, workflow routes, node/LLM
latency, tokens, tool calls, approvals, and open exceptions).

Verified locally: API health, JWT login, agent-first chat, frontend on :3000,
MCP `list_tools`/tool calls over HTTP, Prometheus targets `up`, and the Grafana
dashboard populated.

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
API_SECRET_KEY=change-me-in-production-use-32-chars-min   # JWT signing key; change in production
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

The workflow labels below describe **hybrid mode**. In the default agent-first
mode, all read-only questions report `agent`, while action requests still route
to the deterministic action workflow.

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
| Which invoices are overdue? | sql (semantic list) |
| Which payment requests are pending? | sql (semantic list) |
| List all pending payments and approvals as a table | agent (multi-category) |
| Which contracts expire within 60 days? | sql (semantic) |
| What is the average approval cycle time by department? | sql (semantic) |
| What are the approval requirements for invoices over 50000? | agent (documents) |
| How can you help me with finance operations? | agent (help) |
| I just said all | agent (conversation context) |
| Which vendors have the highest average invoice value? Show the top 5 with invoice counts | agent (SQL) |
| What changed in spending from 2024 to 2025? | agent (SQL) |
| Find invoices that exceed their contract maximum and show the contract title | agent (SQL) |
| Show me payments above 1,000,000 with invoice numbers and vendors | agent (SQL) |
| Request payment for INV-000003 | action |

### Orchestration modes

**Agent-first (default):** every read-only question goes to the agent, including
anomalies, exceptions, policy synthesis, entity lookups, comparisons, and
follow-ups. The agent decides which tools to use and can chain several tools
when one is not enough. Payment/approval actions are intercepted and sent to the
deterministic human-in-the-loop action workflow.

**Hybrid (optional):** the validated planner/fast-path router is used instead.
Simple metrics and entity lookups stay deterministic; open-ended, policy,
exception-detail, and multi-category pending questions still route to the agent.

```bash
ORCHESTRATION_MODE=agent_first   # default
# ORCHESTRATION_MODE=hybrid
```

The agent can call `describe_schema`, `query_database`, `run_metric`,
`search_documents`, `list_exceptions`, and read-only entity tools. It observes
results, corrects failed SQL, and writes the final answer with citations. The
planner decision (in hybrid mode) and a compact agent tool trace are persisted
in `planner_decisions.raw_decision`; the API records a decision ID and trace ID
for each chat request.

The deterministic detection workflow remains in the codebase as a hybrid-mode
fallback. In agent-first mode, anomaly questions use `list_exceptions` and the
agent can enrich the result with invoice, PO, contract, vendor, and payment
lookups.

The agent is read-only. It cannot execute payments or approvals; those still go
through the human-in-the-loop action workflow.

**SQL guardrails:** the agent SQL tool accepts one `SELECT`/`WITH` statement,
rejects data-changing/schema-changing keywords and dangerous functions, blocks
sensitive tables/columns (`planner_decisions`, checkpoints, `password_hash`,
`embedding`, `bank_details`), runs in a read-only transaction, caps results at
100 rows, and applies a 5-second statement timeout. Production deployments
should also use a dedicated `SELECT`-only database role.

Open-ended agent responses were verified locally against the running database
and Claude Haiku. The Docker images have not yet been rebuilt with this version
(by design; local verification first).

Multi-turn follow-ups work within a session:

```bash
# Turn 1
"message": "What is the status of invoice INV-000010?", "session_id": "demo"
# Turn 2 — resolves "its" against the previous invoice
"message": "What about its payment?", "session_id": "demo"
```

Ambiguous pending requests are handled conversationally:

```text
User: pend
Agent: Do you mean pending approvals, pending payment requests, or pending payments?
User: all
Agent: shows all three categories separately.
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
      │         ├── agent-first (default)
      │         │     ├── tool loop: schema, read-only SQL, metrics, docs,
      │         │     │   exceptions, entity lookups
      │         │     └── action interception → human approval
      │         ├── hybrid mode (optional)
      │         │     ├── planner (validated route + audit)
      │         │     ├── retrieval / SQL / investigation / detection
      │         │     └── agent fallback
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
on 2026-11-09 (274 documents, 384-dim embeddings, 42,001 invoices, 150 injected
anomalies). Full report: [docs/evaluation/RESULTS.md](docs/evaluation/RESULTS.md).

### Retrieval (K = 5, 48 queries)

| Method | Recall@5 | MRR | NDCG@5 |
|---|---|---|---|
| BM25 | 0.979 | 0.939 | 0.949 |
| Dense (pgvector) | 0.854 | 0.788 | 0.797 |
| **Hybrid (RRF)** | **1.000** | **0.952** | **0.964** |

### Routing

- 100/100 benchmark tasks routed to the expected workflow.

### Open-Ended Agent (5 curated tasks, local)

| Metric | Value |
|---|---|
| Routing accuracy | **1.00** (5/5) |
| Tool selection accuracy | **1.00** (5/5) |
| Answer term coverage | **1.00** (5/5) |
| Tool success rate | **1.00** |
| Average agent steps | 3.6 |
| Adversarial SQL block rate | **1.00** (7/7) |

This is a small verification sample, not a statistically meaningful benchmark;
term coverage is not a semantic-correctness score. See
[docs/evaluation/OPEN_ENDED.md](docs/evaluation/OPEN_ENDED.md) for tasks,
limitations, and the reproducible script.

### Anomaly Detection

| Metric | Value |
|---|---|
| Recall | **1.000** (150/150 injected anomalies) |
| Precision | 0.811 |
| TP / FP / FN | 150 / 35 / 0 |

Remaining false positives are duplicate copies that also trip amount/approval
rules, plus two contract-end date edge cases.

### Current engineering verification

- **174 tests passed** with `uv run pytest tests/ -q`.
- `ruff check` and `mypy src/` clean.
- Agent-first demo verified against the live local stack:
  - `anomalies and exceptions` → 150 open exceptions across 10 types.
  - `invoice exceeds po` → 30 affected invoices with PO, contract, vendor, and
    overage details.
  - `what should I focus on this week?` → combined exceptions, overdue
    invoices, pending queues, and contract context.
- Open-ended evaluation: 5/5 routing, 5/5 primary-tool selection, 5/5 required
  term coverage, 3.6 average tool rounds, and 7/7 adversarial SQL statements
  rejected. See [OPEN_ENDED.md](docs/evaluation/OPEN_ENDED.md).
- Docker images still reflect the pre-agent-first build; no rebuild was performed
  during this local verification.

## Observability

`GET /metrics` exposes Prometheus metrics:

| Metric | Type | Labels |
|---|---|---|
| `agent_requests_total` | Counter | intent, workflow/path |
| `agent_request_duration_seconds` | Histogram | intent |
| `agent_workflow_total` | Counter | workflow, intent |
| `agent_workflow_duration_seconds` | Histogram | workflow |
| `node_duration_seconds` | Histogram | LangGraph node |
| `tool_calls_total` / `tool_errors_total` | Counter | tool name |
| `llm_calls_total`, `llm_tokens_total` | Counter | provider / type |
| `llm_request_duration_seconds` | Histogram | provider, model |
| `approval_requests_total` | Counter | status |
| `anomalies_detected_total` | Counter | type (hybrid detection workflow) |
| `exceptions_open_total` | Gauge | type (agent `list_exceptions` view) |

Every graph node is timed, and the chat endpoint records the routed workflow,
tool calls, and end-to-end duration. In agent-first mode, the `agent` workflow
dominates; `exceptions_open_total` is populated when the agent reads exception
records.

### Reading the Grafana dashboard

Open http://localhost:3001 and choose **Dashboards → Procurement → Procurement AI Platform**.
The default range is **Last 6 hours**, so it includes historical demo traffic
and any earlier hybrid-mode runs, not just the latest request.

| Panel | What it means | How to read it |
|---|---|---|
| **HTTP request rate (all endpoints)** | Rate of all HTTP requests handled by the API. | Includes `/health` probes and `/metrics` scrapes. Filter by `workflow="/chat"` to isolate user chat traffic. A flat zero means no API traffic in the selected window. |
| **LLM calls (planner + agent)** | Provider/model call rate. | In agent-first mode this is dominated by `opencode_go` agent calls. In hybrid mode it also includes planner calls. Zero means no LLM-backed request in the window. |
| **Workflow routes** | Request rate by routed workflow. | In agent-first mode expect `agent`; in hybrid mode you may see `sql`, `retrieval`, `investigation`, `detection`, `clarification`, and `action`. |
| **Workflow latency p95** | 95th percentile of LangGraph workflow duration. | Agent questions can be 20–30 seconds because they may make several tool/LLM rounds. This is not the same as a single HTTP request or database query. |
| **Node latency p95** | Per-node execution latency. | Compare `agent_workflow` with `guardrails`, `intent_classifier`, `planner`, and `response_validator`. Planner should be near zero in agent-first mode because it is bypassed. |
| **LLM call latency p95** | 95th percentile LLM call duration by model. | A long tail here explains high workflow latency. It covers planner plus agent LLM calls. |
| **LLM tokens / second** | Input and output token throughput. | Spikes occur during multi-step agent answers. This is rate, not cumulative spend. |
| **Tool calls** | Tool invocation rate by name. | Useful for seeing whether the agent used `query_database`, `run_metric`, `list_exceptions`, `describe_schema`, or document/entity tools. A zero series means the tool was not called in the window, not necessarily an error. |
| **Approvals by status** | Approval counter by status. | Counters are **process-local** and reset when the API restarts. This is not a live count of rows in PostgreSQL; use `/approvals` for the current database state. |
| **Open exceptions by type** | Gauge populated by the agent’s `list_exceptions` tool. | Shows the current curated exception counts (for example 30 `invoice_exceeds_po`). It updates when the agent reads exceptions; it is not a count of every detection run. |

**Current local snapshot** (from the final agent-first demo run; rates are over
the last 5 minutes and counters reset on API restart):

- HTTP request rate: ~`0.08 req/s` with `/chat` traffic present.
- Agent workflow rate: ~`0.007 req/s`; workflow p95: `28 s`.
- LLM call rate: ~`0.011 calls/s`; LLM p95: `9.6 s`; token rates: ~`131 input/s`
  and ~`15 output/s`.
- Tool activity: `run_metric`, `list_exceptions`, `describe_schema`, and
  `query_database` were observed.
- Open exceptions: 30 `invoice_exceeds_po`, 25 `missing_approval`,
  20 `invoice_exceeds_contract`, 15 `duplicate_invoice`, and 10 each for the
  remaining six types.

The screenshot in the [Demo](#demo) section is a 6-hour Grafana view and
therefore intentionally shows more history than the 5-minute snapshot above.

## Data Access Model

Transactional records are **not** chunked or embedded. They change constantly,
so they are queried live through typed entity tools and governed SQL. Only
curated documents are embedded for semantic search (policies, notes, emails,
and contract summaries). This keeps the vector index small and avoids
re-embedding on every invoice, PO, or payment change.

Analytics run through the **semantic layer** (`src/procurement_ai/semantic/`):
metrics such as total spend, overdue rate, exception rate, and approval cycle
time have explicit definitions and allow-listed dimensions. In agent-first mode
the agent may also generate **guarded read-only SQL** for arbitrary joins and
comparisons; that SQL is validated, row-capped, time-limited, and executed in a
read-only transaction. Transactional data is never embedded.

## LLM Planner

In **hybrid mode**, the planner converts natural language into a **validated
structured route**: workflow, entity reference, semantic metric, clarification,
or fallback. In agent-first mode the planner is bypassed for read-only
questions; the agent owns tool selection. Controlled actions still use the
deterministic action workflow.

Planner modes (hybrid):

| Mode | Behavior |
|---|---|
| `deterministic` (default) | Keyword router, no API key, no network; simple fast paths only |
| `llm` | Claude Haiku 5.5 via OpenCode Go, with deterministic fallback; enables the open-ended agent |

Configuration (in `.env`, never committed):

```bash
ORCHESTRATION_MODE=agent_first
PLANNER_MODE=llm
OPENCODE_GO_API_KEY=...
OPENCODE_GO_BASE_URL=https://opencode.ai/zen/go/v1
OPENCODE_GO_MODEL=claude-haiku-5-5
OPENCODE_SESSION_ID=procurement-ai-planner
LLM_TIMEOUT_SECONDS=20
SQL_MAX_ROWS=100
SQL_QUERY_TIMEOUT_MS=5000
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

Every chat request writes a durable decision record, whether agent-first
routing, the LLM planner, or the deterministic router handled it. The chat
response includes `decision_id`; agent runs also include a compact tool trace in
`raw_decision`.

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
- **Testing:** pytest (174 tests)
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
