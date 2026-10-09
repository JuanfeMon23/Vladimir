"""Tests de `GET /api/v1/activity` (historial de activaciones)."""

from typing import get_args
from uuid import uuid4

from httpx import AsyncClient

from app.core.activity import ACTIVATABLE_TABLES, ActivityEntityType
from app.core.db.registry import Base


def _code() -> str:
    return f"ZZ-act-{uuid4().hex[:20]}"


def test_entity_types_son_las_tablas_con_is_active() -> None:
    activatable = {
        name for name, table in Base.metadata.tables.items() if "is_active" in table.c
    }
    assert set(ACTIVATABLE_TABLES) == activatable
    assert get_args(ActivityEntityType) == ACTIVATABLE_TABLES


async def test_activity_lista_eventos_con_motivo_mas_reciente_primero(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/lab-areas", json={"code": _code(), "name": "Area de prueba"}
    )
    area_id = created.json()["id"]
    await client.patch(
        f"/api/v1/lab-areas/{area_id}",
        json={"is_active": False, "activity_reason": "Cierre temporal"},
    )
    await client.patch(f"/api/v1/lab-areas/{area_id}", json={"is_active": True})

    response = await client.get(
        "/api/v1/activity", params={"entity_type": "lab_areas", "entity_id": area_id}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert [(e["action"], e["reason"]) for e in body["items"]] == [
        ("activated", None),
        ("deactivated", "Cierre temporal"),
        ("activated", None),
    ]
    first = body["items"][0]
    assert first["entity_type"] == "lab_areas"
    assert first["entity_id"] == area_id
    assert set(first) == {
        "id",
        "entity_type",
        "entity_id",
        "action",
        "reason",
        "occurred_at",
    }


async def test_activity_es_paginado(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/lab-areas", json={"code": _code(), "name": "Area de prueba"}
    )
    area_id = created.json()["id"]
    await client.patch(f"/api/v1/lab-areas/{area_id}", json={"is_active": False})

    response = await client.get(
        "/api/v1/activity",
        params={
            "entity_type": "lab_areas",
            "entity_id": area_id,
            "page": 1,
            "page_size": 1,
        },
    )

    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["action"] == "deactivated"


async def test_activity_entity_type_invalido_devuelve_422(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/activity",
        params={"entity_type": "activity_events", "entity_id": str(uuid4())},
    )
    assert response.status_code == 422


async def test_activity_reason_mayor_a_255_devuelve_422(client: AsyncClient) -> None:
    created = await client.post(
        "/api/v1/lab-areas", json={"code": _code(), "name": "Area de prueba"}
    )
    response = await client.patch(
        f"/api/v1/lab-areas/{created.json()['id']}",
        json={"is_active": False, "activity_reason": "x" * 256},
    )
    assert response.status_code == 422
