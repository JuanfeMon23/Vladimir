"""Configuracion de la aplicacion, leida desde `backend/.env`.

`Settings` es el unico punto de acceso a variables de entorno; ningun otro
modulo lee `os.environ` directamente.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variables de entorno del backend (todas obligatorias, sin defaults).

    - `DATABASE_URL`: DSN de PostgreSQL (`postgresql+asyncpg://...`).
    - `CORS_ORIGINS`: origenes permitidos, separados por comas.

    Si falta alguna, al cargar `Settings` falla con un error de validacion.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ambas son obligatorias y sin valor por defecto: ningun valor de entorno
    # se graba en el codigo; salen de `backend/.env` (ver `.env.example`).
    database_url: str
    cors_origins: str

    @property
    def cors_origins_list(self) -> list[str]:
        """Origenes CORS permitidos, parseados de la variable separada por comas."""
        return [
            origin.strip() for origin in self.cors_origins.split(",") if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Devuelve `Settings` cacheado (se lee `.env` una sola vez)."""
    return Settings()
