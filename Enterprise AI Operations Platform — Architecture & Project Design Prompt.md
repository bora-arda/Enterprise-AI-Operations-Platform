You are a senior AI/ML engineer and software architect. I want you to design a complete, production-oriented portfolio project called:

**Agentic Procurement Intelligence & Operations Platform**

The goal is NOT to build a simple chatbot or a generic RAG demo. I want a substantial public GitHub project that demonstrates strong skills in:

- Data Science
- Machine Learning
- AI Engineering
- Agentic systems
- LangGraph
- RAG
- Hybrid retrieval
- SQL/tool use
- Document intelligence
- Business-rule validation
- Anomaly detection
- Human-in-the-loop workflows
- MCP/tool execution
- Evaluation
- Observability
- Testing
- Docker
- CI/CD
- Production-oriented architecture

The project should also indirectly demonstrate the type of agentic workflow architecture I have experience with in a private/NDA project, without copying that project's domain or implementation.

---

# 1. BUSINESS PROBLEM

The project simulates an enterprise procurement/finance environment.

In a real company, procurement information is distributed across multiple systems:

- Procurement/tender records
- Vendors
- Contracts
- Purchase orders
- Invoices
- Payments
- Approval records
- Procurement policies
- Vendor policies
- Contract documents
- Emails/operational notes

Employees normally have to manually navigate several systems to answer questions or investigate problems.

For example, answering:

> "Why hasn't invoice INV-1042 been paid?"

may require checking:

1. Invoice database
2. Purchase order
3. Contract
4. Payment records
5. Procurement policy
6. Approval history

The platform should provide a natural-language interface over these heterogeneous sources.

The core product promise is:

> **Allow enterprise users to ask operational questions in natural language, investigate issues across structured and unstructured data, provide evidence-backed answers, detect potential anomalies or policy violations, and initiate controlled business workflows when appropriate.**

The system should therefore support five major capabilities:

### 1. FIND
Find information across databases and documents.

### 2. UNDERSTAND
Combine structured data and document knowledge to explain what something means.

### 3. INVESTIGATE
Perform multi-step investigations across multiple tools and sources.

### 4. DETECT
Identify potential anomalies, inconsistencies, duplicates, or policy violations.

### 5. ACT
Initiate controlled actions, with human approval for high-risk operations.

The project should NOT claim to autonomously make financial or legal decisions. It should present potential anomalies/risk indicators and provide evidence for human review.

---

# 2. TARGET USERS

Design the system for several realistic user personas.

## Procurement Specialist

Examples:

- "Show me purchase orders that exceed their contract limits."
- "Which vendors have the most procurement exceptions?"
- "What are the payment terms for Vendor X?"
- "Does PO-1821 comply with the associated contract?"

## Accounts Payable / Finance

Examples:

- "Which invoices are overdue?"
- "Why is INV-1042 overdue?"
- "Does this invoice match its purchase order?"
- "Is there already a payment associated with this invoice?"
- "Find potentially duplicate invoices."

## Procurement Manager

Examples:

- "Which vendors caused the most exceptions this quarter?"
- "What are the most common procurement issues?"
- "Show me spending by category."
- "Why is Vendor A generating so many exceptions?"

## Compliance / Internal Audit

Examples:

- "Find transactions that may violate procurement policy."
- "Show me the evidence for the flagged invoices."
- "Which transactions are missing required approvals?"
- "Find potential duplicate payments."

## Vendor Manager

Examples:

- "Which vendor contracts expire within 60 days?"
- "Which vendors have outstanding invoices?"
- "Which vendors have repeated compliance issues?"

## Contract / Legal Operations

Examples:

- "What are Vendor X's payment terms?"
- "Does this purchase order comply with the contract?"
- "Which contracts contain spending limits?"
- "Which contracts are approaching expiration?"

## General Business Employee

Examples:

- "What is the process for purchasing new laptops?"
- "Do I need manager approval for a €15,000 purchase?"
- "Can you start a procurement request?"

---

# 3. CORE USE CASES

The system should support at least the following workflows.

## Use Case A — Operational Investigation

User:

> "Why is invoice INV-1042 overdue?"

The agent should potentially:

1. Retrieve the invoice from SQL.
2. Check its due date.
3. Check payment records.
4. Retrieve the associated purchase order.
5. Retrieve the relevant contract.
6. Retrieve relevant procurement/payment policies.
7. Compare the evidence.
8. Produce an evidence-backed explanation.

Example answer:

> Invoice INV-1042 is €18,400 and is 17 days overdue. It is associated with PO-7781 and the contract specifies Net-30 payment terms. No payment transaction has been recorded. The invoice is therefore currently unpaid and past its contractual due date.

The answer must expose relevant evidence/citations rather than hallucinating facts.

---

# 4. USE CASE B — Contract / PO / Invoice Compliance

User:

> "Does invoice INV-1042 comply with its purchase order and contract?"

The system should retrieve:

- Invoice
- PO
- Contract
- Relevant policy

Then compare:

- Amount
- Vendor
- Currency
- Dates
- Line items if available
- Contract limits
- Approval requirements
- Payment terms

The result should distinguish:

- Valid
- Potential mismatch
- Potential policy violation
- Insufficient evidence

Do NOT make unsupported legal conclusions.

---

# 5. USE CASE C — Policy Violation Investigation

User:

> "Find transactions that may violate our procurement policy."

The system should:

1. Query structured procurement data.
2. Apply deterministic/rule-based candidate filters.
3. Retrieve relevant policy documents.
4. Verify candidates against policy.
5. Produce a list of potential violations.
6. Explain the evidence for each candidate.

Example:

```text
INV-1042
Potential issue: missing required approval

PO-8821
Potential issue: amount exceeds contract limit

INV-2214
Potential duplicate payment
```

The system should clearly distinguish:

- deterministic rule violations
- ML/anomaly signals
- LLM-generated interpretations

---

# 6. USE CASE D — Duplicate / Anomaly Detection

The platform should support potential anomaly detection.

Examples:

- Duplicate invoices
- Invoice amount > PO amount
- Invoice amount > contract limit
- Invoice associated with an invalid/nonexistent PO
- Invoice submitted after contract expiration
- Already-paid invoice submitted again
- Vendor mismatch
- Unusual transaction amount
- Missing approval
- Contract/PO mismatch

Consider using both:

### Deterministic rules

For known business constraints.

### Classical ML / anomaly detection

For unusual patterns.

Potential approaches can include:

- Isolation Forest
- Local Outlier Factor
- statistical thresholds
- clustering
- rule-based detection

Do not force ML where a deterministic rule is more appropriate.

---

# 7. USE CASE E — Human-in-the-Loop Action

User:

> "Request payment for INV-1042."

The system should NOT blindly execute a payment.

Workflow:

```text
User request
    ↓
Validate invoice
    ↓
Check duplicate/payment status
    ↓
Check PO
    ↓
Check contract
    ↓
Check policy
    ↓
Determine approval requirement
    ↓
Human approval if required
    ↓
Execute controlled action
    ↓
Record result
```

For high-risk operations:

```text
Agent
  ↓
interrupt()
  ↓
AWAITING_APPROVAL
  ↓
Human
  ├── Approve
  └── Reject
  ↓
Resume graph
  ↓
Execute / Reject
```

The workflow must be persistent and resumable.

---

# 8. USE CASE F — Exception Resolution

Example:

> "Why does INV-1042 not match PO-8821?"

The agent should compare:

```text
Invoice amount
PO amount
Contract amount/limit
Vendor
Currency
Line items
Dates
```

Then explain the discrepancy.

A user may then request:

> "Create an exception request for this invoice."

This should create a workflow requiring the appropriate approval.

---

# 9. USE CASE G — Management Analytics

The system should support questions such as:

- "Which vendors have the most exceptions?"
- "What are our top procurement categories?"
- "What percentage of invoices are overdue?"
- "Which vendors have the highest average invoice value?"
- "What are the most common policy violations?"
- "Show procurement spending by month."
- "What changed compared with the previous quarter?"

These may require SQL and/or analytical Python tools rather than RAG.

The architecture should make it clear when the system should use:

- SQL
- retrieval
- Python/data analysis
- anomaly detection
- multiple tools

---

# 10. DATA STRATEGY

Do NOT make the entire dataset random LLM-generated mock data.

Use a hybrid data strategy.

## Layer 1 — REAL PUBLIC DATA

Use public procurement datasets as the backbone.

Potential sources include:

- Open Contracting Partnership Data Registry
- UK Contracts Finder
- OpenTender / EU procurement datasets
- Other openly licensed procurement datasets

The public data should provide realistic:

- Buyers
- Suppliers/vendors
- Tenders
- Awards
- Contracts
- Categories
- Contract values
- Dates
- Procurement relationships

The exact source should be selected based on licensing, accessibility, quality, and ease of reproducibility.

Clearly document the source and license.

Do not claim that public procurement data represents a private company's internal ERP.

---

# 11. SYNTHETIC ENTERPRISE DATA

Build a deterministic synthetic enterprise layer around the public procurement backbone.

Generate:

- Purchase orders
- Invoices
- Payment records
- Approval requests
- Departments
- Users/roles
- Internal policies
- Vendor records/extensions
- Operational events
- Email threads
- Exception records

The synthetic data must maintain referential integrity.

For example:

```text
Public Contract
      ↓
Synthetic Purchase Order
      ↓
Synthetic Invoice
      ↓
Synthetic Payment
      ↓
Synthetic Approval
```

IDs and relationships must be deterministic and reproducible.

Do NOT simply ask an LLM to randomly generate thousands of unrelated records.

Use Python/Faker/seeded generators and explicit business rules.

---

# 12. SYNTHETIC DOCUMENTS

Generate realistic but clearly synthetic:

- Contract documents
- Procurement policies
- Approval policies
- Payment policies
- Vendor policies
- Invoice PDFs
- Purchase order documents
- Internal email threads
- Operational notes

The documents must be generated from the structured records where appropriate so that the information is internally consistent.

For example:

```text
Contract database:
maximum_value = €100,000

Contract PDF:
"The total value of this agreement shall not exceed €100,000."
```

Avoid contradictions unless the contradiction is intentionally injected as a benchmark case.

---

# 13. INTENTIONAL ANOMALIES

Create a controlled percentage of problematic records.

Examples:

```text
invoice > PO
invoice > contract limit
duplicate invoice
missing approval
expired contract
wrong vendor
already-paid invoice
invalid PO
wrong currency
payment mismatch
```

Every injected anomaly must have known ground truth.

This enables reproducible evaluation.

---

# 14. GROUND TRUTH DATASET

Create an evaluation dataset containing questions and expected outcomes.

For example:

```json
{
  "question": "Why is INV-1042 overdue?",
  "expected_sources": [
    "invoice:INV-1042",
    "payment:PAY-991"
  ],
  "expected_facts": [
    "invoice is unpaid",
    "due date has passed"
  ]
}
```

Also create benchmark cases for:

- retrieval
- SQL reasoning
- compliance
- anomaly detection
- tool selection
- workflow routing
- final answer quality
- human approval routing

The benchmark must be reproducible.

---

# 15. SYSTEM ARCHITECTURE

Design a production-oriented architecture.

A conceptual architecture could look like:

```text
                    ┌───────────────────┐
                    │      Client       │
                    │ Web UI / API      │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │     FastAPI       │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ LangGraph         │
                    │ Orchestrator      │
                    └─────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    Retrieval Agent      SQL/Data Agent      Analysis Agent
          │                   │                   │
          ▼                   ▼                   ▼
     Vector DB            PostgreSQL        Python tools
          │
          ▼
   Hybrid Retrieval
   BM25 + Dense
          │
          ▼
      Reranker
          │
          ▼
      LLM Context

                              │
                              ▼
                     Policy / Risk Engine
                              │
                       ┌──────┴──────┐
                       ▼             ▼
                    Answer         Action
                                     │
                                     ▼
                              Approval Workflow
                                     │
                              Human-in-the-loop
                                     │
                                     ▼
                              External Tool/MCP
```

This is only a starting point. Do not blindly copy it. Improve it based on actual requirements.

---

# 16. LANGGRAPH DESIGN

Use LangGraph meaningfully.

Consider a main orchestration graph:

```text
START
 ↓
Input validation / guardrails
 ↓
Intent classification / routing
 ↓
 ├── Retrieval workflow
 ├── SQL workflow
 ├── Analytics workflow
 ├── Investigation workflow
 └── Action workflow
 ↓
Evidence aggregation
 ↓
Response validation
 ↓
END
```

For long-running actions, consider a dedicated workflow/subgraph:

```text
Action request
 ↓
Validation
 ↓
Policy check
 ↓
Risk assessment
 ↓
Human interrupt
 ↓
Approve / Reject
 ↓
Execute
 ↓
Audit
```

Use persistent checkpointing.

Design the state carefully.

Do not create unnecessary agents just for the sake of calling something "multi-agent".

Prefer deterministic nodes where deterministic logic is sufficient.

---

# 17. RETRIEVAL ARCHITECTURE

Do not build a trivial:

```text
embedding → vector search → LLM
```

pipeline.

Implement a serious retrieval pipeline.

Potential architecture:

```text
Query
 ↓
Query preprocessing
 ↓
 ┌───────────────┬───────────────┐
 ▼               ▼
BM25          Dense retrieval
                  │
                  ▼
              HNSW/vector DB
 └───────────────┬───────────────┘
                 ▼
             Hybrid fusion
                 ▼
            Reranking
                 ▼
          Context selection
                 ▼
                LLM
```

Evaluate:

- BM25
- dense retrieval
- hybrid retrieval
- reranking

Potential metrics:

- Recall@K
- Precision@K
- MRR
- NDCG
- context precision
- context recall
- faithfulness
- answer relevancy

Do not add every possible technique automatically. Select methods based on actual experiments.

---

# 18. DATABASE ARCHITECTURE

Use a relational database for structured operational data.

Potential entities:

```text
vendors
buyers
departments
contracts
purchase_orders
purchase_order_items
invoices
invoice_items
payments
approval_requests
users
procurement_events
exceptions
audit_logs
```

Define:

- primary keys
- foreign keys
- indexes
- constraints
- status fields
- timestamps
- relationships

Design the schema before implementation.

---

# 19. VECTOR DATABASE

Use a vector store for unstructured documents.

Possible choices:

- ChromaDB
- Qdrant
- pgvector

Choose one and explain why.

Store metadata such as:

```text
document_id
document_type
vendor_id
contract_id
department
effective_date
expiration_date
source
page
section
```

Metadata filtering should be supported.

---

# 20. TOOL ARCHITECTURE

Potential tools:

```text
search_documents()
search_contracts()
get_invoice()
get_purchase_order()
get_payment_status()
query_procurement_database()
run_business_analysis()
detect_anomalies()
check_policy()
create_approval_request()
get_approval_status()
execute_controlled_action()
```

Design clear tool contracts.

Tool descriptions must be precise enough for an LLM to select them correctly.

Dangerous tools should require additional authorization.

---

# 21. MCP

Use MCP only where it provides a meaningful architectural boundary.

For example, expose an external operational service through MCP:

```text
LangGraph
     ↓
MCP client
     ↓
MCP server
     ↓
Mock payment/procurement service
```

Potential operations:

```text
create_payment_request()
get_payment_status()
create_exception()
update_workflow_status()
```

Do not use MCP just as a resume keyword.

Explain why it exists.

---

# 22. GUARDRAILS / SECURITY

Consider:

### Input

- Prompt injection detection
- PII detection
- malicious input
- unsupported requests
- authorization checks

### Tool layer

- tool authorization
- role-based access
- high-risk action confirmation
- idempotency
- input validation

### Output

- hallucination checks
- evidence requirement
- PII redaction
- unsupported-claim detection

The system must never fabricate database records or policy statements.

---

# 23. OBSERVABILITY

Design observability into the architecture.

Track:

- request ID
- user/session ID
- graph execution
- node latency
- LLM latency
- retrieval latency
- SQL latency
- tool calls
- token usage
- errors
- retries
- approval events
- final outcome

Potential stack:

- structured logging
- OpenTelemetry
- Prometheus
- Grafana
- LangSmith or another tracing system if appropriate

Keep the architecture practical for a portfolio project.

---

# 24. EVALUATION

Evaluation should be a first-class component.

Separate:

### Retrieval evaluation

```text
Recall@K
MRR
NDCG
```

### RAG evaluation

```text
Faithfulness
Context recall
Context precision
Answer relevancy
```

### Agent evaluation

```text
tool selection accuracy
routing accuracy
workflow completion
```

### Business evaluation

```text
anomaly detection precision/recall
policy violation detection
false positive rate
```

### System evaluation

```text
latency
throughput
failure rate
```

Do not manufacture impressive metrics.

All reported metrics must come from reproducible experiments.

---

# 25. TESTING

Create:

- unit tests
- integration tests
- retrieval tests
- tool tests
- graph/workflow tests
- database tests
- API tests
- end-to-end tests
- evaluation tests

Test failure paths, not only happy paths.

Examples:

- missing invoice
- invalid PO
- database timeout
- vector DB failure
- LLM timeout
- tool failure
- duplicate action
- approval rejection
- resumed interrupted graph
- unauthorized action

---

# 26. DOCKER / INFRASTRUCTURE

Design a local reproducible environment.

Potential services:

```text
api
postgres
vector_db
mcp_server
frontend
```

Do not over-containerize unnecessarily.

The project should be runnable with:

```bash
docker compose up
```

or an equally simple documented command.

Use environment variables for secrets.

Never commit API keys.

---

# 27. CI/CD

Design GitHub Actions for:

```text
lint
format
type check
unit tests
integration tests
evaluation smoke tests
Docker build
```

Potential tools:

- Ruff
- mypy/pyright
- pytest
- coverage
- Docker

Keep CI reasonably fast.

---

# 28. REPOSITORY STRUCTURE

Design a clean professional repository.

I expect something conceptually similar to:

```text
agentic-procurement-platform/
│
├── .github/
│   └── workflows/
│
├── configs/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── synthetic/
│   └── evaluation/
│
├── docs/
│   ├── architecture/
│   ├── data/
│   ├── evaluation/
│   └── decisions/
│
├── frontend/
│
├── scripts/
│   ├── download_public_data.py
│   ├── generate_synthetic_data.py
│   ├── generate_documents.py
│   ├── inject_anomalies.py
│   └── build_evaluation_set.py
│
├── src/
│   └── procurement_ai/
│       ├── api/
│       ├── agents/
│       ├── graph/
│       ├── retrieval/
│       ├── database/
│       ├── tools/
│       ├── mcp/
│       ├── documents/
│       ├── guardrails/
│       ├── anomaly_detection/
│       ├── evaluation/
│       ├── observability/
│       ├── models/
│       ├── config/
│       └── utils/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── evaluation/
│   └── e2e/
│
├── docker/
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── .env.example
```

However, **do not assume this structure is optimal**.

Analyze the architecture and propose a better structure if necessary.

---

# 29. IMPORTANT DESIGN PRINCIPLES

Follow these principles:

1. Do not build a generic chatbot.
2. Do not create unnecessary agents.
3. Use deterministic code whenever deterministic logic is appropriate.
4. Use LLMs where language reasoning actually provides value.
5. Keep business rules explicit.
6. Separate retrieval, reasoning, decision, and execution.
7. Separate read-only tools from write/action tools.
8. Require human approval for high-risk actions.
9. Preserve evidence and provenance.
10. Make all synthetic data reproducible.
11. Maintain referential integrity.
12. Do not fabricate evaluation metrics.
13. Do not expose real private data.
14. Make the entire project reproducible locally.
15. Optimize for engineering quality rather than number of technologies.

---

# 30. TECH STACK

Start with this stack unless you have a strong technical reason to change something:

### Language
Python 3.12+

### API
FastAPI

### Agent orchestration
LangGraph

### LLM
Provider-agnostic abstraction supporting:
- OpenAI/Azure OpenAI
- local model through Ollama if practical

### Embeddings
Provider-agnostic abstraction.

### Structured database
PostgreSQL

### Vector database
Choose between:
- pgvector
- Qdrant
- ChromaDB

Explain the decision.

### Retrieval
- BM25
- dense embeddings
- hybrid fusion
- optional cross-encoder reranking

### Documents
PDF/document parsing using appropriate open-source tools.

### Synthetic data
Python + Faker + seeded deterministic generators.

### ML
scikit-learn for anomaly detection where appropriate.

### MCP
FastMCP or another suitable implementation.

### Testing
pytest

### Packaging
uv

### Containers
Docker + Docker Compose

### CI
GitHub Actions

### Observability
Choose a practical stack.

Do not introduce technologies simply because they are popular.

---

# 31. WHAT I WANT FROM YOU NOW

Do NOT start writing implementation code yet.

First act as a senior software architect and produce a complete design document.

Your response should contain:

## A. Product definition
- What the product is
- What it is not
- Who uses it
- Why they use it
- Main business value
- Main use cases

## B. Complete system architecture
Give me a detailed architecture diagram in Mermaid.

## C. Data architecture
Explain:

- Public datasets
- Synthetic datasets
- Database schema
- Documents
- Vector store
- Ground truth
- Relationships
- Data generation pipeline

## D. Agent architecture
Explain:

- Main LangGraph
- Subgraphs
- State
- Nodes
- Routers
- Tools
- Interrupts
- Persistence
- Error handling

Include a Mermaid graph.

## E. Retrieval architecture
Explain:

- ingestion
- parsing
- chunking
- metadata
- BM25
- dense retrieval
- hybrid fusion
- reranking
- context construction
- evaluation

## F. Action/approval architecture
Explain the full lifecycle:

```text
request
→ validation
→ policy
→ risk
→ approval
→ execution
→ audit
```

## G. Database schema
Provide an ER diagram in Mermaid.

## H. Repository/file structure
Give the final recommended directory tree.

For every important directory/file, explain:

- responsibility
- why it exists
- what belongs there
- what does NOT belong there

## I. API design
Define important endpoints and request/response responsibilities.

## J. Tool design
Define every important tool and its input/output contract.

## K. MCP architecture
Explain exactly where MCP belongs and why.

## L. Security/guardrails
Explain input, tool, authorization and output protections.

## M. Evaluation framework
Define datasets, benchmark cases, metrics and evaluation scripts.

## N. Testing strategy
Define unit/integration/e2e/evaluation tests.

## O. Docker architecture
Define services, networks, volumes and dependencies.

## P. CI/CD
Define the GitHub Actions pipeline.

## Q. Observability
Define logs, metrics, tracing and important dashboards.

## R. Development roadmap
Break implementation into phases.

For each phase specify:

- objective
- files created/modified
- dependencies
- expected result
- tests

Do not make the roadmap unrealistically large.

## S. Portfolio presentation
Finally explain how this project should be presented on GitHub:

- project title
- one-line description
- README structure
- architecture diagram
- screenshots/demo
- evaluation results
- technical highlights
- limitations
- future improvements

---

# 32. VERY IMPORTANT

I want you to think about this as a **real software/AI system**, not as a tutorial.

Do not optimize for:

> "How many AI technologies can we put into the project?"

Optimize for:

> "What is the simplest architecture that convincingly solves the business problem while demonstrating strong AI/ML engineering?"

If a component is unnecessary, say so.

If two components overlap, recommend removing one.

If a proposed technology is only there for CV keyword value, explicitly flag it.

Also identify architectural risks, likely bottlenecks, failure modes, and places where an LLM could hallucinate or make an unsafe decision.

Before proposing the final architecture, reason through the complete end-to-end lifecycle of at least these scenarios:

1. User asks why an invoice is overdue.
2. User asks whether an invoice complies with its PO and contract.
3. User asks to find potential procurement policy violations.
4. User asks to find duplicate invoices.
5. User asks to request payment for an invoice.
6. Human approves the payment.
7. Human rejects the payment.
8. A tool/database fails during the workflow.
9. The graph is interrupted and resumed later.
10. The user asks an unrelated question outside the procurement domain.

The final architecture should support these scenarios cleanly without introducing unnecessary complexity.

Do not write application code yet. I want the architecture and repository design first.