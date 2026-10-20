"""Catalogo de Leo y dependencias de permiso del modulo `staff`.

Tags `vladimir.staff.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "staff"

catalog.module(MODULE, "Personal", "Personal del laboratorio.")
catalog.action(
    MODULE, "view", "Consultar personal",
    "Listar el personal y ver su detalle.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear personal", "Registrar una persona del personal."
)
catalog.action(
    MODULE, "edit", "Editar personal", "Modificar los datos de una persona."
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar personal",
    "Desactivar una persona o reactivarla.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
