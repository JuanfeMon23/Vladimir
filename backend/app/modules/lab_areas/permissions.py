"""Catalogo de Leo y dependencias de permiso del modulo `lab_areas`.

Tags `vladimir.lab-areas.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "lab-areas"

catalog.module(MODULE, "Áreas de laboratorio", "Áreas del laboratorio y su encargado.")
catalog.action(
    MODULE, "view", "Consultar áreas de laboratorio",
    "Listar áreas, ver su detalle y el historial de encargados.",
)  # fmt: skip
catalog.action(MODULE, "create", "Crear áreas de laboratorio", "Registrar un área.")
catalog.action(
    MODULE, "edit", "Editar áreas de laboratorio", "Modificar código, nombre y descripción."
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar áreas de laboratorio",
    "Desactivar un área o reactivarla.",
)  # fmt: skip
catalog.action(
    MODULE, "assign-manager", "Asignar encargado de área de laboratorio",
    "Asignar o cambiar el encargado vigente de un área.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
ASSIGN_MANAGER = f"{APP_SLUG}.{MODULE}.assign-manager"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanAssignManager = Annotated[LeoUser, auth.require_action(ASSIGN_MANAGER)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
