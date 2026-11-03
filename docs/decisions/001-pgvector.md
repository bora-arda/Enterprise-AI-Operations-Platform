# ADR 001: Use pgvector as the vector database

## Status

Accepted

## Context

We need a vector database for document retrieval. Options considered:

- **pgvector** — PostgreSQL extension
- **Qdrant** — dedicated vector DB
- **ChromaDB** — lightweight vector DB

## Decision

Use **pgvector** as the vector store.

## Rationale

1. **One less service** — no separate vector DB to run, backup, or monitor
2. **SQL-filterable metadata** — filter by vendor_id, date_range, document_type in the same query
3. **ACID compliance** — vector writes are transactional with relational data
4. **Sufficient scale** — portfolio project with thousands of documents, not millions
5. **Simpler operations** — single backup, single migration path

## Consequences

- Positive: simpler Docker Compose, fewer moving parts, transactional consistency
- Negative: not as scalable as dedicated vector DBs (acceptable for this project)
- Negative: vector search performance slightly lower than specialized solutions (acceptable)
