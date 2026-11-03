"""Purchase order repository for data access."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import PurchaseOrder

logger = logging.getLogger(__name__)


class PurchaseOrderRepository:
    """Repository for purchase order data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, po_id: str | UUID) -> PurchaseOrder | None:
        """Get PO by ID."""
        try:
            result = await self.session.execute(select(PurchaseOrder).where(PurchaseOrder.id == UUID(str(po_id))))
            return result.scalar_one_or_none()
        except ValueError:
            return None

    async def get_by_number(self, po_number: str) -> PurchaseOrder | None:
        """Get PO by PO number."""
        result = await self.session.execute(select(PurchaseOrder).where(PurchaseOrder.po_number == po_number))
        return result.scalar_one_or_none()

    async def list_by_contract(self, contract_id: str, limit: int = 50) -> list[PurchaseOrder]:
        """List POs by contract."""
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.contract_id == UUID(contract_id)).limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_vendor(self, vendor_id: str, limit: int = 50) -> list[PurchaseOrder]:
        """List POs by vendor."""
        result = await self.session.execute(
            select(PurchaseOrder).where(PurchaseOrder.vendor_id == UUID(vendor_id)).limit(limit)
        )
        return list(result.scalars().all())
