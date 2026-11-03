# ADR 002: Use LangGraph for agent orchestration

## Status

Accepted

## Context

We need an agent orchestration framework that supports:

- Stateful multi-step workflows
- Human-in-the-loop interrupts
- Persistent checkpointing
- Conditional routing

Options considered:

- **LangGraph** — graph-based agent framework
- **LangChain Agents** — legacy agent executor
- **AutoGen** — multi-agent conversation framework
- **CrewAI** — role-based agent framework

## Decision

Use **LangGraph** for orchestration.

## Rationale

1. **First-class interrupts** — `interrupt()` is built-in, not hacked together
2. **PostgreSQL checkpointing** — persistent state out of the box
3. **Deterministic + LLM nodes** — mix deterministic code with LLM calls
4. **Conditional edges** — clean routing based on state
5. **LangSmith integration** — LLM-specific observability

## Consequences

- Positive: clean separation of deterministic and LLM logic
- Positive: approval workflows are trivial to implement
- Negative: learning curve for graph-based thinking
- Negative: newer framework with evolving API
