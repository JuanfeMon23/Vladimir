"""Catalogo de Leo y dependencias de permiso del modulo `print_labels`.

Tags `vladimir.print-labels.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "print-labels"

catalog.module(
    MODULE, "Etiquetas de impresión",
    "Etiquetas de muestras y sus versiones (borrador, publicada, retirada).",
)  # fmt: skip
catalog.action(
    MODULE, "view", "Consultar etiquetas de impresión",
    "Listar etiquetas, ver su detalle y el de sus versiones.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear etiquetas de impresión", "Registrar una etiqueta."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar etiquetas de impresión",
    "Modificar los datos de una etiqueta.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar etiquetas de impresión",
    "Desactivar una etiqueta o reactivarla.",
)  # fmt: skip
catalog.action(
    MODULE, "create-version", "Crear versiones de etiquetas",
    "Crear el borrador de una nueva versión de una etiqueta.",
)  # fmt: skip
catalog.action(
    MODULE, "edit-version", "Editar versiones de etiquetas",
    "Modificar el borrador de una versión de una etiqueta.",
)  # fmt: skip
catalog.action(
    MODULE, "publish-version", "Publicar versiones de etiquetas",
    "Publicar el borrador de una versión para que los exámenes puedan usarla.",
)  # fmt: skip
catalog.action(
    MODULE, "retire-version", "Retirar versiones de etiquetas",
    "Retirar una versión publicada.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
CREATE_VERSION = f"{APP_SLUG}.{MODULE}.create-version"
EDIT_VERSION = f"{APP_SLUG}.{MODULE}.edit-version"
PUBLISH_VERSION = f"{APP_SLUG}.{MODULE}.publish-version"
RETIRE_VERSION = f"{APP_SLUG}.{MODULE}.retire-version"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanCreateVersion = Annotated[LeoUser, auth.require_action(CREATE_VERSION)]
CanEditVersion = Annotated[LeoUser, auth.require_action(EDIT_VERSION)]
CanPublishVersion = Annotated[LeoUser, auth.require_action(PUBLISH_VERSION)]
CanRetireVersion = Annotated[LeoUser, auth.require_action(RETIRE_VERSION)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
