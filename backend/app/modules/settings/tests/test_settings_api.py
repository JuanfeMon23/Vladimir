"""`/api/v1/settings`: lectura, edicion, historial, permisos y auditoria.

Los ajustes se leen/escriben en la sesion del test (revertida al final).
"""

import dataclasses
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from httpx import AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.conftest import FakeLeo
from app.core import runtime_settings
from app.core.leo import auth, catalog
from app.modules.settings import permissions as p

BASE = "/api/v1/settings"
KEY = "pagination.max_page_size"


@pytest_asyncio.fixture(autouse=True)
async def shared_store(session: AsyncSession) -> AsyncGenerator[None]:
    store = runtime_settings.store
    original = store.session_factory

    @asynccontextmanager
    async def shared() -> AsyncGenerator[AsyncSession]:
        yield session

    store.session_factory = shared
    store.invalidate()
    await store.sync_registry({})
    yield
    store.session_factory = original
    store.invalidate()


async def _put(
    client: AsyncClient, key: str, value: object, version: int = 1
) -> Response:
    return await client.put(
        f"{BASE}/{key}",
        json={
            "value": value,
            "reason": "ajuste de prueba",
            "expected_version": version,
        },
    )


async def test_list_groups_the_declared_settings(client: AsyncClient) -> None:
    response = await client.get(BASE)

    assert response.status_code == 200
    groups = {g["group"]: g["settings"] for g in response.json()["groups"]}
    assert set(groups) == {"files", "pagination"}
    (files,) = groups["files"]
    assert files["key"] == "files.consent_max_mib"
    assert (files["value"], files["default"], files["min"], files["max"]) == (
        5,
        5,
        1,
        20,
    )
    assert files["unit"] == "MiB"


async def test_edit_changes_value_history_and_audits(
    client: AsyncClient, leo: FakeLeo
) -> None:
    response = await _put(client, KEY, 300)

    assert response.status_code == 200
    body = response.json()
    assert (body["value"], body["version"]) == (300, 2)
    assert body["updated_by"] == str(leo.user.id)
    assert body["updated_by_username"] == "tester"
    assert await runtime_settings.get(KEY) == 300  # el cache se invalida al editar

    history = await client.get(f"{BASE}/{KEY}/history")
    entry = history.json()["items"][0]
    assert (entry["old_value"], entry["new_value"]) == (200, 300)
    assert entry["reason"] == "ajuste de prueba"

    event = next(e for e in leo.events if e["action_tag"] == p.UPDATE_EVENT)
    assert event["entity_type"] == "setting"
    assert event["entity_id"] == KEY
    assert event["reason"] == "ajuste de prueba"


async def test_out_of_range_value_is_rejected(client: AsyncClient) -> None:
    response = await _put(client, KEY, 100)

    assert response.status_code == 422
    assert response.json()["code"] == "setting_out_of_range"


async def test_stale_version_conflicts(client: AsyncClient) -> None:
    assert (await _put(client, KEY, 300)).status_code == 200

    response = await _put(client, KEY, 400, version=1)

    assert response.status_code == 409


async def test_unknown_key_returns_404(client: AsyncClient) -> None:
    assert (await _put(client, "nope.key", 1)).status_code == 404


async def test_edit_with_arbitrary_user_uuid_works(
    client: AsyncClient, session: AsyncSession, leo: FakeLeo
) -> None:
    # sin tabla de usuarios: cualquier uuid vale
    leo.user = dataclasses.replace(leo.user, id=uuid.uuid4())

    response = await _put(client, KEY, 300)

    assert response.status_code == 200
    assert response.json()["updated_by"] == str(leo.user.id)
    changed_by = (
        await session.execute(
            text("SELECT changed_by FROM settings_history WHERE setting_key = :k"),
            {"k": KEY},
        )
    ).scalar_one()
    assert changed_by == leo.user.id


@pytest.mark.parametrize(
    ("method", "path", "tag"),
    [
        ("GET", BASE, p.VIEW),
        ("GET", f"{BASE}/{KEY}/history", p.VIEW),
        ("PUT", f"{BASE}/{KEY}", p.EDIT),
    ],
)
async def test_each_route_needs_its_permission(
    client: AsyncClient, leo: FakeLeo, method: str, path: str, tag: str
) -> None:
    body = {"value": 300, "reason": "prueba", "expected_version": 1}
    leo.grant(*(catalog.tags - {tag}))
    assert (await client.request(method, path, json=body)).status_code == 403

    leo.grant(tag)
    assert (await client.request(method, path, json=body)).status_code == 200


async def test_no_session_returns_401(client: AsyncClient, leo: FakeLeo) -> None:
    leo.user = None
    assert (await client.get(BASE)).status_code == 401


def test_catalog_declares_the_module() -> None:
    auth.check_catalog()
    prefix = "vladimir.settings."
    declared = {t for t in catalog.tags if t.startswith(prefix)}
    used = {t for t in auth.used_tags if t.startswith(prefix)}
    assert declared == {p.VIEW, p.EDIT, p.EDIT_SECURITY, p.UPDATE_EVENT}
    # `update` es solo el evento de auditoria: ninguna ruta lo exige.
    assert used == {p.VIEW, p.EDIT, p.EDIT_SECURITY}
    (module,) = [m for m in catalog.to_payload()["modules"] if m["slug"] == "settings"]
    assert module["name"] == "Ajustes"
