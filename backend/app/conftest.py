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
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from leo_sdk import LeoError, LeoUnavailableError, LeoUser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import engine
from app.core.database import get_session as real_get_session
from app.core.leo import auth, catalog
from app.main import app


@dataclass
class FakeLeo:
    """Doble de Leo para los tests: usuario actual y eventos de auditoria.

    `user=None` -> sin sesion (401). Por defecto el usuario tiene TODOS los tags
    del catalogo; usar `grant(*tags)` para dar solo algunos. `down=True` simula
    Leo caido al auditar.
    """

    user: LeoUser | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    down: bool = False

    def grant(self, *tags: str) -> None:
        self.user = make_leo_user(tags)


def make_leo_user(tags: Any) -> LeoUser:
    return LeoUser(
        id=uuid4(),
        username="tester",
        name="Tester",
        email="tester@example.com",
        permissions=frozenset(tags),
        session_id=uuid4(),
        access_token="token-falso",
        jkt="jkt-falso",
    )


@pytest.fixture
def leo(monkeypatch: pytest.MonkeyPatch) -> FakeLeo:
    fake = FakeLeo(user=make_leo_user(catalog.tags))

    async def ingest_audit(payload: dict[str, Any]) -> None:
        if fake.down:
            raise LeoUnavailableError("down")
        fake.events.append(payload)

    monkeypatch.setattr(auth.client, "ingest_audit", ingest_audit)
    auth.audit._queue.clear()
    return fake


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
async def client(session: AsyncSession, leo: FakeLeo) -> AsyncGenerator[AsyncClient]:
    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield session

    async def override_current_user() -> LeoUser:
        if leo.user is None:
            raise LeoError("not_authenticated", "Inicia sesión para continuar.", 401)
        return leo.user

    app.dependency_overrides[real_get_session] = override_get_session
    app.dependency_overrides[auth.current_user] = override_current_user
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
