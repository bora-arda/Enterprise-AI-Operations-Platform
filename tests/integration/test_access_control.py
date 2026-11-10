"""Integration checks for department-scoped agent data access."""

import pytest
from sqlalchemy import select

from procurement_ai.agent.tools import execute_tool
from procurement_ai.database.connection import AsyncSessionLocal
from procurement_ai.database.models import PurchaseOrder
from procurement_ai.security.access import build_access_scope


@pytest.mark.asyncio
async def test_specialist_exception_scope_is_smaller_than_global():
    async with AsyncSessionLocal() as session:
        department_id = await session.scalar(
            select(PurchaseOrder.department_id).where(PurchaseOrder.department_id.isnot(None)).limit(1)
        )
    assert department_id is not None

    scope = build_access_scope(
        "access-test",
        "specialist",
        str(department_id),
        enabled=True,
    )
    scoped = await execute_tool(
        "list_exceptions",
        {"limit": 1},
        scope=scope,
    )
    global_result = await execute_tool("list_exceptions", {"limit": 1})
    assert scoped["total"] < global_result["total"]
    assert scoped["total"] >= 0
