"""SQL subgraph for natural language to SQL pipeline."""

import logging

from langgraph.graph import END, START, StateGraph

logger = logging.getLogger(__name__)


def create_sql_subgraph():
    """Create the SQL subgraph."""
    graph = StateGraph(dict)

    graph.add_node("sql_generate", sql_generate_node)
    graph.add_node("sql_validate", sql_validate_node)
    graph.add_node("sql_execute", sql_execute_node)
    graph.add_node("format_results", format_results_node)

    graph.add_edge(START, "sql_generate")
    graph.add_edge("sql_generate", "sql_validate")
    graph.add_conditional_edges(
        "sql_validate",
        lambda state: "valid" if state.get("sql_valid") else "invalid",
        {
            "valid": "sql_execute",
            "invalid": "sql_generate",  # Retry
        },
    )
    graph.add_edge("sql_execute", "format_results")
    graph.add_edge("format_results", END)

    return graph.compile()


def sql_generate_node(state: dict) -> dict:
    """Generate SQL from natural language."""
    # TODO: Implement LLM-based SQL generation
    state["sql_query"] = ""
    state["sql_valid"] = False
    return state


def sql_validate_node(state: dict) -> dict:
    """Validate the generated SQL."""
    # TODO: Implement SQL validation (read-only check, syntax check)
    state["sql_valid"] = True
    return state


def sql_execute_node(state: dict) -> dict:
    """Execute the SQL query."""
    # TODO: Implement read-only SQL execution
    state["sql_results"] = []
    return state


def format_results_node(state: dict) -> dict:
    """Format SQL results for the user."""
    # TODO: Implement result formatting
    state["formatted_results"] = ""
    return state
