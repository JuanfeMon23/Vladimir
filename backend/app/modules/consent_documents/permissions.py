"""Catalogo de Leo y dependencias de permiso del modulo `consent_documents`.

Tags `vladimir.consent-documents.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "consent-documents"

catalog.module(
    MODULE, "Documentos a firmar",
    "Consentimientos y documentos que firma el paciente, con sus versiones y PDF.",
)  # fmt: skip
catalog.action(
    MODULE, "view", "Consultar documentos a firmar",
    "Listar documentos, ver su detalle y el de sus versiones, y descargar el PDF.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear documentos a firmar", "Registrar un documento."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar documentos a firmar",
    "Modificar los datos de un documento.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar documentos a firmar",
    "Desactivar un documento o reactivarlo.",
)  # fmt: skip
catalog.action(
    MODULE, "create-version", "Crear versiones de documentos a firmar",
    "Crear el borrador de una nueva versión de un documento.",
)  # fmt: skip
catalog.action(
    MODULE, "edit-version", "Editar versiones de documentos a firmar",
    "Modificar el borrador de una versión (texto, firmante y PDF).",
)  # fmt: skip
catalog.action(
    MODULE, "publish-version", "Publicar versiones de documentos a firmar",
    "Publicar el borrador de una versión para que pueda firmarse y asignarse.",
)  # fmt: skip
catalog.action(
    MODULE, "retire-version", "Retirar versiones de documentos a firmar",
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
