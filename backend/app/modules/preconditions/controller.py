"""Casos de uso / logica de negocio del modulo `preconditions`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`, solo excepciones
de `app.modules.preconditions.exceptions` que el nucleo traduce a HTTP.
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
from app.modules.preconditions import repository
from app.modules.preconditions.models import Precondition
from app.modules.preconditions.schemas import (
    PreconditionCreate,
    PreconditionItemCreate,
    PreconditionRead,
    PreconditionUpdate,
)


def _to_read(
    precondition: Precondition, items: list[Precondition] | None = None
) -> PreconditionRead:
    base = PreconditionRead.model_validate(precondition)
    if items is not None:
        base = base.model_copy(
            update={"items": [PreconditionRead.model_validate(item) for item in items]}
        )
    return base


async def list_preconditions(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[PreconditionRead]:
    """Lista precondiciones raiz con sus items anidados (sin N+1: una
    consulta para las raices, una consulta bulk para todos sus items).
    """
    roots, total = await repository.list_roots(
        session, pagination, active_filter, search
    )

    items_by_parent = await repository.get_items_bulk(
        session, [root.id for root in roots]
    )

    reads = [_to_read(root, items_by_parent.get(root.id, [])) for root in roots]

    return Page[PreconditionRead](
        items=reads,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_precondition(
    session: AsyncSession, data: PreconditionCreate
) -> PreconditionRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("una precondición", data.code)
    precondition = await create_entity(
        session, Precondition, data, parent_id=None, kind="precondition"
    )
    return _to_read(precondition, items=[])


async def create_item(
    session: AsyncSession, parent_id: UUID, data: PreconditionItemCreate
) -> PreconditionRead:
    parent = await get_or_404(session, Precondition, parent_id, "una precondicion")
    ensure_active(parent, subject="la precondición", field="parent_id", feminine=True)

    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("una precondición", data.code)

    item = await repository.create_item(session, parent_id, data)
    return _to_read(item)


async def get_precondition(
    session: AsyncSession, precondition_id: UUID
) -> PreconditionRead:
    precondition = await get_or_404(
        session, Precondition, precondition_id, "una precondicion"
    )
    if precondition.parent_id is None:
        items_by_parent = await repository.get_items_bulk(session, [precondition.id])
        return _to_read(precondition, items_by_parent.get(precondition.id, []))
    return _to_read(precondition)


async def update_precondition(
    session: AsyncSession, precondition_id: UUID, data: PreconditionUpdate
) -> PreconditionRead:
    precondition = await get_or_404(
        session, Precondition, precondition_id, "una precondicion"
    )

    new_code = data.code
    if new_code is not None and new_code != precondition.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("una precondición", new_code)

    precondition = await update_entity(session, precondition, data)

    if precondition.parent_id is None:
        items_by_parent = await repository.get_items_bulk(session, [precondition.id])
        return _to_read(precondition, items_by_parent.get(precondition.id, []))
    return _to_read(precondition)
