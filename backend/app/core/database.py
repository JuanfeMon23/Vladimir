"""Engine async y sesion por request.

`get_session` es la unica dependencia FastAPI que abre/cierra sesion de BD;
todos los routers de todos los modulos la usan (una sesion por request, ver
AGENTS.md seccion "Transacciones").
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Dependencia FastAPI: una sesion async por request."""
    async with AsyncSessionLocal() as session:
        yield session
