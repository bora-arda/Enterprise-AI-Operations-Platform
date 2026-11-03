"""Invoice repository for data access."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import Invoice

logger = logging.getLogger(__name__)


class InvoiceRepository:
    """Repository for invoice data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, invoice_id: str | UUID) -> Invoice | None:
        """Get invoice by ID."""
        try:
            result = await self.session.execute(select(Invoice).where(Invoice.id == UUID(str(invoice_id))))
            return result.scalar_one_or_none()
        except ValueError:
            return None

    async def get_by_number(self, invoice_number: str) -> Invoice | None:
        """Get invoice by invoice number."""
        result = await self.session.execute(select(Invoice).where(Invoice.invoice_number == invoice_number))
        return result.scalar_one_or_none()

    async def list_overdue(self, limit: int = 50) -> list[Invoice]:
        """List overdue invoices."""
        result = await self.session.execute(select(Invoice).where(Invoice.status == "overdue").limit(limit))
        return list(result.scalars().all())

    async def list_by_vendor(self, vendor_id: str, limit: int = 50) -> list[Invoice]:
        """List invoices by vendor."""
        result = await self.session.execute(select(Invoice).where(Invoice.vendor_id == UUID(vendor_id)).limit(limit))
        return list(result.scalars().all())

    async def list_by_status(self, status: str, limit: int = 50) -> list[Invoice]:
        """List invoices by status."""
        result = await self.session.execute(select(Invoice).where(Invoice.status == status).limit(limit))
        return list(result.scalars().all())
