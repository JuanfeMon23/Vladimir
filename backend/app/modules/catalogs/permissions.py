"""Catalogo de Leo y dependencias de permiso del modulo `catalogs`.

Tags `vladimir.catalogs.<verbo>`; un solo juego de permisos cubre los 9
catalogos de categoria. `view` es el que se concede al rol de servicio de
otras apps (p. ej. `catalogo-lectura` de Incubus). El catalogo se publica con
`python -m app.core.leo_sync`.
"""

from typing import Annotated

from leo_sdk import LeoUser

from app.core.leo import APP_SLUG, auth, catalog

MODULE = "catalogs"

catalog.module(
    MODULE,
    "Catálogos de categoría",
    "Listas de categoría (unidades, tipos de resultado, sexos...) que usan los módulos.",
)
catalog.action(
    MODULE, "view", "Consultar catálogos de categoría",
    "Listar los catálogos de categoría con sus columnas de comportamiento.",
)  # fmt: skip
catalog.action(
    MODULE, "create", "Crear elementos de catálogos de categoría",
    "Agregar un elemento a un catálogo de categoría.",
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar elementos de catálogos de categoría",
    "Modificar nombre, orden y columnas de comportamiento.",
)  # fmt: skip
catalog.action(
    MODULE, "change-status", "Activar o desactivar elementos de catálogos de categoría",
    "Desactivar un elemento de catálogo o reactivarlo.",
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
