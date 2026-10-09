"""Acceso a datos del modulo `samples`. Unico archivo que arma consultas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.samples.models import Sample, SampleType


async def get_by_code(session: AsyncSession, code: str) -> Sample | None:
    stmt = select(Sample).where(Sample.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_type_by_code(session: AsyncSession, code: str) -> SampleType | None:
    stmt = select(SampleType).where(SampleType.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_samples(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[Sample], int]:
    stmt = active_filter.apply(select(Sample), Sample.is_active)
    stmt = search.apply(stmt, Sample.code, Sample.name)
    return await paginate(session, stmt, pagination, Sample.name)


async def get_types_bulk(
    session: AsyncSession, sample_ids: list[UUID]
) -> dict[UUID, list[SampleType]]:
    """Tipos de varias muestras en una sola consulta (sin N+1)."""
    if not sample_ids:
        return {}
    stmt = (
        select(SampleType)
        .where(SampleType.sample_id.in_(sample_ids))
        .order_by(SampleType.draw_order, SampleType.name)
    )
    types = (await session.execute(stmt)).scalars().all()

    grouped: dict[UUID, list[SampleType]] = {sample_id: [] for sample_id in sample_ids}
    for sample_type in types:
        grouped[sample_type.sample_id].append(sample_type)
    return grouped


async def list_types_by_sample(
    session: AsyncSession,
    sample_id: UUID,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[SampleType], int]:
    stmt = active_filter.apply(
        select(SampleType).where(SampleType.sample_id == sample_id),
        SampleType.is_active,
    )
    stmt = search.apply(stmt, SampleType.code, SampleType.name)
    return await paginate(
        session, stmt, pagination, SampleType.draw_order, SampleType.name
    )
