"""Acceso a datos del modulo `staff`. Unico archivo que arma consultas."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.staff.models import Staff


async def get_by_document_number(
    session: AsyncSession, document_number: str
) -> Staff | None:
    stmt = select(Staff).where(Staff.document_number == document_number)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_staff(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[Staff], int]:
    stmt = active_filter.apply(select(Staff), Staff.is_active)
    stmt = search.apply(
        stmt,
        Staff.first_name,
        Staff.last_name,
        Staff.document_number,
        Staff.email,
        Staff.job_title,
    )
    return await paginate(session, stmt, pagination, Staff.last_name, Staff.first_name)
