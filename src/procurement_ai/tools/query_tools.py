"""SQL query tools for procurement data."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Read-only SQL templates
SQL_TEMPLATES = {
    "overdue_invoices": """
        SELECT i.invoice_number, i.amount, i.currency, i.due_date, i.status
        FROM invoices i
        WHERE i.status = 'overdue'
        ORDER BY i.due_date
        LIMIT :limit
    """,
    "vendor_exceptions": """
        SELECT v.name as vendor_name, COUNT(e.id) as exception_count
        FROM vendors v
        JOIN invoices i ON i.vendor_id = v.id
        JOIN exceptions e ON e.invoice_id = i.id
        GROUP BY v.name
        ORDER BY exception_count DESC
        LIMIT :limit
    """,
    "spending_by_category": """
        SELECT c.category, SUM(i.amount) as total_spending
        FROM contracts c
        JOIN purchase_orders p ON p.contract_id = c.id
        JOIN invoices i ON i.po_id = p.id
        GROUP BY c.category
        ORDER BY total_spending DESC
    """,
    "top_vendors": """
        SELECT v.name, AVG(i.amount) as avg_invoice, COUNT(i.id) as invoice_count
        FROM vendors v
        JOIN invoices i ON i.vendor_id = v.id
        GROUP BY v.name
        ORDER BY avg_invoice DESC
        LIMIT :limit
    """,
    "monthly_spending": """
        SELECT DATE_TRUNC('month', i.invoice_date) as month, SUM(i.amount) as total
        FROM invoices i
        GROUP BY month
        ORDER BY month DESC
        LIMIT :limit
    """,
}


async def query_procurement_db(session: AsyncSession, query_type: str, params: dict | None = None) -> list[dict]:
    """Execute a read-only SQL query."""
    if query_type not in SQL_TEMPLATES:
        raise ValueError(f"Unknown query type: {query_type}")

    sql = SQL_TEMPLATES[query_type]
    params = params or {}

    try:
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"SQL query failed: {e}")
        raise


async def search_invoices(
    session: AsyncSession,
    vendor_id: str | None = None,
    status: str | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    limit: int = 50,
) -> list[dict]:
    """Search invoices with filters."""
    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit}

    if vendor_id:
        conditions.append("i.vendor_id = :vendor_id")
        params["vendor_id"] = vendor_id
    if status:
        conditions.append("i.status = :status")
        params["status"] = status
    if min_amount:
        conditions.append("i.amount >= :min_amount")
        params["min_amount"] = min_amount
    if max_amount:
        conditions.append("i.amount <= :max_amount")
        params["max_amount"] = max_amount

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    sql = f"""
        SELECT i.invoice_number, i.amount, i.currency, i.status, i.invoice_date, i.due_date
        FROM invoices i
        WHERE {where_clause}
        ORDER BY i.invoice_date DESC
        LIMIT :limit
    """

    result = await session.execute(text(sql), params)
    rows = result.mappings().all()
    return [dict(row) for row in rows]
