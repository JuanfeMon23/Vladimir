"""Validacion de referencias a catalogos de categoria (regla «Catalogos en BD»).

Las columnas de categoria (`kind`, `document_type`, `result_type`...) son FK al
`code` de su tabla de catalogo (`CategoryMixin`). El schema ya no lista los
valores: el controller comprueba contra la BD que el codigo exista y este
activo, con el mismo formato de error que el resto de referencias nuevas
(422 `invalid_reference` / `inactive_reference`).
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active_reference


async def get_category[ModelT](
    session: AsyncSession, model: type[ModelT], code: str
) -> ModelT | None:
    """La fila del catalogo con ese `code`, activa o no (`None` si no existe)."""
    stmt = select(model).where(model.code == code)  # type: ignore[attr-defined]
    return (await session.execute(stmt)).scalar_one_or_none()


async def ensure_category[ModelT](
    session: AsyncSession,
    model: type[ModelT],
    code: str | None,
    *,
    subject: str,
    field: str,
    feminine: bool = False,
    current: Any = None,
) -> ModelT | None:
    """Referencia NUEVA a un catalogo de categoria: 422 `invalid_reference` si
    el `code` no existe, 422 `inactive_reference` si esta desactivado.

    Devuelve la fila (para leer sus columnas de comportamiento), o `None` si
    `code` es `None` o igual a `current` (valor que la fila ya tenia: una
    referencia existente no se revalida aunque la categoria se haya desactivado).
    """
    if code is None or code == current:
        return None
    return ensure_active_reference(
        await get_category(session, model, code),
        subject=subject,
        field=field,
        value=code,
        feminine=feminine,
    )


async def categories_by_code[ModelT](
    session: AsyncSession, model: type[ModelT]
) -> dict[str, ModelT]:
    """Todas las filas del catalogo (activas o no) por `code`: para leer sus
    columnas de comportamiento en una sola consulta."""
    rows = (await session.execute(select(model))).scalars()
    return {row.code: row for row in rows}  # type: ignore[attr-defined]
