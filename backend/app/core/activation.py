"""Activacion/desactivacion: "nada se elimina, solo se desactiva".

Reglas de negocio (usuario, 2026-10-02):
1. Nada se elimina fisicamente: la BD bloquea los DELETE (SQLSTATE `VLD01`,
   mapeado a `409 delete_forbidden` en `core/exceptions.py`).
2. No se crean relaciones NUEVAS con elementos desactivados
   (`ensure_active`); las existentes se conservan.
3. Cada (des)activacion queda en `activity_events` con fecha-hora y motivo
   opcional. La fila la escribe un trigger de BD; el motivo se le pasa con
   `set_config('vladimir.activity_reason', ..., true)` en la misma
   transaccion del UPDATE (`flush_with_reason`).

Uso tipico en un repository (ver tambien `core/repository.py::update_entity`,
que ya lo hace para todo PATCH):

    entity.is_active = False
    await flush_with_reason(session, data.activity_reason)
    await session.commit()

Uso en un controller, antes de asociar una referencia:

    ensure_active(analyte, subject="el analito", field="analyte_id")
"""

from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.triggers import ACTIVITY_REASON_SETTING
from app.core.exceptions import InvalidReferenceError, ValidationAppError


class _Activatable(Protocol):
    id: Any
    is_active: bool


class InactiveReferenceError(ValidationAppError):
    """Se intento crear una relacion nueva con un elemento desactivado (o
    publicar una version que incluye algo desactivado)."""

    code = "inactive_reference"


def _identifier(entity: Any) -> str:
    """Lo que el usuario reconoce del elemento: `code`, si no `name`, si no
    el `id`."""
    for attr in ("code", "name"):
        value = getattr(entity, attr, None)
        if value:
            return str(value)
    return str(entity.id)


def ensure_active(
    entity: _Activatable, *, subject: str, field: str, feminine: bool = False
) -> None:
    """`InactiveReferenceError` (422, `inactive_reference`) si `entity` esta
    desactivado.

    - `subject`: sustantivo con articulo definido ("el analito", "la unidad").
    - `field`: nombre tecnico del campo del body que lo referencia; es la
      clave de `details` (el frontend la usa para ubicar el error).
    - `feminine`: concordancia de "inactivo/inactiva".
    """
    if entity.is_active:
        return
    adjective = "inactiva" if feminine else "inactivo"
    raise InactiveReferenceError(
        message=f"{subject[:1].upper()}{subject[1:]} «{_identifier(entity)}» "
        f"está {adjective}.",
        details={field: str(entity.id)},
    )


def ensure_active_reference[EntityT: _Activatable](
    entity: EntityT | None,
    *,
    subject: str,
    field: str,
    value: object,
    feminine: bool = False,
) -> EntityT:
    """Referencia NUEVA desde un body: `InvalidReferenceError` (422,
    `invalid_reference`) si no existe, `InactiveReferenceError` si esta
    desactivada. Devuelve la entidad para seguir usandola."""
    if entity is None:
        raise InvalidReferenceError(subject, field, value)
    ensure_active(entity, subject=subject, field=field, feminine=feminine)
    return entity


async def flush_with_reason(session: AsyncSession, reason: str | None) -> None:
    """Hace `flush` de los cambios pendientes con `reason` como motivo de
    cualquier (des)activacion que incluyan.

    El motivo (`set_config(..., true)`) es local a la transaccion: se descarta
    con el `commit`/`rollback` que sigue, asi que no se limpia aparte. Sin
    autoflush al fijarlo: los cambios pendientes deben llegar a la BD despues
    del motivo, no antes. Llamar solo cuando hay un cambio de `is_active`.
    """
    with session.no_autoflush:
        await session.execute(
            select(func.set_config(ACTIVITY_REASON_SETTING, reason or "", True))
        )
    await session.flush()


async def get_active_by_id[ModelT](
    session: AsyncSession, model: type[ModelT], entity_id: UUID
) -> ModelT | None:
    """La fila `entity_id` de `model` solo si existe y esta activa."""
    entity = await session.get(model, entity_id)
    if entity is None or not entity.is_active:  # type: ignore[attr-defined]
        return None
    return entity
