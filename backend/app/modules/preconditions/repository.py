"""Acceso a datos del modulo `preconditions`. Unico archivo que arma consultas.

La regla de "maximo un nivel de jerarquia" la fuerza el trigger de BD
`fn_preconditions_depth` (ver `models.py`); este modulo no la reimplementa,
solo captura la excepcion Postgres que el trigger lanza al violarla y la
traduce a `PreconditionHierarchyError` (ver AGENTS.md seccion "Errores").
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import paginate
from app.modules.preconditions.exceptions import PreconditionHierarchyError
from app.modules.preconditions.models import Precondition
from app.modules.preconditions.schemas import (
    PreconditionItemCreate,
)


def _is_depth_violation(exc: DBAPIError) -> bool:
    """El trigger `fn_preconditions_depth` lanza un `RAISE EXCEPTION` cuyo
    mensaje empieza con `preconditions:` (ver migracion). No es una
    violacion de constraint (no es `IntegrityError`), por eso se detecta
    por el mensaje del error original, no por su clase.
    """
    return "preconditions:" in str(exc.orig)


async def get_by_code(session: AsyncSession, code: str) -> Precondition | None:
    stmt = select(Precondition).where(Precondition.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_roots(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[Precondition], int]:
    """Lista solo precondiciones raiz (`parent_id IS NULL`), paginadas."""
    stmt = active_filter.apply(
        select(Precondition).where(Precondition.parent_id.is_(None)),
        Precondition.is_active,
    )
    stmt = search.apply(stmt, Precondition.code, Precondition.name)
    return await paginate(session, stmt, pagination, Precondition.name)


async def get_items_bulk(
    session: AsyncSession, parent_ids: list[UUID]
) -> dict[UUID, list[Precondition]]:
    """Items de varias precondiciones raiz en una sola consulta (sin N+1)."""
    if not parent_ids:
        return {}
    stmt = (
        select(Precondition)
        .where(Precondition.parent_id.in_(parent_ids))
        .order_by(Precondition.name)
    )
    items = (await session.execute(stmt)).scalars().all()

    grouped: dict[UUID, list[Precondition]] = {
        parent_id: [] for parent_id in parent_ids
    }
    for item in items:
        grouped[item.parent_id].append(item)
    return grouped


async def create_item(
    session: AsyncSession, parent_id: UUID, data: PreconditionItemCreate
) -> Precondition:
    item = Precondition(parent_id=parent_id, kind="condition", **data.model_dump())
    session.add(item)
    try:
        await session.commit()
    except DBAPIError as exc:
        await session.rollback()
        if _is_depth_violation(exc):
            raise PreconditionHierarchyError(str(parent_id), str(exc.orig)) from exc
        raise
    await session.refresh(item)
    return item
