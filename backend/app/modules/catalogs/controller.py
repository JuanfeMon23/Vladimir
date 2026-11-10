"""Casos de uso de los catalogos de categoria. No conoce HTTP.

Genericos: reciben el `CatalogSpec` del catalogo (ver `registry.py`) y valen
para los 9. Nada se elimina: se desactiva con `is_active` (+ `activity_reason`).
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import get_category
from app.core.exceptions import CodeConflictError, ConflictError
from app.core.repository import create_entity, get_or_404, update_entity
from app.modules.catalogs import repository
from app.modules.catalogs.registry import CatalogSpec
from app.modules.catalogs.schemas import CategoryCreate, CategoryRead, CategoryUpdate


async def _ensure_flag_is_free(
    session: AsyncSession, spec: CatalogSpec, exclude_id: UUID | None
) -> None:
    """409 si otra fila ya tiene la bandera exclusiva (p. ej. el comodin)."""
    assert spec.exclusive_flag is not None
    flag, message = spec.exclusive_flag
    other: Any = await repository.get_flagged_row(
        session, spec.model, flag, exclude_id=exclude_id
    )
    if other is not None:
        raise ConflictError(
            message=message.format(code=other.code),
            details={"code": other.code, "id": str(other.id)},
        )


async def list_items(
    session: AsyncSession, spec: CatalogSpec, *, include_inactive: bool
) -> list[CategoryRead]:
    rows = await repository.list_items(
        session, spec.model, include_inactive=include_inactive
    )
    return [spec.read.model_validate(row) for row in rows]


async def get_item(
    session: AsyncSession, spec: CatalogSpec, item_id: UUID
) -> CategoryRead:
    row = await get_or_404(session, spec.model, item_id, spec.noun)
    return spec.read.model_validate(row)


async def create_item(
    session: AsyncSession, spec: CatalogSpec, data: CategoryCreate
) -> CategoryRead:
    if await get_category(session, spec.model, data.code) is not None:
        raise CodeConflictError(spec.noun, data.code)
    if spec.exclusive_flag is not None and getattr(data, spec.exclusive_flag[0]):
        await _ensure_flag_is_free(session, spec, None)
    row = await create_entity(session, spec.model, data)
    return spec.read.model_validate(row)


async def update_item(
    session: AsyncSession, spec: CatalogSpec, item_id: UUID, data: CategoryUpdate
) -> CategoryRead:
    row: Any = await get_or_404(session, spec.model, item_id, spec.noun)
    if spec.exclusive_flag is not None:
        flag = spec.exclusive_flag[0]
        if data.model_dump(exclude_unset=True).get(flag, getattr(row, flag)):
            await _ensure_flag_is_free(session, spec, row.id)
    row = await update_entity(session, row, data)
    return spec.read.model_validate(row)
