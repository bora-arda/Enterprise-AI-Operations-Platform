# ADR 003: Use MCP as the boundary to external ERP

## Status

Accepted

## Context

The agent needs to execute actions (payments, exceptions) in an external system. We need a clean architectural boundary for this integration.

Options considered:

- **Direct API calls** — agent calls REST API directly
- **MCP server** — agent speaks MCP, server translates to ERP protocol
- **Tool wrapper** — wrap ERP calls as LangChain tools

## Decision

Use **MCP (Model Context Protocol)** as the boundary to the mock ERP service.

## Rationale

1. **Simulates real integration** — in production, this would be SAP/Oracle
2. **Protocol boundary** — agent speaks MCP, ERP speaks its own protocol
3. **Testability** — mock ERP can be replaced with real one without changing agent code
4. **Tool discovery** — MCP provides standard tool discovery and schema
5. **Not just a keyword** — MCP provides genuine architectural value here

## Consequences

- Positive: clean separation between agent and external systems
- Positive: swappable mock/real ERP implementations
- Negative: additional service to run and maintain
- Negative: MCP is still evolving as a standard
