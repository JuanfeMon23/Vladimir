"""Catalogo de Leo y dependencias de permiso del modulo `preconditions`.

Tags `vladimir.preconditions.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "preconditions"

catalog.module(MODULE, "Precondiciones", "Precondiciones de los exámenes y sus ítems.")
catalog.action(
    MODULE, "view", "Consultar precondiciones",
    "Listar precondiciones con sus ítems y ver su detalle.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear precondiciones", "Registrar una precondición."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar precondiciones", "Modificar los datos de una precondición."
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar precondiciones",
    "Desactivar una precondición o reactivarla.",
)  # fmt: skip
catalog.action(
    MODULE, "add-item", "Agregar ítems a precondiciones",
    "Agregar un ítem a una precondición.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
ADD_ITEM = f"{APP_SLUG}.{MODULE}.add-item"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanAddItem = Annotated[LeoUser, auth.require_action(ADD_ITEM)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
