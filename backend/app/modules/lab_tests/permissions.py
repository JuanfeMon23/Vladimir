"""Catalogo de Leo y dependencias de permiso del modulo `lab_tests`.

Tags `vladimir.lab-tests.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "lab-tests"

catalog.module(
    MODULE, "Exámenes de laboratorio",
    "Exámenes con sus precondiciones, tipos de muestra y documentos a firmar.",
)  # fmt: skip
catalog.action(
    MODULE, "view", "Consultar exámenes de laboratorio",
    "Listar exámenes, ver su detalle y sus precondiciones, muestras y documentos.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear exámenes de laboratorio", "Registrar un examen."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar exámenes de laboratorio",
    "Modificar los datos del examen y sus versiones de etiqueta y plantilla.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar exámenes de laboratorio",
    "Desactivar un examen o reactivarlo.",
)  # fmt: skip
catalog.action(
    MODULE, "set-preconditions", "Asignar precondiciones a exámenes",
    "Reemplazar el conjunto de precondiciones de un examen.",
)  # fmt: skip
catalog.action(
    MODULE, "set-sample-types", "Asignar tipos de muestra a exámenes",
    "Reemplazar el conjunto de tipos de muestra de un examen.",
)  # fmt: skip
catalog.action(
    MODULE, "set-consent-documents", "Asignar documentos a firmar a exámenes",
    "Reemplazar el conjunto de documentos a firmar de un examen.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
SET_PRECONDITIONS = f"{APP_SLUG}.{MODULE}.set-preconditions"
SET_SAMPLE_TYPES = f"{APP_SLUG}.{MODULE}.set-sample-types"
SET_CONSENT_DOCUMENTS = f"{APP_SLUG}.{MODULE}.set-consent-documents"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanSetPreconditions = Annotated[LeoUser, auth.require_action(SET_PRECONDITIONS)]
CanSetSampleTypes = Annotated[LeoUser, auth.require_action(SET_SAMPLE_TYPES)]
CanSetConsentDocuments = Annotated[LeoUser, auth.require_action(SET_CONSENT_DOCUMENTS)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
