"""Vendor repository for data access."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import Vendor

logger = logging.getLogger(__name__)


class VendorRepository:
    """Repository for vendor data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, vendor_id: str | UUID) -> Vendor | None:
        """Get vendor by ID."""
        try:
            result = await self.session.execute(select(Vendor).where(Vendor.id == UUID(str(vendor_id))))
            return result.scalar_one_or_none()
        except ValueError:
            return None

    async def list_all(self, limit: int = 100) -> list[Vendor]:
        """List all vendors."""
        result = await self.session.execute(select(Vendor).limit(limit))
        return list(result.scalars().all())

    async def search_by_name(self, name: str, limit: int = 20) -> list[Vendor]:
        """Search vendors by name."""
        result = await self.session.execute(select(Vendor).where(Vendor.name.ilike(f"%{name}%")).limit(limit))
        return list(result.scalars().all())
