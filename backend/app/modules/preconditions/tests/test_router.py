"""Tests end-to-end (HTTP) del modulo `preconditions`."""

from httpx import AsyncClient

from app.modules.preconditions.tests.conftest import unique_code


async def test_create_and_get_precondition(
    client: AsyncClient, precondition_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/preconditions", json=precondition_payload
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == precondition_payload["code"]
    assert created["kind"] == "precondition"
    assert created["parent_id"] is None
    assert created["items"] == []

    get_response = await client.get(f"/api/v1/preconditions/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_precondition_duplicate_code_returns_409(
    client: AsyncClient, precondition_payload: dict
) -> None:
    first = await client.post("/api/v1/preconditions", json=precondition_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/preconditions", json=precondition_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_get_precondition_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/preconditions/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_item_under_missing_parent_returns_404(
    client: AsyncClient, precondition_item_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/preconditions/00000000-0000-0000-0000-000000000000/items",
        json=precondition_item_payload,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_item_and_grandchild_rejected(
    client: AsyncClient, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    root_response = await client.post(
        "/api/v1/preconditions", json=precondition_payload
    )
    root_id = root_response.json()["id"]

    item_response = await client.post(
        f"/api/v1/preconditions/{root_id}/items", json=precondition_item_payload
    )
    assert item_response.status_code == 201
    item = item_response.json()
    assert item["kind"] == "condition"
    assert item["parent_id"] == root_id

    grandchild_payload = {**precondition_item_payload, "code": unique_code()}
    grandchild_response = await client.post(
        f"/api/v1/preconditions/{item['id']}/items", json=grandchild_payload
    )
    assert grandchild_response.status_code == 422
    assert grandchild_response.json()["code"] == "validation_error"


async def test_list_preconditions_returns_nested_tree(
    client: AsyncClient, precondition_payload: dict, precondition_item_payload: dict
) -> None:
    root_response = await client.post(
        "/api/v1/preconditions", json=precondition_payload
    )
    root_id = root_response.json()["id"]

    item_response = await client.post(
        f"/api/v1/preconditions/{root_id}/items", json=precondition_item_payload
    )
    item_id = item_response.json()["id"]

    list_response = await client.get(
        "/api/v1/preconditions", params={"page": 1, "page_size": 50}
    )
    assert list_response.status_code == 200
    body = list_response.json()

    found = next((p for p in body["items"] if p["id"] == root_id), None)
    assert found is not None
    assert [i["id"] for i in found["items"]] == [item_id]


async def test_update_precondition(
    client: AsyncClient, precondition_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/preconditions", json=precondition_payload
    )
    precondition_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/preconditions/{precondition_id}",
        json={"name": "Ayuno de 12 horas"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Ayuno de 12 horas"


async def test_create_precondition_invalid_enum_returns_422(
    client: AsyncClient, precondition_payload: dict
) -> None:
    """`category` y `duration_unit` se validan en el schema (antes llegaban
    al CHECK de la BD)."""
    for field, value in (("category", "inexistente"), ("duration_unit", "semanas")):
        response = await client.post(
            "/api/v1/preconditions", json={**precondition_payload, field: value}
        )
        assert response.status_code == 422, field
        assert response.json()["detail"][0]["loc"] == ["body", field]
