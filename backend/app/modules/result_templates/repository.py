"""Acceso a datos del modulo `result_templates`. Unico archivo que arma
consultas."""

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
from app.modules.result_templates.models import (
    Analyte,
    ReferenceRange,
    ResultOption,
    ResultOptionSet,
    ResultTemplate,
    ResultTemplateAnalyte,
    ResultTemplateSection,
    Unit,
)

# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------


async def get_unit_by_code(session: AsyncSession, code: str) -> Unit | None:
    stmt = select(Unit).where(Unit.code == code)
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_units(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[Unit], int]:
    stmt = active_filter.apply(select(Unit), Unit.is_active)
    stmt = search.apply(stmt, Unit.code, Unit.symbol, Unit.name)
    return await paginate(session, stmt, pagination, Unit.code)


# --------------------------------------------------------------------------
# Analytes
# --------------------------------------------------------------------------


async def get_analyte_by_code(session: AsyncSession, code: str) -> Analyte | None:
    stmt = select(Analyte).where(Analyte.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_analytes(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[Analyte], int]:
    stmt = active_filter.apply(select(Analyte), Analyte.is_active)
    stmt = search.apply(stmt, Analyte.code, Analyte.name, Analyte.loinc_code)
    return await paginate(session, stmt, pagination, Analyte.name)


# --------------------------------------------------------------------------
# Result option sets
# --------------------------------------------------------------------------


async def get_option_set_by_code(
    session: AsyncSession, code: str
) -> ResultOptionSet | None:
    stmt = select(ResultOptionSet).where(ResultOptionSet.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_option_sets(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[ResultOptionSet], int]:
    stmt = active_filter.apply(select(ResultOptionSet), ResultOptionSet.is_active)
    stmt = search.apply(stmt, ResultOptionSet.code, ResultOptionSet.name)
    return await paginate(session, stmt, pagination, ResultOptionSet.name)


# --------------------------------------------------------------------------
# Result options
# --------------------------------------------------------------------------


async def get_option_by_set_and_code(
    session: AsyncSession, option_set_id: UUID, code: str
) -> ResultOption | None:
    stmt = select(ResultOption).where(
        ResultOption.option_set_id == option_set_id, ResultOption.code == code
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_options_by_set(
    session: AsyncSession,
    option_set_id: UUID,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[ResultOption], int]:
    stmt = active_filter.apply(
        select(ResultOption).where(ResultOption.option_set_id == option_set_id),
        ResultOption.is_active,
    )
    stmt = search.apply(stmt, ResultOption.code, ResultOption.label)
    return await paginate(session, stmt, pagination, ResultOption.sort_order)


# --------------------------------------------------------------------------
# Result templates
# --------------------------------------------------------------------------


async def get_template_by_code(
    session: AsyncSession, code: str
) -> ResultTemplate | None:
    stmt = select(ResultTemplate).where(ResultTemplate.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_templates(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[ResultTemplate], int]:
    stmt = active_filter.apply(select(ResultTemplate), ResultTemplate.is_active)
    stmt = search.apply(stmt, ResultTemplate.code, ResultTemplate.name)
    return await paginate(session, stmt, pagination, ResultTemplate.name)


# --------------------------------------------------------------------------
# Result template versions
# --------------------------------------------------------------------------


async def list_sections_by_version(
    session: AsyncSession, version_id: UUID, *, include_inactive: bool = False
) -> list[ResultTemplateSection]:
    stmt = select(ResultTemplateSection).where(
        ResultTemplateSection.version_id == version_id
    )
    if not include_inactive:
        stmt = stmt.where(ResultTemplateSection.is_active.is_(True))
    stmt = stmt.order_by(ResultTemplateSection.sort_order, ResultTemplateSection.id)
    return list((await session.execute(stmt)).scalars().all())


async def list_analytes_by_version(
    session: AsyncSession, version_id: UUID, *, include_inactive: bool = False
) -> list[ResultTemplateAnalyte]:
    stmt = select(ResultTemplateAnalyte).where(
        ResultTemplateAnalyte.version_id == version_id
    )
    if not include_inactive:
        stmt = stmt.where(ResultTemplateAnalyte.is_active.is_(True))
    stmt = stmt.order_by(ResultTemplateAnalyte.sort_order, ResultTemplateAnalyte.id)
    return list((await session.execute(stmt)).scalars().all())


async def get_active_template_analyte_for_analyte(
    session: AsyncSession, version_id: UUID, analyte_id: UUID
) -> ResultTemplateAnalyte | None:
    """La fila activa de `analyte_id` en la version (a lo sumo una, indice
    unico parcial `WHERE is_active`)."""
    stmt = select(ResultTemplateAnalyte).where(
        ResultTemplateAnalyte.version_id == version_id,
        ResultTemplateAnalyte.analyte_id == analyte_id,
        ResultTemplateAnalyte.is_active.is_(True),
    )
    return (await session.execute(stmt)).scalar_one_or_none()


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Template analytes
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Reference ranges
# --------------------------------------------------------------------------


async def list_reference_ranges_by_template_analyte(
    session: AsyncSession,
    template_analyte_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[ReferenceRange]:
    ranges = await list_reference_ranges_by_template_analytes(
        session, [template_analyte_id], include_inactive=include_inactive
    )
    return ranges.get(template_analyte_id, [])


async def list_reference_ranges_by_template_analytes(
    session: AsyncSession,
    template_analyte_ids: list[UUID],
    *,
    include_inactive: bool = False,
) -> dict[UUID, list[ReferenceRange]]:
    """Rangos de varios analitos de plantilla en una sola consulta."""
    grouped: dict[UUID, list[ReferenceRange]] = {
        template_analyte_id: [] for template_analyte_id in template_analyte_ids
    }
    if not template_analyte_ids:
        return grouped
    stmt = select(ReferenceRange).where(
        ReferenceRange.template_analyte_id.in_(template_analyte_ids)
    )
    if not include_inactive:
        stmt = stmt.where(ReferenceRange.is_active.is_(True))
    stmt = stmt.order_by(ReferenceRange.created_at, ReferenceRange.id)
    for reference_range in (await session.execute(stmt)).scalars().all():
        grouped[reference_range.template_analyte_id].append(reference_range)
    return grouped
