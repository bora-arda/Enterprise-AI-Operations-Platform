# Agentic Procurement Intelligence & Operations Platform — Architecture & Design

> **Status:** Design document (no implementation code yet)
> **Version:** 1.0
> **Date:** 2026-10-01

---

## Table of Contents

- [A. Product Definition](#a-product-definition)
- [B. System Architecture](#b-system-architecture)
- [C. Data Architecture](#c-data-architecture)
- [D. Agent Architecture](#d-agent-architecture)
- [E. Retrieval Architecture](#e-retrieval-architecture)
- [F. Action / Approval Architecture](#f-action--approval-architecture)
- [G. Database Schema](#g-database-schema)
- [H. Repository / File Structure](#h-repository--file-structure)
- [I. API Design](#i-api-design)
- [J. Tool Design](#j-tool-design)
- [K. MCP Architecture](#k-mcp-architecture)
- [L. Security / Guardrails](#l-security--guardrails)
- [M. Evaluation Framework](#m-evaluation-framework)
- [N. Testing Strategy](#n-testing-strategy)
- [O. Docker Architecture](#o-docker-architecture)
- [P. CI/CD](#p-cicd)
- [Q. Observability](#q-observability)
- [R. Development Roadmap](#r-development-roadmap)
- [S. Portfolio Presentation](#s-portfolio-presentation)
- [Appendix: End-to-End Scenario Walkthroughs](#appendix-end-to-end-scenario-walkthroughs)

---

## A. Product Definition

### What it is

An **agentic operations platform** that lets enterprise procurement/finance users ask natural-language questions about operational data, investigate issues across heterogeneous sources (SQL databases, documents, policies), detect anomalies and policy violations, and initiate controlled business workflows with human-in-the-loop approval.

### What it is NOT

- Not a generic chatbot
- Not a simple RAG demo
- Not an autonomous financial decision-maker
- Not a replacement for an ERP system
- Not a tutorial project

### Who uses it

| Persona | Primary need |
|---|---|
| Procurement Specialist | PO/contract compliance, vendor exceptions |
| Accounts Payable / Finance | Invoice status, overdue payments, duplicates |
| Procurement Manager | Spending analytics, vendor performance, trends |
| Compliance / Internal Audit | Policy violations, missing approvals, evidence |
| Vendor Manager | Contract expirations, outstanding invoices |
| Contract / Legal Operations | Payment terms, contract limits, expirations |
| General Business Employee | Process guidance, approval thresholds |

### Why they use it

They currently navigate 5–10 disconnected systems to answer a single operational question. This platform provides **one natural-language interface** that retrieves evidence from all sources, explains findings with citations, flags risks, and can initiate controlled actions.

### Main business value

1. **Time savings** — answers that took hours of cross-system navigation in seconds
2. **Risk reduction** — systematic anomaly and policy violation detection
3. **Audit readiness** — every answer carries evidence and provenance
4. **Controlled automation** — high-risk actions require human approval

### Main use cases

1. **FIND** — locate records across databases and documents
2. **UNDERSTAND** — explain what something means using structured + unstructured data
3. **INVESTIGATE** — multi-step investigation across tools and sources
4. **DETECT** — anomalies, duplicates, policy violations
5. **ACT** — controlled workflows with human approval

---

## B. System Architecture

### High-level diagram

```mermaid
graph TB
    subgraph Client Layer
        UI[Web UI / API Client]
    end

    subgraph API Layer
        FASTAPI[FastAPI Application]
    end

    subgraph Orchestration Layer
        GRAPH[LangGraph Orchestrator]
        subgraph Workflows
            RETRIEVAL[Retrieval Workflow]
            SQL[SQL/Data Workflow]
            ANALYSIS[Analytics Workflow]
            INVESTIGATION[Investigation Workflow]
            ACTION[Action Workflow]
        end
    end

    subgraph Capability Layer
        subgraph Retrieval
            BM25[BM25 Index]
            DENSE[Dense Embeddings]
            FUSION[Hybrid Fusion]
            RERANK[Reranker]
        end
        subgraph Data
            POSTGRES[(PostgreSQL)]
            VECTOR[(pgvector)]
        end
        subgraph Intelligence
            ANOMALY[Anomaly Detection]
            POLICY[Policy Engine]
        end
        subgraph Execution
            MCP[MCP Client]
            TOOLS[Tool Registry]
        end
    end

    subgraph External Services
        LLM[LLM Provider<br/>OpenAI / Ollama]
        EMB[Embedding Provider]
        MCPSERVER[MCP Server<br/>Mock ERP Service]
    end

    subgraph Observability
        OTEL[OpenTelemetry]
        PROM[Prometheus]
        GRAFANA[Grafana]
        LANGSMITH[LangSmith]
    end

    UI --> FASTAPI
    FASTAPI --> GRAPH
    GRAPH --> RETRIEVAL & SQL & ANALYSIS & INVESTIGATION & ACTION

    RETRIEVAL --> BM25 & DENSE
    BM25 & DENSE --> FUSION --> RERANK
    DENSE --> VECTOR

    SQL --> POSTGRES
    ANALYSIS --> POSTGRES
    INVESTIGATION --> TOOLS
    ANOMALY --> POSTGRES
    POLICY --> POSTGRES

    ACTION --> MCP
    MCP --> MCPSERVER

    GRAPH --> LLM
    RETRIEVAL --> EMB

    FASTAPI -.-> OTEL
    GRAPH -.-> OTEL
    OTEL --> PROM --> GRAFANA
    GRAPH -.-> LANGSMITH
```

### Architecture decisions

| Decision | Choice | Rationale |
|---|---|---|
| API framework | FastAPI | Async-native, Pydantic validation, OpenAPI docs, production-proven |
| Agent orchestration | LangGraph | Stateful graphs, interrupts, checkpointing, human-in-the-loop |
| LLM provider | Provider-agnostic (OpenAI / Ollama) | Avoid vendor lock-in; local dev without API keys |
| Embeddings | Provider-agnostic (OpenAI / local) | Same rationale |
| Structured store | PostgreSQL | Referential integrity, JSON support, mature ecosystem |
| Vector store | pgvector | Single database for structured + vector; no extra service; SQL-filterable metadata |
| MCP | FastMCP | Clean boundary to mock external ERP; not just a keyword |
| Packaging | uv | Fast, modern, lockfile-based |
| Observability | OpenTelemetry + Prometheus + Grafana + LangSmith | Industry standard; LangSmith for LLM-specific tracing |

### Why pgvector over Qdrant/ChromaDB

- **One less service** to run in Docker Compose
- **SQL-filterable metadata** — can filter by vendor_id, date_range, document_type in the same query
- **ACID compliance** — vector writes are transactional with the relational data
- **Sufficient scale** — portfolio project with thousands of documents, not millions
- **Simpler operations** — no separate vector DB to backup, monitor, or migrate

---

## C. Data Architecture

### Data sources

#### Layer 1 — Public procurement data (backbone)

| Source | What it provides | License |
|---|---|---|
| Open Contracting Partnership Data Registry | Buyers, suppliers, tenders, awards, contracts | Open Data Commons |
| UK Contracts Finder | Contract notices, values, dates | Open Government Licence |

The public data provides realistic **vendor names, buyer organizations, contract values, categories, and dates**. It is clearly documented as public data, NOT a private company's ERP.

#### Layer 2 — Synthetic enterprise data (deterministic)

Generated with Python + Faker + seeded RNG:

- Purchase orders (linked to public contracts)
- Invoices (linked to POs)
- Payment records
- Approval requests
- Departments
- Users/roles
- Vendor extensions (contacts, bank details)
- Operational events
- Exception records

**Referential integrity is enforced by construction** — every synthetic record references a valid parent.

#### Layer 3 — Synthetic documents

Generated from structured records (internally consistent):

- Contract PDFs (values match database)
- Procurement policies
- Approval policies
- Payment policies
- Vendor policies
- Invoice PDFs
- PO documents
- Email threads
- Operational notes

#### Layer 4 — Intentional anomalies

A controlled percentage (~5–10%) of records have injected anomalies with **known ground truth**:

| Anomaly type | Detection method |
|---|---|
| Invoice > PO amount | Deterministic rule |
| Invoice > contract limit | Deterministic rule |
| Duplicate invoice | Deterministic rule (fuzzy match) |
| Missing approval | Deterministic rule |
| Expired contract | Deterministic rule |
| Wrong vendor | Deterministic rule |
| Already-paid invoice | Deterministic rule |
| Invalid PO reference | Deterministic rule |
| Wrong currency | Deterministic rule |
| Payment mismatch | Deterministic rule |
| Unusual transaction amount | ML (Isolation Forest) |

### Database schema

See [G. Database Schema](#g-database-schema) for the full ER diagram.

### Vector store

Documents are chunked and embedded into pgvector with metadata:

```json
{
  "document_id": "doc_001",
  "document_type": "contract",
  "vendor_id": "V-101",
  "contract_id": "C-201",
  "department": "IT",
  "effective_date": "2025-01-01",
  "expiration_date": "2026-12-31",
  "source": "synthetic",
  "page": 1,
  "section": "payment_terms"
}
```

Metadata filtering is supported via SQL `WHERE` clauses on the embedding table.

### Data generation pipeline

```mermaid
graph LR
    A[Public Data<br/>Download] --> B[Public Data<br/>Clean & Normalize]
    B --> C[Synthetic Data<br/>Generator]
    C --> D[Document<br/>Generator]
    D --> E[Anomaly<br/>Injector]
    E --> F[Ground Truth<br/>Builder]
    C --> G[(PostgreSQL)]
    D --> H[(pgvector)]
    F --> I[(Evaluation Dataset)]
```

All scripts are deterministic (seeded) and reproducible.

---

## D. Agent Architecture

### Main orchestration graph

```mermaid
graph TD
    START([User Input]) --> GUARD[Input Guardrails<br/>PII / Injection / Auth]
    GUARD -->|pass| INTENT[Intent Classifier<br/>Route to Workflow]
    GUARD -->|fail| REJECT[Reject Request<br/>Log & Explain]

    INTENT -->|find/understand| RETRIEVAL[Retrieval Workflow]
    INTENT -->|query/analyze| SQL[SQL/Data Workflow]
    INTENT -->|investigate| INVESTIGATION[Investigation Workflow]
    INTENT -->|detect| DETECTION[Detection Workflow]
    INTENT -->|act| ACTION[Action Workflow]
    INTENT -->|out_of_scope| OOS[Out of Scope Response]

    RETRIEVAL --> EVIDENCE[Evidence Aggregator]
    SQL --> EVIDENCE
    INVESTIGATION --> EVIDENCE
    DETECTION --> EVIDENCE
    ACTION --> EVIDENCE

    EVIDENCE --> VALIDATE[Response Validator<br/>Hallucination / Evidence Check]
    VALIDATE -->|pass| OUTPUT[Structured Response<br/>+ Citations]
    VALIDATE -->|fail| FALLBACK[Fallback Response<br/>Insufficient Evidence]
```

### Workflow details

#### Retrieval Workflow

```mermaid
graph TD
    Q[User Query] --> QP[Query Preprocessing<br/>Decompose / Rewrite]
    QP --> BM25[BM25 Search]
    QP --> DENSE[Dense Search]
    BM25 --> FUSE[Hybrid Fusion<br/>RRF]
    DENSE --> FUSE
    FUSE --> RERANK[Reranker<br/>Cross-Encoder]
    RERANK --> CTX[Context Selection<br/>Token Budget]
    CTX --> LLM[LLM Generation<br/>with Evidence]
```

#### SQL/Data Workflow

```mermaid
graph TD
    Q[User Query] --> SQLGEN[SQL Generation<br/>LLM + Schema Context]
    SQLGEN --> SQLEXEC[SQL Execution<br/>Read-Only]
    SQLEXEC -->|success| FORMAT[Format Results]
    SQLEXEC -->|error| SQLERR[SQL Error Handler<br/>Retry / Clarify]
    SQLERR --> SQLGEN
    FORMAT --> LLM[LLM Summarization]
```

#### Investigation Workflow

```mermaid
graph TD
    Q[User Query] --> PLAN[Investigation Planner<br/>Decompose into Steps]
    PLAN --> STEP1[Step 1: Get Invoice]
    STEP1 --> STEP2[Step 2: Get PO]
    STEP2 --> STEP3[Step 3: Get Contract]
    STEP3 --> STEP4[Step 4: Get Payments]
    STEP4 --> STEP5[Step 5: Get Policy]
    STEP5 --> COMPARE[Evidence Comparison<br/>Deterministic Rules]
    COMPARE --> EXPLAIN[LLM Explanation<br/>with Citations]
```

#### Action Workflow (with human-in-the-loop)

```mermaid
graph TD
    Q[User Request] --> VALIDATE[Validate Request<br/>Input Check]
    VALIDATE --> POLICY[Policy Check<br/>Business Rules]
    POLICY --> RISK[Risk Assessment<br/>Amount / Type / Role]
    RISK -->|low risk| EXECUTE[Execute Action]
    RISK -->|high risk| INTERRUPT[interrupt<br/>AWAITING_APPROVAL]
    INTERRUPT --> HUMAN{Human Decision}
    HUMAN -->|approve| EXECUTE
    HUMAN -->|reject| REJECT[Record Rejection]
    EXECUTE --> AUDIT[Audit Log]
    REJECT --> AUDIT
    AUDIT --> RESULT[Result Response]
```

### State design

```python
class AgentState(TypedDict):
    # Input
    user_input: str
    user_id: str
    session_id: str

    # Routing
    intent: str
    workflow: str

    # Evidence
    evidence: list[Evidence]
    citations: list[Citation]

    # Tool calls
    tool_calls: list[ToolCall]
    tool_results: list[ToolResult]

    # Action workflow
    action_request: ActionRequest | None
    approval_status: Literal["pending", "approved", "rejected", "not_required"]
    approval_decision: ApprovalDecision | None

    # Output
    response: str
    confidence: float
    errors: list[str]

    # Observability
    trace_id: str
    node_latencies: dict[str, float]
```

### Persistence

LangGraph uses **PostgreSQL checkpointing** via `langgraph.checkpoint.postgres`. This enables:

- Interrupted graph resumption
- Approval workflow persistence across restarts
- Time-travel debugging

### Error handling

| Error type | Handling |
|---|---|
| LLM timeout | Retry with backoff (max 2), then fallback response |
| SQL syntax error | LLM regenerates SQL (max 2 retries) |
| Tool failure | Log, return error to LLM for alternative approach |
| Database unavailable | Return "system unavailable" with retry guidance |
| Vector DB failure | Degrade to BM25-only retrieval |
| Hallucination detected | Reject response, request more evidence |

---

## E. Retrieval Architecture

### Pipeline

```mermaid
graph TD
    DOC[Documents<br/>PDF / HTML / TXT] --> PARSE[Document Parser<br/>PyPDF / python-docx]
    PARSE --> CHUNK[Chunker<br/>Semantic / Recursive]
    CHUNK --> META[Metadata Enrichment<br/>Entity Extraction]
    META --> EMB[Embedding Generation]
    EMB --> VSTORE[(pgvector)]
    CHUNK --> BM25STORE[(BM25 Index)]

    Q[User Query] --> QP[Query Preprocessing]
    QP --> QE[Query Embedding]
    QE --> VSEARCH[Vector Search<br/>Cosine Similarity]
    QP --> BSEARCH[BM25 Search<br/>Full-Text]

    VSEARCH --> FUSE[Hybrid Fusion<br/>Reciprocal Rank Fusion]
    BSEARCH --> FUSE
    FUSE --> RERANK[Cross-Encoder Reranker]
    RERANK --> SELECT[Context Selection<br/>Token Budget / Diversity]
    SELECT --> LLM[LLM with Context]
```

### Chunking strategy

- **Contracts**: by section (payment_terms, deliverables, limitations, termination)
- **Policies**: by clause
- **Invoices/POs**: by line item group
- **Emails**: by thread
- Target: 300–500 tokens per chunk with 50-token overlap

### Hybrid fusion

Reciprocal Rank Fusion (RRF) combines BM25 and dense scores:

```
RRF_score(d) = 1 / (k + rank_bm25(d)) + 1 / (k + rank_dense(d))
```

where k = 60 (standard constant).

### Reranking

Cross-encoder reranker (e.g., `cross-encoder/ms-marco-MiniLM-L-6-v2`) applied to top-20 hybrid results, returning top-5 for LLM context.

### Evaluation

| Metric | Target |
|---|---|
| Recall@5 | > 0.85 |
| MRR | > 0.75 |
| NDCG@5 | > 0.80 |
| Context precision | > 0.80 |
| Context recall | > 0.85 |
| Faithfulness | > 0.90 |
| Answer relevancy | > 0.85 |

---

## F. Action / Approval Architecture

### Lifecycle

```mermaid
sequenceDiagram
    participant U as User
    participant A as Agent
    participant P as Policy Engine
    participant H as Human
    participant E as External Service (MCP)
    participant DB as Audit Log

    U->>A: "Request payment for INV-1042"
    A->>A: Validate request
    A->>P: Check policy (amount, role, duplicates)
    P-->>A: Policy result
    A->>A: Risk assessment
    alt Low risk
        A->>E: Execute payment
        E-->>A: Success
        A->>DB: Audit log
        A-->>U: "Payment executed"
    else High risk
        A->>A: interrupt() — AWAITING_APPROVAL
        A-->>U: "Approval required"
        U->>H: Notify approver
        H->>A: Approve / Reject
        alt Approved
            A->>E: Execute payment
            E-->>A: Success
            A->>DB: Audit log
            A-->>U: "Payment executed"
        else Rejected
            A->>DB: Audit log
            A-->>U: "Payment rejected"
        end
    end
```

### Risk assessment matrix

| Factor | Low risk | High risk |
|---|---|---|
| Amount | < €10,000 | >= €10,000 |
| Action type | create_request | execute_payment |
| User role | manager | specialist |
| Anomaly flags | none | any |
| Duplicate check | clean | suspicious |

### Approval routing

- **Low risk**: auto-execute, audit log
- **Medium risk**: manager approval
- **High risk**: manager + finance approval

---

## G. Database Schema

### ER Diagram

```mermaid
erDiagram
    USERS ||--o{ APPROVAL_REQUESTS : creates
    USERS ||--o{ AUDIT_LOGS : generates
    DEPARTMENTS ||--o{ USERS : employs
    DEPARTMENTS ||--o{ PURCHASE_ORDERS : owns

    VENDORS ||--o{ CONTRACTS : has
    VENDORS ||--o{ PURCHASE_ORDERS : supplies
    VENDORS ||--o{ INVOICES : bills

    CONTRACTS ||--o{ PURCHASE_ORDERS : governs
    PURCHASE_ORDERS ||--o{ PURCHASE_ORDER_ITEMS : contains
    PURCHASE_ORDERS ||--o{ INVOICES : referenced_by
    INVOICES ||--o{ INVOICE_ITEMS : contains
    INVOICES ||--o{ PAYMENTS : paid_by
    INVOICES ||--o{ APPROVAL_REQUESTS : requires
    INVOICES ||--o{ EXCEPTIONS : flagged_as

    PAYMENTS ||--o{ AUDIT_LOGS : audited_by
    APPROVAL_REQUESTS ||--o{ AUDIT_LOGS : audited_by

    USERS {
        uuid id PK
        string name
        string email
        string role
        uuid department_id FK
        timestamp created_at
    }

    DEPARTMENTS {
        uuid id PK
        string name
        string code
        decimal budget_limit
    }

    VENDORS {
        uuid id PK
        string name
        string tax_id
        string country
        string status
        jsonb bank_details
        timestamp created_at
    }

    CONTRACTS {
        uuid id PK
        string contract_number
        uuid vendor_id FK
        string title
        decimal value
        decimal max_value
        string currency
        date start_date
        date end_date
        string payment_terms
        string status
        jsonb terms
    }

    PURCHASE_ORDERS {
        uuid id PK
        string po_number
        uuid contract_id FK
        uuid vendor_id FK
        uuid department_id FK
        decimal total_amount
        string currency
        string status
        date order_date
        date delivery_date
    }

    PURCHASE_ORDER_ITEMS {
        uuid id PK
        uuid po_id FK
        string description
        integer quantity
        decimal unit_price
        decimal total_price
    }

    INVOICES {
        uuid id PK
        string invoice_number
        uuid po_id FK
        uuid vendor_id FK
        decimal amount
        string currency
        date invoice_date
        date due_date
        string status
        string payment_status
    }

    INVOICE_ITEMS {
        uuid id PK
        uuid invoice_id FK
        string description
        integer quantity
        decimal unit_price
        decimal total_price
    }

    PAYMENTS {
        uuid id PK
        string payment_reference
        uuid invoice_id FK
        decimal amount
        string currency
        date payment_date
        string method
        string status
    }

    APPROVAL_REQUESTS {
        uuid id PK
        string request_type
        uuid invoice_id FK
        uuid requested_by FK
        uuid approved_by FK
        string status
        text justification
        timestamp requested_at
        timestamp decided_at
    }

    EXCEPTIONS {
        uuid id PK
        uuid invoice_id FK
        string exception_type
        string severity
        text description
        string status
        timestamp detected_at
    }

    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string action
        string entity_type
        string entity_id
        jsonb details
        timestamp created_at
    }
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_invoices_po_id ON invoices(po_id);
CREATE INDEX idx_invoices_vendor_id ON invoices(vendor_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_payments_invoice_id ON payments(invoice_id);
CREATE INDEX idx_po_contract_id ON purchase_orders(contract_id);
CREATE INDEX idx_exceptions_invoice_id ON exceptions(invoice_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(status);

-- Full-text search
CREATE INDEX idx_vendors_name_trgm ON vendors USING gin(name gin_trgm_ops);

-- Vector index (pgvector)
CREATE INDEX idx_documents_embedding ON documents USING hnsw(embedding vector_cosine_ops);
```

---

## H. Repository / File Structure

```
agentic-procurement-platform/
│
├── .github/
│   └── workflows/
│       ├── ci.yml                    # lint, format, type-check, unit tests
│       ├── integration.yml           # integration tests (requires Docker)
│       └── docker-build.yml         # Docker image build & push
│
├── configs/
│   ├── llm.yaml                      # LLM provider configs
│   ├── retrieval.yaml                # BM25, dense, reranker configs
│   ├── anomaly.yaml                  # Anomaly detection thresholds
│   └── approval.yaml                 # Risk thresholds, approval routing
│
├── data/
│   ├── raw/                          # Downloaded public data (git-ignored)
│   ├── processed/                    # Cleaned public data (git-ignored)
│   ├── synthetic/                    # Generated synthetic data (git-ignored)
│   └── evaluation/                   # Ground truth & benchmark datasets
│       ├── retrieval_benchmark.json
│       ├── sql_benchmark.json
│       ├── compliance_benchmark.json
│       ├── anomaly_ground_truth.json
│       └── agent_benchmark.json
│
├── docs/
│   ├── architecture/
│   │   ├── DESIGN.md                 # This document
│   │   ├── SYSTEM_ARCHITECTURE.md   # Detailed system architecture
│   │   └── AGENT_ARCHITECTURE.md    # Detailed agent/graph design
│   ├── data/
│   │   ├── DATA_SOURCES.md           # Public data sources & licenses
│   │   ├── SCHEMA.md                 # Database schema details
│   │   └── GENERATION.md             # Synthetic data generation guide
│   ├── evaluation/
│   │   ├── METRICS.md                # Evaluation methodology
│   │   └── RESULTS.md                # Reproducible results
│   └── decisions/
│       ├── 001-pgvector.md           # ADR: Vector store choice
│       ├── 002-langgraph.md          # ADR: Orchestration framework
│       └── 003-mcp-boundary.md       # ADR: MCP usage rationale
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Chat.tsx
│   │   │   ├── Evidence.tsx
│   │   │   ├── ApprovalPanel.tsx
│   │   │   └── AnomalyCard.tsx
│   │   └── api/
│   │       └── client.ts
│   └── Dockerfile
│
├── scripts/
│   ├── download_public_data.py       # Fetch public procurement data
│   ├── generate_synthetic_data.py    # Deterministic synthetic generator
│   ├── generate_documents.py         # Document generator (PDF/DOCX)
│   ├── inject_anomalies.py           # Anomaly injection with ground truth
│   ├── build_evaluation_set.py       # Build benchmark datasets
│   └── run_evaluations.py            # Run all evaluations
│
├── src/
│   └── procurement_ai/
│       ├── __init__.py
│       ├── main.py                   # FastAPI app entry point
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes/
│       │   │   ├── chat.py           # POST /chat — main conversation endpoint
│       │   │   ├── approvals.py      # GET/POST /approvals — approval management
│       │   │   ├── anomalies.py      # GET /anomalies — anomaly listing
│       │   │   └── health.py         # GET /health — health check
│       │   ├── schemas/
│       │   │   ├── chat.py           # Request/Response models
│       │   │   ├── approval.py
│       │   │   └── anomaly.py
│       │   └── dependencies.py       # FastAPI dependency injection
│       │
│       ├── graph/
│       │   ├── __init__.py
│       │   ├── orchestrator.py       # Main LangGraph orchestrator
│       │   ├── state.py              # AgentState definition
│       │   ├── nodes/
│       │   │   ├── guardrails.py     # Input validation nodes
│       │   │   ├── intent.py         # Intent classification & routing
│       │   │   ├── retrieval.py      # Retrieval workflow nodes
│       │   │   ├── sql.py            # SQL workflow nodes
│       │   │   ├── investigation.py  # Investigation workflow nodes
│       │   │   ├── detection.py      # Anomaly detection nodes
│       │   │   ├── action.py         # Action workflow nodes
│       │   │   └── validation.py     # Response validation nodes
│       │   └── subgraphs/
│       │       ├── retrieval_graph.py
│       │       ├── sql_graph.py
│       │       ├── investigation_graph.py
│       │       └── action_graph.py
│       │
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── base.py               # Base agent class
│       │   ├── retrieval_agent.py
│       │   ├── sql_agent.py
│       │   ├── investigation_agent.py
│       │   └── action_agent.py
│       │
│       ├── retrieval/
│       │   ├── __init__.py
│       │   ├── chunker.py            # Document chunking
│       │   ├── embedder.py           # Embedding generation
│       │   ├── bm25.py               # BM25 index
│       │   ├── dense.py              # Dense vector search
│       │   ├── fusion.py             # Hybrid fusion (RRF)
│       │   ├── reranker.py           # Cross-encoder reranking
│       │   └── context.py            # Context selection & formatting
│       │
│       ├── database/
│       │   ├── __init__.py
│       │   ├── connection.py         # SQLAlchemy async engine
│       │   ├── models.py             # SQLAlchemy ORM models
│       │   ├── migrations/           # Alembic migrations
│       │   │   └── versions/
│       │   └── repositories/         # Data access layer
│       │       ├── invoice_repo.py
│       │       ├── po_repo.py
│       │       ├── contract_repo.py
│       │       └── vendor_repo.py
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py           # Tool registry & discovery
│       │   ├── base.py               # Base tool class
│       │   ├── read_tools.py         # Read-only tools (get_invoice, etc.)
│       │   ├── query_tools.py        # SQL query tools
│       │   ├── analysis_tools.py     # Python analysis tools
│       │   ├── detection_tools.py    # Anomaly detection tools
│       │   └── action_tools.py       # Write/action tools (require approval)
│       │
│       ├── mcp/
│       │   ├── __init__.py
│       │   ├── client.py             # MCP client
│       │   └── server.py             # MCP server (mock ERP)
│       │
│       ├── documents/
│       │   ├── __init__.py
│       │   ├── parser.py             # PDF/DOCX/TXT parsing
│       │   ├── generator.py          # Synthetic document generator
│       │   └── extractor.py          # Entity/metadata extraction
│       │
│       ├── guardrails/
│       │   ├── __init__.py
│       │   ├── input_guard.py        # PII, injection, auth checks
│       │   ├── output_guard.py       # Hallucination, evidence checks
│       │   └── tool_guard.py         # Tool authorization, idempotency
│       │
│       ├── anomaly_detection/
│       │   ├── __init__.py
│       │   ├── rules.py              # Deterministic business rules
│       │   ├── ml_detector.py        # Isolation Forest / LOF
│       │   └── feature_engineering.py
│       │
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── retrieval_eval.py     # Recall@K, MRR, NDCG
│       │   ├── rag_eval.py           # Faithfulness, relevancy
│       │   ├── agent_eval.py         # Tool selection, routing accuracy
│       │   ├── business_eval.py      # Anomaly precision/recall
│       │   └── runner.py             # Evaluation orchestrator
│       │
│       ├── observability/
│       │   ├── __init__.py
│       │   ├── tracing.py            # OpenTelemetry setup
│       │   ├── metrics.py            # Prometheus metrics
│       │   └── logging.py            # Structured logging
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── llm.py                # LLM provider abstraction
│       │   └── embeddings.py         # Embedding provider abstraction
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── settings.py           # Pydantic settings (env vars)
│       │   └── constants.py          # Business constants
│       │
│       └── utils/
│           ├── __init__.py
│           ├── idempotency.py        # Idempotency key handling
│           └── retry.py              # Retry with backoff
│
├── tests/
│   ├── unit/
│   │   ├── test_guardrails.py
│   │   ├── test_retrieval.py
│   │   ├── test_anomaly_rules.py
│   │   ├── test_tools.py
│   │   └── test_state.py
│   ├── integration/
│   │   ├── test_graph.py
│   │   ├── test_sql_agent.py
│   │   ├── test_action_workflow.py
│   │   └── test_api.py
│   ├── evaluation/
│   │   ├── test_retrieval_eval.py
│   │   ├── test_rag_eval.py
│   │   └── test_agent_eval.py
│   └── e2e/
│       ├── test_invoice_investigation.py
│       ├── test_payment_approval.py
│       └── test_anomaly_detection.py
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.frontend
│   └── Dockerfile.mcp
│
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── .gitignore
├── .dockerignore
├── Makefile
└── README.md
```

### Directory responsibilities

| Path | Responsibility | What belongs | What does NOT belong |
|---|---|---|---|
| `src/procurement_ai/api/` | HTTP layer | Routes, request/response schemas, dependency injection | Business logic, DB queries |
| `src/procurement_ai/graph/` | Orchestration | LangGraph nodes, edges, state, routing | Direct DB/LLM calls |
| `src/procurement_ai/agents/` | Agent logic | Agent classes that use tools | Graph topology |
| `src/procurement_ai/retrieval/` | Search & ranking | Chunking, embedding, BM25, fusion, reranking | Document generation |
| `src/procurement_ai/database/` | Persistence | ORM models, repositories, migrations | Business rules |
| `src/procurement_ai/tools/` | Tool contracts | Tool definitions, input/output schemas, auth | Graph nodes |
| `src/procurement_ai/mcp/` | External boundary | MCP client/server, mock ERP | Internal tools |
| `src/procurement_ai/documents/` | Document handling | Parsing, generation, extraction | Retrieval logic |
| `src/procurement_ai/guardrails/` | Safety | Input/output/tool validation | Business logic |
| `src/procurement_ai/anomaly_detection/` | Detection | Rules, ML models, features | Data generation |
| `src/procurement_ai/evaluation/` | Evaluation | Metrics, benchmarks, runners | Production logic |
| `src/procurement_ai/observability/` | Monitoring | Tracing, metrics, logging | Business logic |
| `src/procurement_ai/models/` | Abstractions | LLM/embedding provider interfaces | Provider-specific code |
| `src/procurement_ai/config/` | Configuration | Settings, constants, env vars | Business logic |
| `scripts/` | Data pipeline | Download, generate, inject, evaluate | Application code |
| `tests/` | Quality | Test code, fixtures, conftest | Application code |

---

## I. API Design

### Endpoints

#### POST /chat

Main conversation endpoint.

**Request:**
```json
{
  "message": "Why is invoice INV-1042 overdue?",
  "user_id": "user-123",
  "session_id": "sess-456"
}
```

**Response:**
```json
{
  "response": "Invoice INV-1042 is €18,400 and is 17 days overdue...",
  "citations": [
    {"source": "invoice:INV-1042", "snippet": "Amount: €18,400, Due: 2025-09-15"},
    {"source": "payment:PAY-991", "snippet": "No payment found"}
  ],
  "confidence": 0.92,
  "workflow": "investigation",
  "trace_id": "trace-789"
}
```

#### GET /anomalies

List detected anomalies.

**Query params:** `?severity=high&status=open&limit=50`

**Response:**
```json
{
  "anomalies": [
    {
      "id": "exc-001",
      "invoice_id": "INV-1042",
      "type": "missing_approval",
      "severity": "high",
      "description": "Invoice exceeds PO amount by €2,400",
      "status": "open",
      "detected_at": "2025-10-01T10:00:00Z"
    }
  ],
  "total": 1
}
```

#### GET /approvals

List pending approval requests.

**Query params:** `?status=pending&user_id=user-123`

#### POST /approvals/{approval_id}/decide

Approve or reject a pending action.

**Request:**
```json
{
  "decision": "approve",
  "comment": "Verified with vendor"
}
```

#### GET /health

Health check for Docker/Compose.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "api": "up",
    "postgres": "up",
    "vector_db": "up"
  }
}
```

---

## J. Tool Design

### Read-only tools (no approval required)

| Tool | Input | Output | Description |
|---|---|---|---|
| `get_invoice` | `invoice_id: str` | `Invoice` | Retrieve single invoice |
| `get_purchase_order` | `po_id: str` | `PurchaseOrder` | Retrieve single PO |
| `get_contract` | `contract_id: str` | `Contract` | Retrieve single contract |
| `get_vendor` | `vendor_id: str` | `Vendor` | Retrieve vendor details |
| `get_payment_status` | `invoice_id: str` | `PaymentStatus` | Check payment status |
| `search_documents` | `query: str, filters?: dict` | `list[DocumentChunk]` | Hybrid document search |
| `query_procurement_db` | `sql: str` (read-only) | `list[dict]` | Execute read-only SQL |
| `run_business_analysis` | `query: str` | `AnalysisResult` | Python data analysis |
| `detect_anomalies` | `entity_type: str, entity_id?: str` | `list[Anomaly]` | Run anomaly detection |
| `check_policy` | `entity_type: str, entity_id: str` | `PolicyCheckResult` | Check policy compliance |
| `get_approval_status` | `approval_id: str` | `ApprovalStatus` | Check approval status |

### Write/action tools (require approval)

| Tool | Input | Output | Description |
|---|---|---|---|
| `create_approval_request` | `request_type, entity_id, justification` | `ApprovalRequest` | Create approval request |
| `execute_controlled_action` | `action_type, entity_id, params` | `ActionResult` | Execute after approval |

### Tool contract example

```python
class GetInvoiceInput(BaseModel):
    invoice_id: str = Field(..., description="Invoice identifier, e.g., INV-1042")


class GetInvoiceOutput(BaseModel):
    invoice_id: str
    po_id: str
    vendor_id: str
    amount: float
    currency: str
    status: str
    due_date: date
    payment_status: str


@tool
def get_invoice(invoice_id: str) -> GetInvoiceOutput:
    """Retrieve a single invoice by its ID.
    Use when the user asks about a specific invoice.
    Returns full invoice details including payment status.
    """
    ...
```

---

## K. MCP Architecture

### Where MCP belongs

MCP provides a **clean architectural boundary** between the agent platform and an external mock ERP/payment service. It is NOT used as a resume keyword — it represents a real integration boundary.

```mermaid
graph LR
    AGENT[LangGraph Agent] -->|MCP Client| MCP[MCP Server]
    MCP -->|Mock ERP API| ERP[(Mock ERP<br/>PostgreSQL)]
    MCP -->|Mock Payment API| PAY[(Mock Payment<br/>Service)]
```

### Why MCP is used here

1. **Simulates real integration** — in production, this would be a real ERP (SAP, Oracle)
2. **Protocol boundary** — the agent speaks MCP, the ERP speaks its own protocol
3. **Testability** — the mock ERP can be replaced with a real one without changing agent code
4. **Tool discovery** — MCP provides standard tool discovery and schema

### MCP server tools

| Tool | Description |
|---|---|
| `create_payment_request` | Submit payment to mock ERP |
| `get_payment_status` | Check payment status in mock ERP |
| `create_exception` | Create exception record in mock ERP |
| `update_workflow_status` | Update workflow state in mock ERP |

---

## L. Security / Guardrails

### Input guardrails

| Check | Implementation | Action on failure |
|---|---|---|
| PII detection | Presidio / regex patterns | Redact, log warning |
| Prompt injection | LLM-based classifier + pattern matching | Reject, log incident |
| Input length | Max 2000 chars | Reject with message |
| Authorization | JWT + role check | 403 Forbidden |
| Rate limiting | 100 req/min per user | 429 Too Many Requests |

### Tool-layer guardrails

| Check | Implementation | Action on failure |
|---|---|---|
| Tool authorization | Role-based tool access | Reject, log |
| Idempotency | Idempotency-Key header | Return cached result |
| Input validation | Pydantic schemas | 422 Unprocessable |
| High-risk confirmation | Risk assessment matrix | Require approval |
| SQL injection | Read-only SQL + parameterized queries | Reject |

### Output guardrails

| Check | Implementation | Action on failure |
|---|---|---|
| Hallucination detection | NLI model / evidence overlap | Reject, request more evidence |
| Evidence requirement | Every claim must have citation | Reject unsupported claims |
| PII redaction | Presidio / regex | Redact before returning |
| Unsupported claim | LLM judge | Flag as "interpretation" |

---

## M. Evaluation Framework

### Datasets

| Dataset | Size | Purpose |
|---|---|---|
| `retrieval_benchmark.json` | 200 queries | Recall@K, MRR, NDCG |
| `sql_benchmark.json` | 100 questions | SQL accuracy, execution accuracy |
| `compliance_benchmark.json` | 50 cases | Policy violation detection |
| `anomaly_ground_truth.json` | 500 records | Anomaly precision/recall |
| `agent_benchmark.json` | 100 tasks | Tool selection, routing, completion |

### Metrics

| Category | Metrics |
|---|---|
| Retrieval | Recall@K, Precision@K, MRR, NDCG |
| RAG | Faithfulness, Context Precision, Context Recall, Answer Relevancy |
| Agent | Tool Selection Accuracy, Routing Accuracy, Workflow Completion Rate |
| Business | Anomaly Precision, Anomaly Recall, Policy Violation F1, False Positive Rate |
| System | P50/P95 Latency, Throughput, Error Rate |

### Evaluation scripts

```bash
# Run all evaluations
python scripts/run_evaluations.py --all

# Run specific evaluation
python scripts/run_evaluations.py --retrieval --benchmark data/evaluation/retrieval_benchmark.json

# Generate report
python scripts/run_evaluations.py --report --output docs/evaluation/RESULTS.md
```

---

## N. Testing Strategy

### Test pyramid

```mermaid
graph TD
    E2E[E2E Tests<br/>Full workflows] --> INT[Integration Tests<br/>Graph + DB + LLM]
    INT --> UNIT[Unit Tests<br/>Functions & Classes]
```

### Test categories

| Category | Examples | Count target |
|---|---|---|
| Unit | Guardrail functions, chunker, fusion, rules | 100+ |
| Integration | Graph execution, SQL generation, tool calls | 50+ |
| Evaluation | Retrieval metrics, RAG quality, agent accuracy | 30+ |
| E2E | Full invoice investigation, payment approval | 10+ |

### Failure path testing

- Missing invoice → graceful "not found" response
- Invalid PO → validation error
- Database timeout → retry + fallback
- Vector DB failure → BM25-only degradation
- LLM timeout → retry + fallback message
- Tool failure → alternative approach
- Duplicate action → idempotency check
- Approval rejection → proper audit trail
- Resumed interrupted graph → correct state restoration
- Unauthorized action → 403 + audit log

---

## O. Docker Architecture

### Services

```yaml
# docker-compose.yml
services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@postgres:5432/procurement
      - VECTOR_DB_URL=postgresql+asyncpg://user:pass@postgres:5432/procurement
      - LLM_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - app-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api
    networks:
      - app-network

  mcp_server:
    build:
      context: .
      dockerfile: docker/Dockerfile.mcp
    ports:
      - "8001:8001"
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - app-network

  postgres:
    image: pgvector/pgvector:pg16
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=procurement
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d procurement"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - app-network

  prometheus:
    image: prom/prometheus
    volumes:
      - ./configs/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
    networks:
      - app-network

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
    driver: bridge
```

### Networks

- **app-network**: all services communicate internally
- No external network exposure except through mapped ports

### Volumes

- **postgres_data**: persistent database storage

---

## P. CI/CD

### GitHub Actions workflows

#### ci.yml — Pull requests

```yaml
name: CI
on:
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run mypy src/

  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run pytest tests/unit/ -v --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v4
```

#### integration.yml — Main branch

```yaml
name: Integration Tests
on:
  push:
    branches: [main]

jobs:
  integration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: user
          POSTGRES_PASSWORD: pass
          POSTGRES_DB: procurement
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run pytest tests/integration/ -v
      - run: uv run pytest tests/evaluation/ -v
```

#### docker-build.yml — Releases

```yaml
name: Docker Build
on:
  release:
    types: [published]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: docker/Dockerfile.api
          push: true
          tags: ghcr.io/${{ github.repository }}/api:${{ github.event.release.tag_name }}
```

---

## Q. Observability

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2026-10-01T10:00:00Z",
  "level": "INFO",
  "trace_id": "trace-789",
  "span_id": "span-001",
  "user_id": "user-123",
  "session_id": "sess-456",
  "node": "retrieval",
  "event": "tool_call",
  "tool": "get_invoice",
  "latency_ms": 45,
  "status": "success"
}
```

### Metrics (Prometheus)

| Metric | Type | Description |
|---|---|---|
| `agent_requests_total` | Counter | Total requests by intent |
| `agent_request_duration_seconds` | Histogram | End-to-end latency |
| `node_duration_seconds` | Histogram | Per-node latency |
| `llm_calls_total` | Counter | LLM calls by provider |
| `llm_tokens_total` | Counter | Token usage by type |
| `retrieval_latency_seconds` | Histogram | Retrieval pipeline latency |
| `tool_calls_total` | Counter | Tool calls by name |
| `tool_errors_total` | Counter | Tool errors by name |
| `approval_requests_total` | Counter | Approvals by status |
| `anomalies_detected_total` | Counter | Anomalies by type |

### Tracing

- **OpenTelemetry** for distributed tracing
- **LangSmith** for LLM-specific tracing (prompt/completion tracking)
- Every graph execution produces a trace with node-level spans

### Dashboards (Grafana)

1. **Overview** — request rate, error rate, latency percentiles
2. **Agent** — intent distribution, workflow completion rate, node latency
3. **LLM** — token usage, cost, latency, error rate
4. **Retrieval** — BM25 vs dense vs hybrid latency, reranker latency
5. **Approvals** — pending approvals, approval rate, rejection rate

---

## R. Development Roadmap

### Phase 1 — Foundation (Week 1)

**Objective:** Project skeleton, database, data generation

- Set up `pyproject.toml`, project structure
- Define SQLAlchemy models + Alembic migrations
- Implement data generation scripts (public data + synthetic)
- Set up Docker Compose (PostgreSQL + pgvector)
- Write unit tests for data generation

**Expected result:** Database populated with realistic data, all tests pass

### Phase 2 — Retrieval (Week 2)

**Objective:** Document ingestion and hybrid retrieval pipeline

- Implement document parser and chunker
- Set up pgvector, embedding generation
- Implement BM25 + dense + hybrid fusion + reranker
- Write retrieval evaluation tests

**Expected result:** Retrieval pipeline working, Recall@5 > 0.80

### Phase 3 — Agent Core (Week 3)

**Objective:** LangGraph orchestrator with retrieval + SQL workflows

- Implement AgentState, orchestrator graph
- Implement retrieval workflow
- Implement SQL workflow (read-only)
- Implement intent classifier
- Write integration tests for graph execution

**Expected result:** Agent can answer "Why is INV-1042 overdue?" with evidence

### Phase 4 — Investigation & Detection (Week 4)

**Objective:** Multi-step investigation + anomaly detection

- Implement investigation workflow
- Implement deterministic anomaly rules
- Implement ML anomaly detection (Isolation Forest)
- Implement policy engine
- Write evaluation tests

**Expected result:** Agent can detect anomalies with known ground truth

### Phase 5 — Action & Approval (Week 5)

**Objective:** Human-in-the-loop action workflow

- Implement action workflow with interrupts
- Set up LangGraph PostgreSQL checkpointing
- Implement MCP server (mock ERP)
- Implement approval API endpoints
- Write E2E tests for approval flow

**Expected result:** Payment request → approval → execution works end-to-end

### Phase 6 — Hardening & Polish (Week 6)

**Objective:** Guardrails, observability, evaluation, documentation

- Implement input/output/tool guardrails
- Set up OpenTelemetry + Prometheus + Grafana
- Run full evaluation suite, document results
- Write README, architecture docs
- Set up CI/CD

**Expected result:** Production-ready portfolio project

---

## S. Portfolio Presentation

### Project title

**Agentic Procurement Intelligence & Operations Platform**

### One-line description

An agentic AI platform that lets enterprise procurement teams investigate operational issues across databases and documents using natural language, with evidence-backed answers, anomaly detection, and human-in-the-loop approval workflows.

### README structure

1. **Badges** — CI status, coverage, Python version, license
2. **Demo** — GIF/screenshot of the UI
3. **Quick Start** — `docker compose up` + example queries
4. **Architecture** — Link to design doc + diagram
5. **Features** — FIND, UNDERSTAND, INVESTIGATE, DETECT, ACT
6. **Evaluation** — Link to results
7. **Development** — Setup, testing, contributing
8. **License** — MIT

### Technical highlights to emphasize

1. **LangGraph orchestration** with persistent checkpointing and interrupts
2. **Hybrid retrieval** (BM25 + dense + RRF + cross-encoder reranking)
3. **Provider-agnostic LLM/embedding** abstraction
4. **Deterministic + ML anomaly detection** with known ground truth
5. **Human-in-the-loop** approval workflow with full audit trail
6. **MCP boundary** to mock external ERP
7. **Comprehensive evaluation** — retrieval, RAG, agent, business metrics
8. **Production-oriented** — Docker, CI/CD, observability, guardrails

### Limitations to acknowledge

- Mock ERP (not a real payment system)
- Synthetic data (not real company data)
- Single-tenant (no multi-tenancy)
- English only
- No real authentication (mock auth)

### Future improvements

- Multi-tenant architecture
- Real ERP integration (SAP, Oracle)
- Streaming responses
- Multi-modal document understanding (scanned PDFs, images)
- Advanced analytics (forecasting, trend analysis)
- Fine-tuned domain model

---

## Appendix: End-to-End Scenario Walkthroughs

### Scenario 1: "Why is invoice INV-1042 overdue?"

1. **Input guardrails** — pass (no PII, no injection)
2. **Intent classifier** → `investigate`
3. **Investigation workflow:**
   - `get_invoice(INV-1042)` → amount=€18,400, due=2025-09-15, status=unpaid
   - `get_purchase_order(PO-7781)` → contract_id=C-201
   - `get_contract(C-201)` → payment_terms=Net-30, max_value=€100,000
   - `get_payment_status(INV-1042)` → no payment found
   - `search_documents("payment policy")` → policy requires payment within 30 days
4. **Evidence aggregator** — combines all tool results
5. **Response validator** — all claims have citations
6. **Output:** "Invoice INV-1042 is €18,400 and is 17 days overdue. It is associated with PO-7781 and the contract specifies Net-30 payment terms. No payment transaction has been recorded. The invoice is therefore currently unpaid and past its contractual due date."

### Scenario 2: "Does INV-1042 comply with its PO and contract?"

1. **Intent** → `investigate`
2. **Investigation workflow:**
   - `get_invoice(INV-1042)` → amount=€18,400, vendor=V-101
   - `get_purchase_order(PO-7781)` → amount=€16,000, vendor=V-101
   - `get_contract(C-201)` → max_value=€100,000, vendor=V-101
   - `check_policy(INV-1042)` → invoice exceeds PO by €2,400
3. **Comparison:**
   - Amount: invoice (€18,400) > PO (€16,000) → **mismatch**
   - Vendor: match
   - Currency: match
   - Contract limit: invoice (€18,400) < contract (€100,000) → OK
4. **Output:** "Potential mismatch detected: Invoice amount (€18,400) exceeds PO amount (€16,000) by €2,400. Vendor and currency match. Invoice is within contract limit."

### Scenario 3: "Find transactions that may violate procurement policy"

1. **Intent** → `detect`
2. **Detection workflow:**
   - `detect_anomalies(entity_type="invoice")` → runs deterministic rules + ML
   - Returns: INV-1042 (missing approval), PO-8821 (exceeds contract), INV-2214 (duplicate)
3. **Policy verification:**
   - `search_documents("procurement policy")` → relevant policy sections
   - `check_policy()` for each candidate
4. **Output:** List of potential violations with evidence and severity

### Scenario 4: "Find duplicate invoices"

1. **Intent** → `detect`
2. **Detection workflow:**
   - `detect_anomalies(entity_type="invoice", check="duplicate")`
   - Deterministic fuzzy matching on (vendor, amount, date, line_items)
3. **Output:** List of potential duplicate groups with similarity scores

### Scenario 5: "Request payment for INV-1042"

1. **Intent** → `act`
2. **Action workflow:**
   - `get_invoice(INV-1042)` → valid, unpaid
   - `get_payment_status(INV-1042)` → no existing payment
   - `check_policy(INV-1042)` → amount=€18,400, requires manager approval
   - **Risk assessment:** high risk (amount > €10,000)
   - **interrupt()** → AWAITING_APPROVAL
3. **Output:** "Payment request created. Approval required from manager."

### Scenario 6: Human approves the payment

1. **POST /approvals/{id}/decide** → `{"decision": "approve"}`
2. **Graph resumes:**
   - `execute_controlled_action("payment", INV-1042)` → MCP call to mock ERP
   - Mock ERP processes payment → success
   - `audit_log` records the action
3. **Output:** "Payment executed successfully. Reference: PAY-2025-001."

### Scenario 7: Human rejects the payment

1. **POST /approvals/{id}/decide** → `{"decision": "reject", "comment": "Vendor verification pending"}`
2. **Graph resumes:**
   - `audit_log` records the rejection
   - No MCP call made
3. **Output:** "Payment rejected. Reason: Vendor verification pending."

### Scenario 8: Tool/database fails during workflow

1. **Investigation workflow** → `get_invoice(INV-1042)` → database timeout
2. **Error handling:**
   - Retry with backoff (max 2)
   - If still failing → return error to LLM
   - LLM tries alternative: `search_documents("INV-1042")` → document search succeeds
3. **Output:** "I had trouble accessing the database directly, but found the invoice in document records: [partial evidence]. Please try again later for full details."

### Scenario 9: Graph interrupted and resumed later

1. **Action workflow** → `interrupt()` → AWAITING_APPROVAL
2. **Checkpoint saved** to PostgreSQL
3. **API restarts** (deploy, crash, etc.)
4. **User returns** → `GET /approvals` → pending approval still exists
5. **User approves** → graph resumes from checkpoint
6. **Execution continues** → payment processed

### Scenario 10: Unrelated question outside procurement domain

1. **Input guardrails** — pass
2. **Intent classifier** → `out_of_scope`
3. **Output:** "I'm designed to help with procurement and finance operations. I can help you investigate invoices, purchase orders, contracts, payments, and procurement policies. Could you rephrase your question in that context?"

---

## Architectural Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM hallucination | Incorrect answers | Evidence requirement, citations, hallucination detection |
| SQL injection | Data breach | Read-only SQL, parameterized queries, no DDL/DML |
| Prompt injection | Unauthorized actions | Input guardrails, tool authorization, approval gates |
| Vector DB failure | Retrieval degradation | BM25 fallback, graceful degradation |
| LLM latency | Slow responses | Async execution, streaming, caching |
| Data inconsistency | Wrong answers | Deterministic generation, referential integrity checks |
| Approval workflow abuse | Unauthorized actions | Role-based routing, audit logging, idempotency |

---

*End of design document.*
