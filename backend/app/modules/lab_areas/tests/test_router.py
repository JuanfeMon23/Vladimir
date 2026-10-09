"""Tests end-to-end (HTTP) del modulo `lab_areas`."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lab_areas.tests.conftest import unique_code
from app.modules.staff.models import Staff


async def test_create_and_get_lab_area(
    client: AsyncClient, lab_area_payload: dict
) -> None:
    create_response = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == lab_area_payload["code"]
    assert created["is_active"] is True
    assert created["current_manager"] is None

    get_response = await client.get(f"/api/v1/lab-areas/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_lab_area_duplicate_code_returns_409(
    client: AsyncClient, lab_area_payload: dict
) -> None:
    first = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "conflict"
    code = lab_area_payload["code"]
    assert body["message"] == f"Ya existe un área con el código «{code}»."
    assert body["details"] == {"code": code}


async def test_get_lab_area_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/lab-areas/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_list_lab_areas_is_paginated(
    client: AsyncClient, lab_area_payload: dict
) -> None:
    await client.post("/api/v1/lab-areas", json=lab_area_payload)

    response = await client.get(
        "/api/v1/lab-areas", params={"page": 1, "page_size": 10}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] >= 1
    assert isinstance(body["items"], list)


async def test_list_lab_areas_filter_active(
    client: AsyncClient, lab_area_payload: dict
) -> None:
    await client.post("/api/v1/lab-areas", json=lab_area_payload)

    inactive_payload = {**lab_area_payload, "code": unique_code(), "is_active": False}
    await client.post("/api/v1/lab-areas", json=inactive_payload)

    response = await client.get("/api/v1/lab-areas", params={"active": "true"})
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()["items"]}
    assert lab_area_payload["code"] in codes
    assert inactive_payload["code"] not in codes


async def test_update_lab_area(client: AsyncClient, lab_area_payload: dict) -> None:
    create_response = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    area_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/lab-areas/{area_id}", json={"description": "Actualizada"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Actualizada"


async def test_assign_and_change_manager(
    client: AsyncClient,
    lab_area_payload: dict,
    session: AsyncSession,
    active_staff: Staff,
    inactive_staff: Staff,
) -> None:
    inactive_staff.is_active = True
    await session.commit()

    create_response = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    area_id = create_response.json()["id"]

    first_response = await client.put(
        f"/api/v1/lab-areas/{area_id}/manager",
        json={"staff_id": str(active_staff.id)},
    )
    assert first_response.status_code == 200
    assert first_response.json()["staff_id"] == str(active_staff.id)
    assert first_response.json()["end_at"] is None

    area_response = await client.get(f"/api/v1/lab-areas/{area_id}")
    assert area_response.json()["current_manager"]["staff_id"] == str(active_staff.id)

    second_response = await client.put(
        f"/api/v1/lab-areas/{area_id}/manager",
        json={"staff_id": str(inactive_staff.id), "notes": "Cambio de encargado"},
    )
    assert second_response.status_code == 200
    assert second_response.json()["staff_id"] == str(inactive_staff.id)

    history_response = await client.get(f"/api/v1/lab-areas/{area_id}/manager-history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 2
    ended = next(item for item in history if item["staff_id"] == str(active_staff.id))
    current = next(
        item for item in history if item["staff_id"] == str(inactive_staff.id)
    )
    assert ended["end_at"] is not None
    assert current["end_at"] is None


async def test_assign_manager_rejects_inactive_staff_returns_422(
    client: AsyncClient, lab_area_payload: dict, inactive_staff: Staff
) -> None:
    create_response = await client.post("/api/v1/lab-areas", json=lab_area_payload)
    area_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-areas/{area_id}/manager",
        json={"staff_id": str(inactive_staff.id)},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_manager_history_unknown_area_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/lab-areas/00000000-0000-0000-0000-000000000000/manager-history"
    )
    assert response.status_code == 404
