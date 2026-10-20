"""Casos de uso / logica de negocio del modulo `samples`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`, solo excepciones
de `app.core.exceptions` que el nucleo traduce a HTTP.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active
from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError
from app.core.repository import create_entity, get_or_404, update_entity
from app.core.schemas import Page
from app.modules.samples import repository
from app.modules.samples.models import Sample, SampleType
from app.modules.samples.schemas import (
    SampleCreate,
    SampleRead,
    SampleTypeCreate,
    SampleTypeRead,
    SampleTypeUpdate,
    SampleUpdate,
)


def _to_read(sample: Sample, types: list[SampleType] | None = None) -> SampleRead:
    base = SampleRead.model_validate(sample)
    if types is not None:
        base = base.model_copy(
            update={"types": [SampleTypeRead.model_validate(t) for t in types]}
        )
    return base


async def list_samples(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[SampleRead]:
    """Lista muestras con sus tipos anidados (sin N+1: una consulta para las
    muestras, una consulta bulk para todos sus tipos).
    """
    samples, total = await repository.list_samples(
        session, pagination, active_filter, search
    )

    types_by_sample = await repository.get_types_bulk(
        session, [sample.id for sample in samples]
    )

    reads = [_to_read(sample, types_by_sample.get(sample.id, [])) for sample in samples]

    return Page[SampleRead](
        items=reads,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_sample(session: AsyncSession, data: SampleCreate) -> SampleRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("una muestra", data.code)
    sample = await create_entity(session, Sample, data)
    return _to_read(sample, types=[])


async def get_sample(session: AsyncSession, sample_id: UUID) -> SampleRead:
    sample = await get_or_404(session, Sample, sample_id, "una muestra")
    types_by_sample = await repository.get_types_bulk(session, [sample.id])
    return _to_read(sample, types_by_sample.get(sample.id, []))


async def update_sample(
    session: AsyncSession, sample_id: UUID, data: SampleUpdate
) -> SampleRead:
    sample = await get_or_404(session, Sample, sample_id, "una muestra")

    new_code = data.code
    if new_code is not None and new_code != sample.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("una muestra", new_code)

    sample = await update_entity(session, sample, data)
    types_by_sample = await repository.get_types_bulk(session, [sample.id])
    return _to_read(sample, types_by_sample.get(sample.id, []))


async def list_sample_types(
    session: AsyncSession,
    sample_id: UUID,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[SampleTypeRead]:
    await get_or_404(session, Sample, sample_id, "una muestra")

    types, total = await repository.list_types_by_sample(
        session, sample_id, pagination, active_filter, search
    )

    return Page[SampleTypeRead](
        items=[SampleTypeRead.model_validate(t) for t in types],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_sample_type(
    session: AsyncSession, sample_id: UUID, data: SampleTypeCreate
) -> SampleTypeRead:
    sample = await get_or_404(session, Sample, sample_id, "una muestra")
    ensure_active(sample, subject="la muestra", field="sample_id", feminine=True)

    existing = await repository.get_type_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un tipo de muestra", data.code)

    sample_type = await create_entity(session, SampleType, data, sample_id=sample_id)
    return SampleTypeRead.model_validate(sample_type)


async def get_sample_type(
    session: AsyncSession, sample_type_id: UUID
) -> SampleTypeRead:
    sample_type = await get_or_404(
        session, SampleType, sample_type_id, "un tipo de muestra"
    )
    return SampleTypeRead.model_validate(sample_type)


async def update_sample_type(
    session: AsyncSession, sample_type_id: UUID, data: SampleTypeUpdate
) -> SampleTypeRead:
    sample_type = await get_or_404(
        session, SampleType, sample_type_id, "un tipo de muestra"
    )

    new_code = data.code
    if new_code is not None and new_code != sample_type.code:
        existing = await repository.get_type_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un tipo de muestra", new_code)

    sample_type = await update_entity(session, sample_type, data)
    return SampleTypeRead.model_validate(sample_type)
