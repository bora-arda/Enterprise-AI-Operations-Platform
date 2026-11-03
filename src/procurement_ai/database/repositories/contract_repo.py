"""Contract repository for data access."""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from procurement_ai.database.models import Contract

logger = logging.getLogger(__name__)


class ContractRepository:
    """Repository for contract data access."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, contract_id: str | UUID) -> Contract | None:
        """Get contract by ID."""
        try:
            result = await self.session.execute(select(Contract).where(Contract.id == UUID(str(contract_id))))
            return result.scalar_one_or_none()
        except ValueError:
            return None

    async def get_by_number(self, contract_number: str) -> Contract | None:
        """Get contract by contract number."""
        result = await self.session.execute(select(Contract).where(Contract.contract_number == contract_number))
        return result.scalar_one_or_none()

    async def list_by_vendor(self, vendor_id: str, limit: int = 50) -> list[Contract]:
        """List contracts by vendor."""
        result = await self.session.execute(select(Contract).where(Contract.vendor_id == UUID(vendor_id)).limit(limit))
        return list(result.scalars().all())

    async def list_expiring_soon(self, days: int = 60, limit: int = 50) -> list[Contract]:
        """List contracts expiring within specified days."""
        from datetime import date, timedelta

        cutoff = date.today() + timedelta(days=days)
        result = await self.session.execute(select(Contract).where(Contract.end_date <= cutoff).limit(limit))
        return list(result.scalars().all())
