"""Rutas `/api/v1/settings`: router compartido del SDK + permisos y auditoria
de Vladimir.

El actor que edita queda en `updated_by`/`changed_by` (id de Leo, sin FK) y
cada cambio emite el evento `vladimir.settings.update` con el valor anterior
y el nuevo.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends
from leo_sdk import LeoUser
from leo_sdk.settings_store import SettingsRouterDeps, build_settings_router

from app.core import runtime_settings
from app.core.leo import auth, record_audit
from app.modules.settings import permissions as p

ENTITY_TYPE = "setting"


@dataclass(frozen=True)
class SettingsCaller:
    """Quien edita: el usuario de Leo y los campos que lee el store."""

    user: LeoUser
    user_id: UUID
    username: str


def _caller_dep(tag: str) -> Callable[..., Awaitable[SettingsCaller]]:
    async def dependency(
        user: Annotated[LeoUser, auth.require_action(tag)],
    ) -> SettingsCaller:
        return SettingsCaller(user=user, user_id=user.id, username=user.username)

    return dependency


async def audit_update(
    caller: SettingsCaller, key: str, before: Any, after: Any, reason: str
) -> None:
    """Evento `vladimir.settings.update` (before/after del valor y motivo)."""
    await record_audit(
        p.UPDATE_EVENT,
        caller.user,
        entity_type=ENTITY_TYPE,
        entity_id=key,
        before={"value": before},
        after={"value": after},
        reason=reason,
    )


settings_router = build_settings_router(
    runtime_settings.store,
    SettingsRouterDeps(
        view_dep=auth.require_action(p.VIEW),
        edit_dep=Depends(_caller_dep(p.EDIT)),
        edit_security_dep=Depends(_caller_dep(p.EDIT_SECURITY)),
        audit=audit_update,
    ),
)
