"""Agent evaluation metrics."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def tool_selection_accuracy(expected_tools: list[str], actual_tools: list[str]) -> float:
    """Compute tool selection accuracy."""
    if not expected_tools:
        return 1.0
    expected_set = set(expected_tools)
    actual_set = set(actual_tools)
    return len(expected_set & actual_set) / len(expected_set)


def routing_accuracy(expected_workflow: str, actual_workflow: str) -> float:
    """Compute routing accuracy."""
    return 1.0 if expected_workflow == actual_workflow else 0.0


def workflow_completion(expected_steps: int, actual_steps: int) -> float:
    """Compute workflow completion ratio."""
    if expected_steps == 0:
        return 1.0
    return min(actual_steps / expected_steps, 1.0)


def step_efficiency(expected_steps: int, actual_steps: int) -> float:
    """Compute step efficiency (1.0 = perfect, >1 = more steps than needed)."""
    if expected_steps == 0:
        return 1.0
    return actual_steps / expected_steps


def evaluate_agent(
    benchmark: list[dict],
    results: dict[str, dict[str, Any]],
) -> dict[str, float]:
    """Evaluate agent performance against a benchmark."""
    tool_scores = []
    routing_scores = []
    completion_scores = []

    for item in benchmark:
        query_id = item.get("invoice_id")
        expected_tools = item.get("expected_tools", [])
        expected_workflow = item.get("expected_workflow", "")

        result = results.get(query_id or "", {})
        actual_tools = result.get("tools_used", [])
        actual_workflow = result.get("workflow", "")

        if expected_tools:
            tool_scores.append(tool_selection_accuracy(expected_tools, actual_tools))
        if expected_workflow:
            routing_scores.append(routing_accuracy(expected_workflow, actual_workflow))
        if expected_tools:
            completion_scores.append(workflow_completion(len(expected_tools), len(actual_tools)))

    n = len(benchmark)
    return {
        "tool_selection_accuracy": sum(tool_scores) / len(tool_scores) if tool_scores else 0.0,
        "routing_accuracy": sum(routing_scores) / len(routing_scores) if routing_scores else 0.0,
        "workflow_completion_rate": sum(completion_scores) / len(completion_scores) if completion_scores else 0.0,
        "total_tasks": n,
    }
