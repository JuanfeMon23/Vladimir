"""Helpers genericos de acceso a datos reusados por los `repository.py` de
los modulos (sin logica de negocio; no conocen ningun modelo concreto).

- `paginate`: total + pagina de un `select`, para `Page[T]`.
- `get_or_404`: una fila por id o `NotFoundError` (404).
- `create_entity`: crea una fila desde un schema de entrada y hace commit.
- `update_entity`: aplica un PATCH (`exclude_unset`) y hace commit,
  registrando `activity_reason` como motivo si el PATCH cambia `is_active`.
- `get_by_ids`: varias filas por id en una consulta (`{id: fila}`).
- `sync_collection`: reemplaza un set completo de filas hijas desactivando,
  reactivando e insertando (nunca `DELETE`).
"""

from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Select, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import flush_with_reason
from app.core.dependencies import PaginationParams
from app.core.exceptions import not_found

# Campos de entrada que no son columnas de la entidad.
_NON_COLUMN_FIELDS = {"activity_reason"}


async def paginate(
    session: AsyncSession,
    stmt: Select,
    pagination: PaginationParams,
    *order_by: Any,
) -> tuple[list[Any], int]:
    """Ejecuta `stmt` (un `select(Model)` ya filtrado) paginado: devuelve
    `(items, total)`. El total se cuenta sobre el mismo `stmt` sin
    `ORDER BY` ni `LIMIT`, y sin sus columnas (`SELECT 1`): asi el conteo no
    nombra columnas pesadas como `file_base64`. Mismas filas que `stmt` salvo
    que use `DISTINCT`/`GROUP BY` (hoy ningun listado lo usa)."""
    rows = stmt.order_by(None).with_only_columns(
        literal_column("1"), maintain_column_froms=True
    )
    count_stmt = select(func.count()).select_from(rows.subquery())
    total = (await session.execute(count_stmt)).scalar_one()
    page_stmt = (
        stmt.order_by(*order_by).offset(pagination.offset).limit(pagination.limit)
    )
    items = (await session.execute(page_stmt)).scalars().all()
    return list(items), total


async def get_or_404[ModelT](
    session: AsyncSession, model: type[ModelT], entity_id: UUID, subject: str
) -> ModelT:
    """La fila `entity_id` de `model`, o `NotFoundError` ("No existe
    {subject} con id '...'.", ver `core.exceptions.not_found`)."""
    entity = await session.get(model, entity_id)
    if entity is None:
        raise not_found(subject, entity_id)
    return entity


async def create_entity[ModelT](
    session: AsyncSession, model: type[ModelT], data: BaseModel, **extra: Any
) -> ModelT:
    """`model(**data, **extra)` + commit + refresh. `extra`: columnas que no
    vienen del body (FK del padre, `kind`, ...)."""
    entity = model(**data.model_dump(), **extra)
    session.add(entity)
    await session.commit()
    await session.refresh(entity)
    return entity


async def update_entity[EntityT](
    session: AsyncSession, entity: EntityT, data: BaseModel, **extra: Any
) -> EntityT:
    """PATCH completo: copia a `entity` los campos enviados (`exclude_unset`,
    sin los que no son columnas, como `activity_reason`) mas `extra`, y hace
    commit y refresh. Si el PATCH cambia `is_active`, el flush previo lleva
    `data.activity_reason` como motivo de la (des)activacion."""
    changes = data.model_dump(exclude_unset=True, exclude=_NON_COLUMN_FIELDS)
    for field, value in {**changes, **extra}.items():
        setattr(entity, field, value)
    if "is_active" in changes:
        await flush_with_reason(session, getattr(data, "activity_reason", None))
    await session.commit()
    await session.refresh(entity)
    return entity


async def sync_collection[RowT](
    session: AsyncSession,
    rows: list[RowT],
    key: str,
    desired: dict[Any, dict[str, Any]],
    make: Callable[[Any, dict[str, Any]], RowT],
) -> None:
    """Reemplazo de un set completo sin borrar (nada se elimina, solo se
    desactiva), en la transaccion en curso (sin commit):

    - fila existente cuya clave no esta en `desired` -> `is_active = False`;
    - clave de `desired` que ya tiene fila (activa o no) -> se reactiva la
      MISMA fila y se le aplican los valores nuevos;
    - clave nueva -> `make(clave, valores)` y se inserta.

    `rows`: todas las filas del padre (activas e inactivas). `key`: atributo
    de la fila que identifica el elemento asociado (p. ej. `precondition_id`).
    Las desactivaciones se envian a la BD antes que el resto, para no chocar
    con indices unicos parciales `WHERE is_active`.
    """
    by_key = {getattr(row, key): row for row in rows}
    for row_key, row in by_key.items():
        if row_key not in desired and row.is_active:  # type: ignore[attr-defined]
            row.is_active = False  # type: ignore[attr-defined]
    await session.flush()

    for row_key, values in desired.items():
        row = by_key.get(row_key)
        if row is None:
            session.add(make(row_key, values))
            continue
        row.is_active = True  # type: ignore[attr-defined]
        for field, value in values.items():
            setattr(row, field, value)
    await session.flush()


async def get_by_ids[ModelT](
    session: AsyncSession, model: type[ModelT], ids: Iterable[Any]
) -> dict[Any, ModelT]:
    """Filas de `model` por id en una sola consulta (sin N+1): `{id: fila}`.
    Los ids inexistentes simplemente no aparecen."""
    unique_ids = {entity_id for entity_id in ids if entity_id is not None}
    if not unique_ids:
        return {}
    stmt = select(model).where(model.id.in_(unique_ids))  # type: ignore[attr-defined]
    rows = (await session.execute(stmt)).scalars().all()
    return {row.id: row for row in rows}  # type: ignore[attr-defined]
