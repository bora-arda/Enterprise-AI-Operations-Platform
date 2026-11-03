"""SQL/analytics workflow node.

Maps natural-language analytics questions to parameterized, read-only SQL
queries. Deterministic template selection - no free-form SQL generation,
so there is no SQL-injection surface.
"""

import logging
import re

from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.semantic.metrics import MetricRequest, compute_metric
from procurement_ai.semantic.parser import format_metric_result, parse_metric_request
from procurement_ai.tools.query_tools import query_procurement_db

logger = logging.getLogger(__name__)

# Ordered pattern -> query template mapping
QUERY_RULES: list[tuple[str, str]] = [
    (r"\boverdue\b", "overdue_invoices"),
    (r"\b(by|per)\s+month\b|\bmonthly\b|\bspending\s+trend", "monthly_spending"),
    (r"\b(by|per)\s+category\b|\bcategor", "spending_by_category"),
    (r"\btop\s+vendors?\b|\bhighest\s+average\b|\baverage\s+invoice", "top_vendors"),
    (r"\bexceptions?\b.*\bvendors?\b|\bvendors?\b.*\bexceptions?\b", "vendor_exceptions"),
    (r"\bspend", "spending_by_category"),
    (r"\boverdue\b|\bunpaid\b", "overdue_invoices"),
]


def _select_template(question: str) -> str | None:
    q = question.lower()
    for pattern, template in QUERY_RULES:
        if re.search(pattern, q):
            return template
    return None


def _format_rows(template: str, rows: list[dict]) -> str:
    if not rows:
        return "The query returned no results."

    lines = [f"Results ({len(rows)} rows):"]
    for row in rows[:10]:
        parts = [f"{k}={v}" for k, v in row.items() if v is not None]
        lines.append("- " + ", ".join(parts))
    if len(rows) > 10:
        lines.append(f"... and {len(rows) - 10} more rows.")
    return "\n".join(lines)


async def sql_workflow_node(state: dict) -> dict:
    """Answer analytics questions via the semantic layer or SQL templates."""
    question = state.get("user_input", "")

    # Governed metric first: explicit definitions, allow-listed dimensions.
    planned = state.get("planned_route") or {}
    metric_request = None
    if planned.get("metric"):
        metric_request = MetricRequest(
            metric=planned["metric"],
            dimension=planned.get("dimension"),
            days=planned.get("days"),
            limit=10,
        )
    else:
        metric_request = parse_metric_request(question)

    if metric_request:
        try:
            async with AsyncSessionLocal() as session:
                result = await compute_metric(session, metric_request)
        except Exception as e:
            logger.error(f"Semantic metric failed: {e}", exc_info=True)
            state["response"] = "I encountered a database error while computing that metric."
            state["errors"] = state.get("errors", []) + [str(e)]
            return state

        state["response"] = format_metric_result(result)
        state["citations"] = [
            {
                "source": f"metric:{metric_request.metric}",
                "snippet": (f"{len(result.rows)} group(s); dimension={metric_request.dimension or 'total'}"),
            }
        ]
        state["evidence"] = [
            {
                "source": f"metric:{metric_request.metric}",
                "content": result.sql,
                "metadata": result.params,
            }
        ]
        state["confidence"] = 0.9
        state["workflow"] = "sql"
        state["tool_results"] = state.get("tool_results", []) + [
            {
                "tool_name": f"metric:{metric_request.metric}",
                "success": True,
                "result": {"rows": len(result.rows)},
                "error": None,
            }
        ]
        return state

    template = _select_template(question)

    if not template:
        state["response"] = (
            "I can answer analytics questions about overdue invoices, spending by "
            "category, monthly spending, top vendors, and vendor exceptions. "
            "Could you rephrase your question along those lines?"
        )
        state["confidence"] = 0.3
        return state

    try:
        async with AsyncSessionLocal() as session:
            rows = await query_procurement_db(session, template, {"limit": 20})
    except Exception as e:
        logger.error(f"SQL workflow failed: {e}", exc_info=True)
        state["response"] = "I encountered a database error while running that analysis."
        state["errors"] = state.get("errors", []) + [str(e)]
        return state

    response = f"Analysis: {template.replace('_', ' ')}\n\n{_format_rows(template, rows)}"

    state["response"] = response
    state["citations"] = [{"source": f"sql:{template}", "snippet": f"{len(rows)} rows returned"}]
    state["evidence"] = [{"source": f"sql:{template}", "content": str(rows[:5]), "metadata": {}}]
    state["confidence"] = 0.85
    state["workflow"] = "sql"
    state["tool_results"] = state.get("tool_results", []) + [
        {
            "tool_name": "query_procurement_db",
            "success": True,
            "result": {"rows": len(rows)},
            "error": None,
        }
    ]
    return state
