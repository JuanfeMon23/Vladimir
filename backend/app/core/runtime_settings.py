"""Ajustes editables de Vladimir (tabla `settings`): registro de claves + store.

Las politicas operativas se declaran AQUI y se leen en cada peticion con
`await get("<clave>")` (cache en proceso de ~10 s, invalidada al instante al
editar). Si la BD falla o la fila falta, se usa el default del registro (nunca
un valor fuera de rango). El modulo compartido es `leo_sdk.settings_store`; el
router vive en `app.modules.settings`.

Infraestructura (`DATABASE_URL`, `CORS_ORIGINS`, credenciales de Leo) NO esta
aqui: sigue en variables de entorno (`app.core.config`).
"""

import logging
from typing import Any

from leo_sdk.settings_store import SettingDef, SettingsRegistry, SettingsStore

from app.core.database import AsyncSessionLocal
from app.core.db.settings_model import SETTINGS_MODELS

logger = logging.getLogger("app.settings")

CACHE_TTL_SECONDS = 10.0

VLADIMIR_SETTINGS = SettingsRegistry(
    [
        SettingDef(
            "files.consent_max_mib",
            "int",
            5,
            "Tamaño máximo del PDF de una versión de documento a firmar.",
            min=1,
            max=20,
            unit="MiB",
            group="files",
        ),
        SettingDef(
            "pagination.max_page_size",
            "int",
            200,
            "Máximo de filas por página en los listados.",
            min=50,
            max=500,
            unit="count",
            group="pagination",
        ),
    ]
)

store = SettingsStore(
    VLADIMIR_SETTINGS,
    AsyncSessionLocal,
    SETTINGS_MODELS,
    cache_ttl=CACHE_TTL_SECONDS,
)


async def get(key: str) -> Any:
    """Valor vigente del ajuste (con cache; nunca lanza por la BD)."""
    return await store.get(key)


async def sync_on_startup() -> None:
    """Alinea la tabla con el registro (llamar al arrancar la API). Si la BD no
    responde, la app arranca igual con los defaults (y el fallo queda en el log)."""
    try:
        result = await store.sync_registry({})
    except Exception:
        logger.exception("No se pudo sincronizar la tabla de ajustes al arrancar.")
        return
    if result.inserted or result.updated or result.adjusted:
        logger.info(
            "Ajustes sincronizados: %d nuevos, %d con metadatos actualizados, "
            "%d valores ajustados al rango.",
            len(result.inserted),
            len(result.updated),
            len(result.adjusted),
        )
