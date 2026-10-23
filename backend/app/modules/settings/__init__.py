"""Interfaz publica del modulo `settings` (ajustes editables de Vladimir).

El registro de claves y el store viven en `app.core.runtime_settings`; el
modulo aporta los permisos (`permissions`) y el router `/api/v1/settings`.
"""

from app.modules.settings.router import settings_router

__all__ = ["settings_router"]
