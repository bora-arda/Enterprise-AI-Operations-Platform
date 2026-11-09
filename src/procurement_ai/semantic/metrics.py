"""Governed semantic layer for procurement metrics.

Metrics are defined here with explicit SQL and allow-listed dimensions.
The LLM/planner never writes SQL; it can only request a metric by name with
an allowed dimension and simple filters.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Allow-listed dimension expressions (never user-provided)
DIMENSIONS = {
    "vendor": "COALESCE(v.name, 'Unknown vendor')",
    "category": "COALESCE(c.category_description, c.category, 'Uncategorized')",
    "department": "COALESCE(d.name, 'Unassigned')",
    "month": "TO_CHAR(DATE_TRUNC('month', i.invoice_date), 'YYYY-MM')",
    "status": "COALESCE(i.status, 'unknown')",
    "exception_type": "COALESCE(e.exception_type, 'unknown')",
}

INVOICE_BASE = """
FROM invoices i
LEFT JOIN purchase_orders p ON p.id = i.po_id
LEFT JOIN contracts c ON c.id = p.contract_id
LEFT JOIN vendors v ON v.id = i.vendor_id
LEFT JOIN departments d ON d.id = p.department_id
LEFT JOIN exceptions e ON e.invoice_id = i.id
"""


@dataclass
class MetricRequest:
    metric: str
    dimension: str | None = None
    days: int | None = None
    limit: int = 10


@dataclass
class MetricResult:
    metric: str
    label: str
    dimension: str | None
    rows: list[dict] = field(default_factory=list)
    sql: str = ""
    params: dict = field(default_factory=dict)


METRIC_LABELS = {
    "total_spend": "Total spend",
    "invoice_count": "Invoice count",
    "avg_invoice_value": "Average invoice value",
    "overdue_rate": "Overdue rate",
    "exception_count": "Exception count",
    "exception_rate": "Exception rate",
    "approval_cycle_time": "Average approval time (hours)",
    "contracts_expiring": "Contracts expiring",
    "overdue_invoices": "Overdue invoices",
    "pending_approvals": "Pending approvals",
    "pending_payment_requests": "Pending payment requests",
    "pending_payments": "Pending payments",
}

LIST_METRICS = {
    "overdue_invoices",
    "pending_approvals",
    "pending_payment_requests",
    "pending_payments",
}

# metric -> allowed dimensions
ALLOWED_DIMENSIONS = {
    "total_spend": {"vendor", "category", "department", "month", "status"},
    "invoice_count": {"vendor", "category", "department", "month", "status"},
    "avg_invoice_value": {"vendor", "category", "department", "month"},
    "overdue_rate": {"vendor", "category", "department", "month"},
    "exception_count": {"vendor", "exception_type", "month", "department"},
    "exception_rate": {"vendor", "exception_type", "month", "department"},
    "approval_cycle_time": {"department", "vendor", "month"},
    "contracts_expiring": set(),
    "overdue_invoices": set(),
    "pending_approvals": set(),
    "pending_payment_requests": set(),
    "pending_payments": set(),
}

AGGREGATES = {
    "total_spend": "SUM(i.amount)",
    "invoice_count": "COUNT(DISTINCT i.id)",
    "avg_invoice_value": "AVG(i.amount)",
    "overdue_rate": (
        "100.0 * COUNT(DISTINCT i.id) FILTER (WHERE i.status = 'overdue') / NULLIF(COUNT(DISTINCT i.id), 0)"
    ),
    "exception_count": "COUNT(DISTINCT e.id)",
    "exception_rate": ("100.0 * COUNT(DISTINCT e.id) / NULLIF(COUNT(DISTINCT i.id), 0)"),
    "approval_cycle_time": ("AVG(EXTRACT(EPOCH FROM (a.decided_at - a.requested_at)) / 3600.0)"),
}


def _build_sql(request: MetricRequest) -> tuple[str, dict]:
    metric = request.metric
    params: dict = {"limit": max(request.limit, 20) if metric in LIST_METRICS else request.limit}

    if metric == "overdue_invoices":
        sql = """
            SELECT i.invoice_number AS "Invoice",
                   COALESCE(v.name, 'Unknown vendor') AS "Vendor",
                   i.amount AS "Amount",
                   i.currency AS "Currency",
                   i.due_date AS "Due date",
                   (CURRENT_DATE - i.due_date) AS "Days overdue"
            FROM invoices i
            LEFT JOIN vendors v ON v.id = i.vendor_id
            WHERE i.status = 'overdue'
            ORDER BY "Days overdue" DESC
            LIMIT :limit
        """
        return sql, params

    if metric == "pending_approvals":
        sql = """
            SELECT a.approval_number AS "Approval",
                   a.request_type AS "Type",
                   i.invoice_number AS "Invoice",
                   i.amount AS "Amount",
                   i.currency AS "Currency",
                   COALESCE(v.name, 'Unknown vendor') AS "Vendor",
                   a.justification AS "Justification",
                   a.requested_at AS "Requested"
            FROM approval_requests a
            LEFT JOIN invoices i ON i.id = a.invoice_id
            LEFT JOIN vendors v ON v.id = i.vendor_id
            WHERE a.status = 'pending'
            ORDER BY a.requested_at DESC
            LIMIT :limit
        """
        return sql, params

    if metric == "pending_payment_requests":
        sql = """
            SELECT a.approval_number AS "Approval",
                   i.invoice_number AS "Invoice",
                   i.amount AS "Amount",
                   i.currency AS "Currency",
                   COALESCE(v.name, 'Unknown vendor') AS "Vendor",
                   a.justification AS "Justification",
                   a.requested_at AS "Requested"
            FROM approval_requests a
            LEFT JOIN invoices i ON i.id = a.invoice_id
            LEFT JOIN vendors v ON v.id = i.vendor_id
            WHERE a.status = 'pending' AND a.request_type = 'payment_request'
            ORDER BY a.requested_at DESC
            LIMIT :limit
        """
        return sql, params

    if metric == "pending_payments":
        sql = """
            SELECT p.payment_reference AS "Payment",
                   i.invoice_number AS "Invoice",
                   p.amount AS "Amount",
                   p.currency AS "Currency",
                   p.status AS "Status",
                   p.payment_date AS "Date",
                   COALESCE(v.name, 'Unknown vendor') AS "Vendor"
            FROM payments p
            LEFT JOIN invoices i ON i.id = p.invoice_id
            LEFT JOIN vendors v ON v.id = i.vendor_id
            WHERE p.status IN ('pending', 'processing')
            ORDER BY p.payment_date DESC
            LIMIT :limit
        """
        return sql, params

    if metric == "contracts_expiring":
        days = request.days or 60
        params["days"] = days
        sql = """
            SELECT c.contract_number AS label,
                   c.title AS detail,
                   c.end_date AS end_date,
                   COALESCE(v.name, 'Unknown vendor') AS vendor
            FROM contracts c
            LEFT JOIN vendors v ON v.id = c.vendor_id
            WHERE c.end_date BETWEEN CURRENT_DATE
                  AND CURRENT_DATE + CAST(:days AS INTEGER) * INTERVAL '1 day'
            ORDER BY c.end_date
            LIMIT :limit
        """
        return sql, params

    dimension = request.dimension
    if dimension and dimension not in ALLOWED_DIMENSIONS[metric]:
        dimension = None
    request.dimension = dimension

    dimension_expr = DIMENSIONS[dimension] if dimension else "'total'"
    aggregate = AGGREGATES[metric]
    joins = INVOICE_BASE

    if metric == "approval_cycle_time":
        joins += "LEFT JOIN approval_requests a ON a.invoice_id = i.id "

    where = []
    if request.days:
        params["days"] = request.days
        where.append("i.invoice_date >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    sql = f"""
        SELECT {dimension_expr} AS label,
               {aggregate} AS value
        {joins}
        {where_clause}
        GROUP BY {dimension_expr}
        ORDER BY value DESC NULLS LAST
        LIMIT :limit
    """
    return sql, params


async def compute_metric(session: AsyncSession, request: MetricRequest) -> MetricResult:
    """Execute a metric using the governed definition."""
    if (
        request.metric not in AGGREGATES
        and request.metric != "contracts_expiring"
        and request.metric not in LIST_METRICS
    ):
        raise ValueError(f"Unknown metric: {request.metric}")

    sql, params = _build_sql(request)
    result = await session.execute(text(sql), params)
    rows = [dict(row) for row in result.mappings().all()]

    return MetricResult(
        metric=request.metric,
        label=METRIC_LABELS.get(request.metric, request.metric),
        dimension=request.dimension,
        rows=rows,
        sql=sql.strip(),
        params=params,
    )
