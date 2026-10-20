"""Catalogo de Leo y dependencias de permiso del modulo `result_templates`.

Tags `vladimir.result-templates.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`.

Agrupamiento: `view` cubre todas las lecturas (unidades, analitos, conjuntos de
opciones, plantillas, versiones y contenido). La plantilla, recurso principal,
lleva `create`/`edit`/`change-status`; su versionado, una accion por paso; el
contenido de un borrador (secciones, analitos y rangos), `edit-content`; y cada
catalogo de apoyo (unidades, analitos, conjuntos de opciones con sus opciones),
una sola accion `manage-*` que cubre crear, editar y (des)activar.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "result-templates"

catalog.module(
    MODULE, "Plantillas de resultados",
    "Plantillas de resultados con sus versiones, y los catálogos que las alimentan: "
    "unidades, analitos y conjuntos de opciones.",
)  # fmt: skip
catalog.action(
    MODULE, "view", "Consultar plantillas de resultados",
    "Listar y ver plantillas, versiones, secciones, analitos, rangos de referencia, "
    "unidades, analitos y conjuntos de opciones.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear plantillas de resultados", "Registrar una plantilla."
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar plantillas de resultados",
    "Modificar los datos de una plantilla.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar plantillas de resultados",
    "Desactivar una plantilla o reactivarla.",
)  # fmt: skip
catalog.action(
    MODULE, "create-version", "Crear versiones de plantillas",
    "Crear el borrador de una nueva versión de una plantilla.",
)  # fmt: skip
catalog.action(
    MODULE, "edit-version", "Editar versiones de plantillas",
    "Modificar el borrador de una versión (ajustes del reporte y notas).",
)  # fmt: skip
catalog.action(
    MODULE, "publish-version", "Publicar versiones de plantillas",
    "Publicar el borrador de una versión para que los exámenes puedan usarla.",
)  # fmt: skip
catalog.action(
    MODULE, "retire-version", "Retirar versiones de plantillas",
    "Retirar una versión publicada.",
)  # fmt: skip
catalog.action(
    MODULE, "edit-content", "Editar contenido de plantillas",
    "Crear, modificar y desactivar secciones, analitos y rangos de referencia "
    "de un borrador.",
)  # fmt: skip
catalog.action(
    MODULE, "manage-units", "Gestionar unidades de medida",
    "Crear, modificar y activar o desactivar unidades.",
)  # fmt: skip
catalog.action(
    MODULE, "manage-analytes", "Gestionar analitos",
    "Crear, modificar y activar o desactivar analitos.",
)  # fmt: skip
catalog.action(
    MODULE, "manage-option-sets", "Gestionar conjuntos de opciones de resultado",
    "Crear, modificar y activar o desactivar conjuntos de opciones y sus opciones.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
CREATE = f"{APP_SLUG}.{MODULE}.create"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
CHANGE_STATUS = f"{APP_SLUG}.{MODULE}.change-status"
CREATE_VERSION = f"{APP_SLUG}.{MODULE}.create-version"
EDIT_VERSION = f"{APP_SLUG}.{MODULE}.edit-version"
PUBLISH_VERSION = f"{APP_SLUG}.{MODULE}.publish-version"
RETIRE_VERSION = f"{APP_SLUG}.{MODULE}.retire-version"
EDIT_CONTENT = f"{APP_SLUG}.{MODULE}.edit-content"
MANAGE_UNITS = f"{APP_SLUG}.{MODULE}.manage-units"
MANAGE_ANALYTES = f"{APP_SLUG}.{MODULE}.manage-analytes"
MANAGE_OPTION_SETS = f"{APP_SLUG}.{MODULE}.manage-option-sets"

CanView = Annotated[LeoUser, auth.require_action(VIEW)]
CanCreate = Annotated[LeoUser, auth.require_action(CREATE)]
CanCreateVersion = Annotated[LeoUser, auth.require_action(CREATE_VERSION)]
CanEditVersion = Annotated[LeoUser, auth.require_action(EDIT_VERSION)]
CanPublishVersion = Annotated[LeoUser, auth.require_action(PUBLISH_VERSION)]
CanRetireVersion = Annotated[LeoUser, auth.require_action(RETIRE_VERSION)]
CanEditContent = Annotated[LeoUser, auth.require_action(EDIT_CONTENT)]
CanManageUnits = Annotated[LeoUser, auth.require_action(MANAGE_UNITS)]
CanManageAnalytes = Annotated[LeoUser, auth.require_action(MANAGE_ANALYTES)]
CanManageOptionSets = Annotated[LeoUser, auth.require_action(MANAGE_OPTION_SETS)]
# Dependencias directas: el PATCH exige `edit` y/o `change-status` segun el body.
EDIT_CHECK = auth.require_action(EDIT).dependency
CHANGE_STATUS_CHECK = auth.require_action(CHANGE_STATUS).dependency
