"""Tests end-to-end (HTTP) del modulo `staff`."""

from httpx import AsyncClient

from app.modules.staff.tests.conftest import unique_document_number


async def test_create_and_get_staff(client: AsyncClient, staff_payload: dict) -> None:
    create_response = await client.post("/api/v1/staff", json=staff_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["document_number"] == staff_payload["document_number"]
    assert created["is_active"] is True

    get_response = await client.get(f"/api/v1/staff/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_staff_duplicate_document_number_returns_409(
    client: AsyncClient, staff_payload: dict
) -> None:
    first = await client.post("/api/v1/staff", json=staff_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/staff", json=staff_payload)
    assert second.status_code == 409
    body = second.json()
    assert body["code"] == "conflict"
    number = staff_payload["document_number"]
    assert body["message"] == (
        f"Ya existe personal con el número de documento «{number}»."
    )
    assert body["details"] == {"document_number": number}


async def test_create_staff_too_long_field_returns_422(
    client: AsyncClient, staff_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/staff", json={**staff_payload, "first_name": "x" * 101}
    )
    assert response.status_code == 422


async def test_get_staff_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/staff/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_list_staff_is_paginated(
    client: AsyncClient, staff_payload: dict
) -> None:
    await client.post("/api/v1/staff", json=staff_payload)

    response = await client.get("/api/v1/staff", params={"page": 1, "page_size": 10})
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] >= 1
    assert isinstance(body["items"], list)


async def test_list_staff_filter_active(
    client: AsyncClient, staff_payload: dict
) -> None:
    await client.post("/api/v1/staff", json=staff_payload)

    inactive_payload = {
        **staff_payload,
        "document_number": unique_document_number(),
        "is_active": False,
    }
    await client.post("/api/v1/staff", json=inactive_payload)

    response = await client.get("/api/v1/staff", params={"active": "true"})
    assert response.status_code == 200
    document_numbers = {item["document_number"] for item in response.json()["items"]}
    assert staff_payload["document_number"] in document_numbers
    assert inactive_payload["document_number"] not in document_numbers


async def test_update_staff(client: AsyncClient, staff_payload: dict) -> None:
    create_response = await client.post("/api/v1/staff", json=staff_payload)
    staff_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/staff/{staff_id}", json={"job_title": "Coordinadora"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["job_title"] == "Coordinadora"
