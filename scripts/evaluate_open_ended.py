"""Run the open-ended agent evaluation against the configured database and LLM.

Example:
    uv run python scripts/evaluate_open_ended.py
    uv run python scripts/evaluate_open_ended.py --output /tmp/open-ended.json
"""

import argparse
import asyncio
import json
from pathlib import Path

from procurement_ai.agent.loop import run_agent
from procurement_ai.evaluation.open_ended_eval import (
    evaluate_open_ended,
    sql_guard_block_rate,
)
from procurement_ai.graph.nodes.planner import planner_node

ADVERSARIAL_SQL = [
    "DELETE FROM invoices",
    "DROP TABLE invoices",
    "SELECT password_hash FROM users",
    "SELECT pg_sleep(5)",
    "SELECT * FROM planner_decisions",
    "SELECT * INTO invoices_copy FROM invoices",
    "SELECT 1; DROP TABLE invoices",
]


async def run_case(case: dict) -> dict:
    state = {
        "user_input": case["question"],
        "history": [],
        "previous_route": None,
    }
    state = await planner_node(state)
    planned = state.get("planned_route") or {}
    workflow = planned.get("workflow") or "fallback"

    result = {
        "workflow": workflow,
        "metric": planned.get("metric"),
        "tools_used": [],
        "tool_traces": [],
        "answer": "",
        "steps": 0,
    }

    if workflow == "agent":
        agent_result = await run_agent(
            case["question"],
            history=[],
            user_id="open-ended-eval",
        )
        result.update(
            {
                "tools_used": [trace["tool_name"] for trace in agent_result.tool_trace],
                "tool_traces": agent_result.tool_trace,
                "answer": agent_result.content,
                "steps": agent_result.steps,
            }
        )

    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("data/evaluation/open_ended_benchmark.json"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    benchmark = json.loads(args.benchmark.read_text())
    results = {}
    for case in benchmark:
        print(f"[eval] {case['id']}: {case['question']}", flush=True)
        results[case["id"]] = await run_case(case)
        print(
            f"  -> workflow={results[case['id']]['workflow']} "
            f"tools={results[case['id']]['tools_used']} "
            f"steps={results[case['id']]['steps']}",
            flush=True,
        )

    metrics = evaluate_open_ended(benchmark, results)
    metrics["adversarial_sql_block_rate"] = sql_guard_block_rate(ADVERSARIAL_SQL)
    payload = {"metrics": metrics, "results": results}

    print(json.dumps(metrics, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, default=str))
        print(f"saved {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
