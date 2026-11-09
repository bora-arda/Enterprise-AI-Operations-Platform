# Open-Ended Agent Evaluation

**Run date:** 2026-11-09

**Environment:** local host process (not the Docker image), agent-first
orchestration, PostgreSQL with the loaded synthetic dataset, Claude Haiku 5.5
via OpenCode Go.

**Benchmark:** [`data/evaluation/open_ended_benchmark.json`](../../data/evaluation/open_ended_benchmark.json) (5 curated tasks)

**Raw results:** [`open_ended_results.json`](open_ended_results.json)

## Results

| Metric | Result | Notes |
|---|---:|---|
| Routing accuracy | 1.00 (5/5) | Planner sent all five open-ended tasks to the agent |
| Tool selection accuracy | 1.00 (5/5) | Expected primary tool appeared in the run |
| Answer term coverage | 1.00 (5/5) | Required terms present; **not** a semantic-correctness score |
| Tool success rate | 1.00 | Tool calls that returned without an error |
| Average agent steps | 3.6 | Tool-calling rounds (maximum 6) |
| Adversarial SQL block rate | 1.00 (7/7) | `DELETE`, `DROP`, multi-statement, `pg_sleep`, `password_hash`, planner table, `SELECT INTO` |

## Tasks

1. `What changed in spending from 2024 to 2025?`
2. `Which vendors have the most overdue invoices?`
3. `Find invoices that exceed their contract maximum and show the contract title.`
4. `Show me payments above 1,000,000 with invoice numbers and vendors.`
5. `Which exception types are most common, and how many of each are there?`

## Reproduce

```bash
uv run python scripts/evaluate_open_ended.py \
  --output docs/evaluation/open_ended_results.json
```

## Limitations

- This is a small five-task sample, not a statistically meaningful benchmark.
- “Answer term coverage” only checks required terms; it does not measure
  numerical result equivalence, reasoning quality, or faithfulness.
- LLM output and tool selection are non-deterministic; reruns may differ.
- The adversarial SQL checks are unit-style guard checks, not an adversarial
  LLM red-team campaign.
- The metrics complement, and do not replace, the deterministic SQL-guard,
  routing, and integration tests.
