"""Python data analysis tools."""

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def run_business_analysis(session: AsyncSession, analysis_type: str) -> dict[str, Any]:
    """Run a business analysis query."""
    if analysis_type == "vendor_performance":
        return await _vendor_performance(session)
    elif analysis_type == "spending_trends":
        return await _spending_trends(session)
    elif analysis_type == "overdue_analysis":
        return await _overdue_analysis(session)
    elif analysis_type == "category_breakdown":
        return await _category_breakdown(session)
    else:
        raise ValueError(f"Unknown analysis type: {analysis_type}")


async def _vendor_performance(session: AsyncSession) -> dict:
    """Analyze vendor performance metrics."""
    sql = """
        SELECT
            v.name as vendor_name,
            COUNT(i.id) as total_invoices,
            SUM(i.amount) as total_amount,
            AVG(i.amount) as avg_amount,
            COUNT(CASE WHEN i.status = 'overdue' THEN 1 END) as overdue_count,
            COUNT(CASE WHEN e.id IS NOT NULL THEN 1 END) as exception_count
        FROM vendors v
        LEFT JOIN invoices i ON i.vendor_id = v.id
        LEFT JOIN exceptions e ON e.invoice_id = i.id
        GROUP BY v.name
        ORDER BY total_amount DESC
        LIMIT 20
    """
    result = await session.execute(text(sql))
    rows = result.mappings().all()
    return {"analysis": "vendor_performance", "data": [dict(r) for r in rows]}


async def _spending_trends(session: AsyncSession) -> dict:
    """Analyze spending trends over time."""
    sql = """
        SELECT
            DATE_TRUNC('month', i.invoice_date) as month,
            SUM(i.amount) as total_spending,
            COUNT(i.id) as invoice_count
        FROM invoices i
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    """
    result = await session.execute(text(sql))
    rows = result.mappings().all()
    return {"analysis": "spending_trends", "data": [dict(r) for r in rows]}


async def _overdue_analysis(session: AsyncSession) -> dict:
    """Analyze overdue invoices."""
    sql = """
        SELECT
            i.invoice_number,
            i.amount,
            i.currency,
            i.due_date,
            CURRENT_DATE - i.due_date as days_overdue,
            v.name as vendor_name
        FROM invoices i
        JOIN vendors v ON v.id = i.vendor_id
        WHERE i.status = 'overdue'
        ORDER BY days_overdue DESC
        LIMIT 50
    """
    result = await session.execute(text(sql))
    rows = result.mappings().all()
    return {"analysis": "overdue_analysis", "data": [dict(r) for r in rows]}


async def _category_breakdown(session: AsyncSession) -> dict:
    """Analyze spending by category."""
    sql = """
        SELECT
            c.category,
            c.category_description,
            SUM(i.amount) as total_spending,
            COUNT(i.id) as invoice_count
        FROM contracts c
        JOIN purchase_orders p ON p.contract_id = c.id
        JOIN invoices i ON i.po_id = p.id
        GROUP BY c.category, c.category_description
        ORDER BY total_spending DESC
    """
    result = await session.execute(text(sql))
    rows = result.mappings().all()
    return {"analysis": "category_breakdown", "data": [dict(r) for r in rows]}
