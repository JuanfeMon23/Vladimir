"""Catalogo de Leo y dependencias de permiso del modulo `samples`.

Tags `vladimir.samples.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "samples"

catalog.module(MODULE, "Muestras", "Muestras y sus tipos (tubos, aditivos, volúmenes).")
catalog.action(
    MODULE, "view", "Consultar muestras",
    "Listar muestras y sus tipos y ver su detalle.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear muestras", "Registrar una muestra."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar muestras",
    "Modificar los datos de una muestra o de uno de sus tipos.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar muestras",
    "Desactivar una muestra o un tipo de muestra, o reactivarlos.",
)  # fmt: skip
catalog.action(
    MODULE, "add-type", "Agregar tipos a muestras",
    "Agregar un tipo de muestra (tubo) a una muestra.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
ADD_TYPE = f"{APP_SLUG}.{MODULE}.add-type"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanAddType = Annotated[LeoUser, auth.require_action(ADD_TYPE)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
