"""Tests end-to-end (HTTP) del modulo `samples`."""

from httpx import AsyncClient

from app.modules.samples.tests.conftest import unique_code


async def test_create_and_get_sample(client: AsyncClient, sample_payload: dict) -> None:
    create_response = await client.post("/api/v1/samples", json=sample_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == sample_payload["code"]
    assert created["types"] == []

    get_response = await client.get(f"/api/v1/samples/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_sample_duplicate_code_returns_409(
    client: AsyncClient, sample_payload: dict
) -> None:
    first = await client.post("/api/v1/samples", json=sample_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/samples", json=sample_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_get_sample_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/samples/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_sample_type_under_missing_sample_returns_404(
    client: AsyncClient, sample_type_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/samples/00000000-0000-0000-0000-000000000000/types",
        json=sample_type_payload,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_sample_type_and_list_nested(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    type_response = await client.post(
        f"/api/v1/samples/{sample_id}/types", json=sample_type_payload
    )
    assert type_response.status_code == 201
    sample_type = type_response.json()
    assert sample_type["sample_id"] == sample_id

    list_response = await client.get(
        "/api/v1/samples", params={"page": 1, "page_size": 50}
    )
    assert list_response.status_code == 200
    body = list_response.json()

    found = next((s for s in body["items"] if s["id"] == sample_id), None)
    assert found is not None
    assert [t["id"] for t in found["types"]] == [sample_type["id"]]


async def test_list_types_of_sample(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    await client.post(f"/api/v1/samples/{sample_id}/types", json=sample_type_payload)

    list_response = await client.get(f"/api/v1/samples/{sample_id}/types")
    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] == 1
    assert body["items"][0]["code"] == sample_type_payload["code"]


async def test_update_sample(client: AsyncClient, sample_payload: dict) -> None:
    create_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/samples/{sample_id}", json={"name": "Sangre venosa"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Sangre venosa"


async def test_update_sample_type_directly(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    type_response = await client.post(
        f"/api/v1/samples/{sample_id}/types", json=sample_type_payload
    )
    sample_type_id = type_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/sample-types/{sample_type_id}", json={"name": "Tubo tapa lila"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Tubo tapa lila"
    assert patch_response.json()["sample_id"] == sample_id


async def test_update_sample_type_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/sample-types/00000000-0000-0000-0000-000000000000",
        json={"name": "x"},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_create_sample_type_duplicate_code_returns_409(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    first = await client.post(
        f"/api/v1/samples/{sample_id}/types", json=sample_type_payload
    )
    assert first.status_code == 201

    other_payload = {**sample_type_payload, "code": sample_type_payload["code"]}
    second = await client.post(f"/api/v1/samples/{sample_id}/types", json=other_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_update_sample_type_duplicate_code_returns_409(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    first_response = await client.post(
        f"/api/v1/samples/{sample_id}/types", json=sample_type_payload
    )
    first_code = first_response.json()["code"]

    other_payload = {**sample_type_payload, "code": unique_code()}
    second_response = await client.post(
        f"/api/v1/samples/{sample_id}/types", json=other_payload
    )
    second_id = second_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/sample-types/{second_id}", json={"code": first_code}
    )
    assert patch_response.status_code == 409
    assert patch_response.json()["code"] == "conflict"


async def test_create_sample_type_invalid_specimen_returns_422(
    client: AsyncClient, sample_payload: dict, sample_type_payload: dict
) -> None:
    sample_response = await client.post("/api/v1/samples", json=sample_payload)
    sample_id = sample_response.json()["id"]

    response = await client.post(
        f"/api/v1/samples/{sample_id}/types",
        json={**sample_type_payload, "specimen": "saliva"},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "specimen"]
