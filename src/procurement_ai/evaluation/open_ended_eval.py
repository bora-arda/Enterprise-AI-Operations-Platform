"""Metrics for open-ended agent evaluation.

These metrics are intentionally simple and auditable. They do not claim to
measure semantic correctness of free-text answers; they measure routing, tool
execution, required-fact coverage, and SQL-guard behavior.
"""

from procurement_ai.evaluation.agent_eval import tool_selection_accuracy


def answer_coverage(required_terms: list[str], answer: str) -> float:
    """Fraction of required terms present in the answer (case-insensitive)."""
    if not required_terms:
        return 1.0
    lowered = (answer or "").lower()
    hits = sum(1 for term in required_terms if term.lower() in lowered)
    return hits / len(required_terms)


def tool_success_rate(tool_traces: list[dict]) -> float:
    """Fraction of agent tool calls that completed without an error."""
    if not tool_traces:
        return 1.0
    successes = sum(1 for trace in tool_traces if trace.get("success"))
    return successes / len(tool_traces)


def sql_guard_block_rate(sql_statements: list[str]) -> float:
    """Fraction of adversarial statements rejected by the SQL guard."""
    from procurement_ai.database.sql_guard import validate_sql

    if not sql_statements:
        return 1.0
    blocked = sum(1 for sql in sql_statements if not validate_sql(sql)[0])
    return blocked / len(sql_statements)


def evaluate_open_ended(benchmark: list[dict], results: dict[str, dict]) -> dict:
    """Aggregate routing, tool selection, coverage, and tool success."""
    routing_scores = []
    tool_scores = []
    coverage_scores = []
    success_scores = []
    steps = []

    for item in benchmark:
        result = results.get(item["id"], {})
        expected_workflow = item.get("expected_workflow")
        actual_workflow = result.get("workflow")
        if expected_workflow:
            routing_scores.append(1.0 if expected_workflow == actual_workflow else 0.0)

        expected_tools = item.get("expected_tools", [])
        actual_tools = result.get("tools_used", [])
        if expected_tools:
            tool_scores.append(tool_selection_accuracy(expected_tools, actual_tools))

        coverage_scores.append(answer_coverage(item.get("required_terms", []), result.get("answer", "")))

        traces = result.get("tool_traces", [])
        if traces:
            success_scores.append(tool_success_rate(traces))
        if result.get("steps") is not None:
            steps.append(result["steps"])

    def mean(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return {
        "routing_accuracy": mean(routing_scores),
        "tool_selection_accuracy": mean(tool_scores),
        "answer_term_coverage": mean(coverage_scores),
        "tool_success_rate": mean(success_scores),
        "average_agent_steps": mean(steps),
        "total_tasks": len(benchmark),
    }
