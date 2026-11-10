"""Acceso a datos del modulo `catalogs`. Unico archivo que arma consultas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def list_items[ModelT](
    session: AsyncSession, model: type[ModelT], *, include_inactive: bool
) -> list[ModelT]:
    """Filas del catalogo por `sort_order` (y `code` para desempatar)."""
    stmt = select(model).order_by(model.sort_order, model.code)  # type: ignore[attr-defined]
    if not include_inactive:
        stmt = stmt.where(model.is_active.is_(True))  # type: ignore[attr-defined]
    return list((await session.execute(stmt)).scalars())


async def get_flagged_row[ModelT](
    session: AsyncSession,
    model: type[ModelT],
    flag: str,
    *,
    exclude_id: UUID | None = None,
) -> ModelT | None:
    """Otra fila con la bandera `flag` en `true` (indice unico parcial)."""
    stmt = select(model).where(getattr(model, flag).is_(True))
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)  # type: ignore[attr-defined]
    return (await session.execute(stmt.limit(1))).scalar_one_or_none()
