"""Persistence queries for versioned IEP record lineages."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bridgeline.db.models import IEPRecord


async def get_current_approved_record(
    session: AsyncSession, iep_record_id: UUID
) -> IEPRecord | None:
    """Fetch the sole current approved version without selecting a newer review draft."""

    statement = select(IEPRecord).where(
        IEPRecord.iep_record_id == iep_record_id,
        IEPRecord.approval_state == "approved",
        IEPRecord.is_current_approved.is_(True),
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()
