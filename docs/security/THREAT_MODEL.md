# Security Review

**Scope:** the agent-first procurement platform as currently implemented in this
repository, including the FastAPI chat path, LangGraph orchestration, tool
executor, read-only SQL guard, retrieval, MCP mock ERP, approvals, Prometheus,
Grafana, and local/Docker deployment.

**Status:** this is a design and implementation review, not an external
penetration test or a certification. Several controls are strong for a pilot;
the residual risks below must be closed before handling real financial data or
multi-tenant production traffic.

## Trust boundaries

```text
Browser / API client
        │  JWT + RBAC
        ▼
FastAPI chat endpoint
        │
        ├── input guardrails
        ├── agent / planner / deterministic action router
        │        │
        │        ├── LLM provider (OpenCode Go)
        │        ├── read-only PostgreSQL tools
        │        ├── retrieval documents
        │        └── human-approved action workflow
        │
        ├── MCP mock ERP
        ├── Prometheus / Grafana
        └── PostgreSQL + pgvector
```

Untrusted inputs include user messages, retrieved documents, emails, operational
notes, SQL results, vendor names/descriptions, MCP responses, and any future
external ERP payloads.

## 1. Prompt injection

**Threat:** a document, email, incident note, vendor name, or tool result tells
the model to ignore policy, reveal secrets, call a tool, or approve a payment.

**Implemented controls**

- Input guardrails detect common instruction-injection patterns.
- Tool results are recursively sanitized and wrapped in an explicit
  `<tool_output trust="untrusted">` envelope.
- The agent system prompt states that tool output is data and must never be
  followed as instructions.
- The agent has no write/action tools; it cannot execute a payment or approval.
- SQL results are value/row capped and sensitive columns are filtered.
- Output guardrails and answer verification run after generation.

**Residual risks**

- The sanitizer is pattern-based; a novel injection can still reach the model.
- A malicious document can still cause a wrong narrative answer without
  executing an action.
- The current guardrails are not a substitute for a red-team evaluation.

**Next steps**

- Add a prompt-injection corpus to CI with documents that contain tool-call
  instructions, fake system messages, encoded payloads, and multilingual
  attacks.
- Treat every tool result as untrusted at the model boundary, including future
  ERP and email integrations.
- Consider an isolated “draft only” model step that cannot call tools, followed
  by a verifier that has no write capability.

## 2. Tool misuse

**Threat:** the model invokes unintended tools, passes unsafe SQL, calls tools
too many times, or uses a tool outside the user’s authority.

**Implemented controls**

- Explicit tool registry; no dynamic tool loading.
- Read-only tool set; action tools are not exposed to the agent.
- Maximum six tool rounds and bounded tool output.
- SQL validator: one `SELECT`/`WITH`, denied keywords/functions/tables/columns,
  row cap, statement timeout, read-only transaction.
- Tool errors are returned to the model for correction instead of crashing.
- Every tool call is included in the agent trace and Prometheus metrics.
- Restricted users cannot use arbitrary SQL.

**Residual risks**

- Regex-based SQL validation is not equivalent to an AST parser or database
  row-level security.
- The agent can still call read-only tools repeatedly within the budget.
- The model can choose a valid but inappropriate tool for a question.

**Next steps**

- Parse SQL with a real AST parser and enforce a table/column allow-list.
- Use a dedicated SELECT-only database role with RLS in production.
- Add per-tool authorization checks based on user role and resource ownership.
- Add tool-call rate limits and per-request budgets.

## 3. Data exfiltration

**Threat:** a user or injected content causes the model to reveal data from
other departments, sensitive columns, secrets, or unrelated tenants.

**Implemented controls**

- SQL blocks sensitive columns (`password_hash`, `embedding`, `bank_details`)
  and sensitive tables (planner decisions, checkpoints).
- Results are capped and sensitive columns are removed even from `SELECT *`.
- The agent cannot access environment variables or arbitrary files.
- `.env` is gitignored; no API keys are committed.
- Restricted users get department-scoped metric, exception, document, and
  entity access; arbitrary SQL is denied.
- Tool output is sanitized and bounded before re-entering the model.

**Residual risks**

- Application-level scope is not the same as database-enforced row-level
  security.
- Global roles (manager/finance/director/admin) can read across departments by
  design.
- Hybrid-mode legacy workflows are not the primary scoped path; production
  should either disable hybrid mode for restricted users or retrofit scope into
  every workflow.
- Documents with no department are treated as global policy material; this
  policy needs review for confidential documents.

**Next steps**

- Implement PostgreSQL RLS with a dedicated read-only role and
  `app.user_id/app.department_id` session variables.
- Add tenant/department scoping to the vector search query itself, not only
  after retrieval.
- Add response DLP checks for secrets, credentials, and unexpected record
  volume.
- Add audit alerts for unusually large result sets or repeated access denials.

## 4. Privilege escalation

**Threat:** a low-privilege user obtains manager/finance capabilities, approves
their own request, or uses the agent to trigger a payment.

**Implemented controls**

- JWT authentication and role-based endpoint dependencies.
- Approval decisions are limited to manager/finance/director/admin.
- Self-approval is forbidden.
- Agent tools are read-only; actions go through the checkpointed human-in-the-
  loop action graph.
- Duplicate-payment and already-paid checks run before execution.
- Restricted users cannot submit an action against an invoice outside their
  department.
- Planner and action decisions are audited.

**Residual risks**

- Role assignment and JWT signing-key management remain deployment
  responsibilities.
- The action workflow’s department check is application-level, not database-
  enforced.
- Legacy approvals created before checkpointing use the direct execution
  fallback; that path needs the same authorization review.

**Next steps**

- Add integration tests for cross-department action attempts.
- Externalize signing keys and rotate them.
- Add organization/tenant claims to tokens and enforce them end-to-end.
- Require re-authentication for high-value approvals.

## 5. Secrets and deployment

- API keys are read from `.env` and are not committed.
- Do not expose `/metrics`, Grafana, or MCP publicly without authentication.
- Grafana admin credentials must be changed from the demo default.
- MCP streamable HTTP currently has no authentication layer; put it behind
  network policy or an authenticated gateway.
- Prometheus and Grafana local test installs use temporary files under
  `/tmp/opencode`; production needs persistent storage and access controls.

## 6. Recommended security test suite

1. Prompt-injection documents and tool outputs.
2. SQL guard bypass attempts using comments, case changes, unicode, nested
   CTEs, and function aliases.
3. Sensitive-column access through `SELECT *` and views.
4. Cross-department entity lookup, metric, exception, and action attempts.
5. Role escalation and self-approval attempts.
6. Oversized result sets, timeouts, and repeated tool calls.
7. SSE/HTTP/MCP authentication and rate limits.
8. Log redaction and secret scanning in CI.

## Current verdict

The design has good **least-privilege intent**: read-only agent tools, guarded
SQL, human approval for actions, and a restricted-user access scope. It is not
yet a security certification. The most important remaining control is
**database-enforced row-level security plus authenticated MCP/network
boundaries**, followed by a real prompt-injection and SQL-bypass test corpus.
