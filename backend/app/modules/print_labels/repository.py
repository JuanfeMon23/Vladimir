"""Acceso a datos del modulo `print_labels`. Unico archivo que arma consultas."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.print_labels.models import PrintLabel


async def get_by_code(session: AsyncSession, code: str) -> PrintLabel | None:
    stmt = select(PrintLabel).where(PrintLabel.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_labels(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[PrintLabel], int]:
    stmt = active_filter.apply(select(PrintLabel), PrintLabel.is_active)
    stmt = search.apply(stmt, PrintLabel.code, PrintLabel.name)
    return await paginate(session, stmt, pagination, PrintLabel.name)
