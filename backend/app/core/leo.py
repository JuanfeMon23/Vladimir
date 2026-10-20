"""Integracion con Leo (SSO, permisos y auditoria) via `leo_sdk`.

Unico punto donde se crean `LeoSettings`, el `Catalog` y `LeoAuth`. Cada modulo
protegido declara su parte del catalogo en su `permissions.py` (modulo + acciones
+ `require_action`) y registra las mutaciones con `record_audit`.
"""

import logging
from collections.abc import Callable, Mapping
from typing import Any

from fastapi import Request
from leo_sdk import Catalog, LeoAuth, LeoSettings, LeoUser

logger = logging.getLogger("app.leo")

APP_SLUG = "vladimir"

settings = LeoSettings()  # lee el entorno / backend/.env (ver .env.example)
catalog = Catalog(APP_SLUG)
auth = LeoAuth(settings, catalog=catalog)


async def record_audit(
    action_tag: str,
    user: LeoUser,
    *,
    entity_type: str,
    entity_id: object,
    before: Mapping[str, Any] | None = None,
    after: Mapping[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    """Registra un evento de auditoria en Leo con el `diff(before, after)`.

    Un fallo de Leo (o de cualquier otro tipo) se loguea y NO propaga: la
    operacion de negocio ya se confirmo y no debe romperse por la auditoria.
    """
    try:
        await auth.audit.record(
            action_tag,
            entity_type=entity_type,
            entity_id=str(entity_id),
            changes=auth.audit.diff(before, after),
            reason=reason,
            actor=user,
        )
    except Exception:
        logger.exception("No se pudo registrar el evento de auditoría %s.", action_tag)


_NOT_AUDITED = frozenset({"id", "created_at", "updated_at"})


def snapshot(model: Any, *exclude: str) -> dict[str, Any]:
    """Estado auditable de un `XRead`: todos sus campos en JSON salvo id,
    timestamps y los `exclude` (anidados o derivados, que no son datos propios)."""
    return model.model_dump(mode="json", exclude=_NOT_AUDITED | set(exclude))


def patch_intent(data: Any) -> tuple[bool, bool]:
    """`(cambia_datos, cambia_estado)` de un PATCH con `is_active`/`activity_reason`."""
    sent = data.model_fields_set
    changes_status = "is_active" in sent and data.is_active is not None
    changes_data = bool(sent - {"is_active", "activity_reason"}) or not changes_status
    return changes_data, changes_status


async def authorize_patch(
    request: Request,
    user: LeoUser,
    data: Any,
    *,
    edit_check: Callable[..., Any],
    status_check: Callable[..., Any],
) -> None:
    """Un PATCH exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    changes_data, changes_status = patch_intent(data)
    if changes_data:
        await edit_check(request, user)
    if changes_status:
        await status_check(request, user)


async def audit_patch(
    user: LeoUser,
    *,
    edit_tag: str,
    status_tag: str,
    entity_type: str,
    entity_id: object,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    reason: str | None,
) -> None:
    """Audita un PATCH: `edit` con el diff de datos y `change-status` con el de
    `is_active` (+ motivo), solo si cada uno cambio."""
    data_before = {k: v for k, v in before.items() if k != "is_active"}
    data_after = {k: v for k, v in after.items() if k != "is_active"}
    if data_before != data_after:
        await record_audit(
            edit_tag,
            user,
            entity_type=entity_type,
            entity_id=entity_id,
            before=data_before,
            after=data_after,
        )
    if before["is_active"] != after["is_active"]:
        await record_audit(
            status_tag,
            user,
            entity_type=entity_type,
            entity_id=entity_id,
            before={"is_active": before["is_active"]},
            after={"is_active": after["is_active"]},
            reason=reason,
        )
