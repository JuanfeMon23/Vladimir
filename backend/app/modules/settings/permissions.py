"""Catalogo de Leo del modulo `settings` (ajustes editables de Vladimir).

Tags `vladimir.settings.<verbo>`; el catalogo se publica con
`python -m app.core.leo_sync`. `update` NO es un permiso: es el tag del evento
de auditoria de cada cambio de ajuste (se declara para que Leo lo conozca,
igual que `leo.settings.update` en Leo).
"""

from app.core.leo import APP_SLUG, catalog

MODULE = "settings"

catalog.module(
    MODULE, "Ajustes",
    "Políticas operativas de Vladimir editables sin redesplegar.",
)  # fmt: skip
catalog.action(
    MODULE, "view", "Consultar ajustes",
    "Ver los ajustes, sus valores vigentes y su historial de cambios.",
)  # fmt: skip
catalog.action(
    MODULE, "edit", "Editar ajustes", "Modificar el valor de un ajuste."
)  # fmt: skip
catalog.action(
    MODULE, "edit-security", "Editar ajustes de seguridad",
    "Modificar los ajustes marcados como sensibles (además de «Editar ajustes»).",
)  # fmt: skip
catalog.action(
    MODULE, "update", "Evento: ajuste modificado",
    "Evento de auditoría de cada cambio de un ajuste; no se concede.",
)  # fmt: skip

VIEW = f"{APP_SLUG}.{MODULE}.view"
EDIT = f"{APP_SLUG}.{MODULE}.edit"
EDIT_SECURITY = f"{APP_SLUG}.{MODULE}.edit-security"
UPDATE_EVENT = f"{APP_SLUG}.{MODULE}.update"
