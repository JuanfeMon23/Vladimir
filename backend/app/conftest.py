"""Fixtures compartidas por los tests de todo el backend (nucleo y modulos).

- `session`: BD real local dentro de una transaccion externa que se revierte
  al final del test (savepoint anidado para sobrevivir a los `commit()` de
  los repositories). No hace falta mockear la BD ni limpiar datos a mano.
- `client`: cliente HTTP (httpx + ASGI) contra la app, con `get_session`
  reemplazada por la sesion del test (mismo aislamiento por rollback).

Los `conftest.py` de cada modulo solo agregan sus payloads/fixtures de
dominio; no redefinen estas.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import engine
from app.core.database import get_session as real_get_session
from app.main import app


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession]:
    async with engine.connect() as connection:
        outer_transaction = await connection.begin()
        test_sessionmaker = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with test_sessionmaker() as test_session:
            yield test_session
        await outer_transaction.rollback()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[real_get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def no_active_general_consent(session: AsyncSession) -> None:
    """Desactiva (dentro de la transaccion del test, que se revierte) el
    consentimiento general `tratamiento_datos` que haya en la BD de
    desarrollo: solo puede haber uno activo, y los tests crean el suyo."""
    await session.execute(
        text(
            "UPDATE consent_documents SET is_active = false "
            "WHERE document_type = 'tratamiento_datos' AND is_active"
        )
    )
