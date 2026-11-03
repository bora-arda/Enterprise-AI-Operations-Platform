# System Architecture

## Overview

The Agentic Procurement Intelligence & Operations Platform is a production-oriented system that provides a natural-language interface over heterogeneous procurement data sources.

## Architecture Layers

### 1. Client Layer

- **Web UI** — React-based single-page application
- **API Clients** — Direct REST API access via FastAPI

### 2. API Layer (FastAPI)

- Request validation (Pydantic)
- Authentication & authorization (JWT)
- Rate limiting
- Request routing
- OpenAPI documentation

### 3. Orchestration Layer (LangGraph)

- **Main Orchestrator** — Routes requests to appropriate workflows
- **Retrieval Workflow** — Hybrid BM25 + dense retrieval with reranking
- **SQL Workflow** — Natural language to SQL with read-only execution
- **Investigation Workflow** — Multi-step evidence gathering
- **Detection Workflow** — Anomaly and policy violation detection
- **Action Workflow** — Human-in-the-loop approval workflows

### 4. Capability Layer

- **Retrieval** — BM25, dense embeddings, hybrid fusion, cross-encoder reranking
- **Database** — PostgreSQL with pgvector
- **Intelligence** — Anomaly detection (deterministic + ML), policy engine
- **Execution** — MCP client/server for external ERP boundary

### 5. External Services

- **LLM Provider** — OpenAI or Ollama (provider-agnostic)
- **Embedding Provider** — OpenAI or sentence-transformers
- **MCP Server** — Mock ERP/payment service

### 6. Observability Layer

- **OpenTelemetry** — Distributed tracing
- **Prometheus** — Metrics collection
- **Grafana** — Dashboards
- **LangSmith** — LLM-specific tracing

## Data Flow

```
User Query
    ↓
FastAPI (validation, auth)
    ↓
LangGraph Orchestrator
    ↓
Intent Classification
    ↓
Workflow Execution (retrieval / SQL / investigation / detection / action)
    ↓
Evidence Aggregation
    ↓
Response Validation
    ↓
Structured Response + Citations
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Docker Compose                      │
│                                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │   API   │  │Frontend │  │   MCP   │  │Prometheus│   │
│  │ :8000   │  │ :3000   │  │ :8001   │  │ :9090   │    │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │
│       │            │            │            │          │
│       └────────────┴────────────┴────────────┘          │
│                         │                                │
│                  ┌──────┴──────┐                        │
│                  │  PostgreSQL  │                        │
│                  │  + pgvector  │                        │
│                  │   :5432      │                        │
│                  └─────────────┘                        │
│                                                          │
│                  ┌─────────────┐                        │
│                  │   Grafana   │                        │
│                  │   :3001     │                        │
│                  └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

## Security Architecture

- **Input Guardrails** — PII detection, prompt injection prevention, input validation
- **Tool Authorization** — Role-based access control for tools
- **Output Guardrails** — Hallucination detection, evidence requirement, PII redaction
- **Approval Workflows** — Human-in-the-loop for high-risk actions
- **Audit Logging** — Complete audit trail for all actions

## Scalability Considerations

- **Horizontal Scaling** — API and MCP servers are stateless
- **Database** — Read replicas for query scaling
- **Caching** — Redis for frequent queries (future)
- **Async Processing** — Background tasks for long-running operations
