"""Registro de ajustes de Vladimir y su consumo por peticion."""

import pytest
from httpx import AsyncClient

from app.core import runtime_settings
from app.core.runtime_settings import VLADIMIR_SETTINGS


def test_registry_declares_the_operational_policies() -> None:
    files = VLADIMIR_SETTINGS.get("files.consent_max_mib")
    assert (files.default, files.min, files.max, files.unit) == (5, 1, 20, "MiB")
    page = VLADIMIR_SETTINGS.get("pagination.max_page_size")
    assert (page.default, page.min, page.max) == (200, 200, 500)
    assert "Incubus" in page.description
    assert not any(d.requires_security for d in VLADIMIR_SETTINGS)


async def test_page_size_limit_follows_the_setting(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def fake_get(key: str) -> int:
        return 250

    monkeypatch.setattr(runtime_settings, "get", fake_get)

    over = await client.get("/api/v1/lab-areas", params={"page_size": 251})
    ok = await client.get("/api/v1/lab-areas", params={"page_size": 250})

    assert over.status_code == 422
    assert over.json() == {
        "code": "validation_error",
        "message": "El tamaño de página máximo permitido es 250.",
        "details": {"field": "page_size", "max": 250},
    }
    assert ok.status_code == 200


async def test_page_size_default_limit_is_200(client: AsyncClient) -> None:
    over = await client.get("/api/v1/lab-areas", params={"page_size": 201})
    ok = await client.get("/api/v1/lab-areas", params={"page_size": 200})

    assert over.status_code == 422
    assert ok.status_code == 200
