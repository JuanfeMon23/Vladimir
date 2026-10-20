"""Integracion con Leo (SSO, permisos y auditoria) via `leo_sdk`.

Unico punto donde se crean `LeoSettings`, el `Catalog` y `LeoAuth`. Cada modulo
protegido declara su parte del catalogo en su `permissions.py` (modulo + acciones
+ `require_action`) y registra las mutaciones con `record_audit`.
"""

import logging
from collections.abc import Mapping
from typing import Any

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
