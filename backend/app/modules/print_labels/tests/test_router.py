"""Tests end-to-end (HTTP) del modulo `print_labels`."""

from httpx import AsyncClient


async def test_create_and_get_print_label(
    client: AsyncClient, print_label_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/print-labels", json=print_label_payload
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == print_label_payload["code"]

    get_response = await client.get(f"/api/v1/print-labels/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_print_label_duplicate_code_returns_409(
    client: AsyncClient, print_label_payload: dict
) -> None:
    first = await client.post("/api/v1/print-labels", json=print_label_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/print-labels", json=print_label_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_get_print_label_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/print-labels/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_update_print_label(
    client: AsyncClient, print_label_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/print-labels", json=print_label_payload
    )
    label_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/print-labels/{label_id}", json={"name": "Nueva etiqueta"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Nueva etiqueta"


async def test_full_version_lifecycle_over_http(
    client: AsyncClient,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label_response = await client.post("/api/v1/print-labels", json=print_label_payload)
    label_id = label_response.json()["id"]

    # Crear etiqueta -> primer draft.
    first_draft_response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions", json=print_label_version_payload
    )
    assert first_draft_response.status_code == 201
    first_draft = first_draft_response.json()
    assert first_draft["version_number"] == 1
    assert first_draft["status"] == "draft"

    # Editar el borrador.
    edit_response = await client.patch(
        f"/api/v1/print-labels/{label_id}/versions/{first_draft['id']}",
        json={"copies": 3},
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["copies"] == 3

    # Publicar.
    publish_response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions/{first_draft['id']}/publish"
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["status"] == "published"
    assert published["published_at"] is not None

    # Editar una version publicada debe fallar.
    edit_published_response = await client.patch(
        f"/api/v1/print-labels/{label_id}/versions/{first_draft['id']}",
        json={"copies": 9},
    )
    assert edit_published_response.status_code == 422
    assert edit_published_response.json()["code"] == "validation_error"

    # Crear 2a version clonando la publicada.
    second_draft_response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions",
        json={"change_notes": "segunda version"},
    )
    assert second_draft_response.status_code == 201
    second_draft = second_draft_response.json()
    assert second_draft["version_number"] == 2
    assert (
        second_draft["template_content"]
        == print_label_version_payload["template_content"]
    )

    # Publicar la 2a version.
    second_publish_response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions/{second_draft['id']}/publish"
    )
    assert second_publish_response.status_code == 200
    assert second_publish_response.json()["status"] == "published"

    # Retirar la 1a version.
    retire_response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions/{first_draft['id']}/retire"
    )
    assert retire_response.status_code == 200
    assert retire_response.json()["status"] == "retired"

    # Listar versiones de la etiqueta.
    list_response = await client.get(f"/api/v1/print-labels/{label_id}/versions")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2


async def test_create_version_missing_fields_returns_422(
    client: AsyncClient, print_label_payload: dict
) -> None:
    label_response = await client.post("/api/v1/print-labels", json=print_label_payload)
    label_id = label_response.json()["id"]

    response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions", json={"change_notes": "incompleta"}
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_create_second_draft_while_one_open_returns_409(
    client: AsyncClient,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label_response = await client.post("/api/v1/print-labels", json=print_label_payload)
    label_id = label_response.json()["id"]

    await client.post(
        f"/api/v1/print-labels/{label_id}/versions", json=print_label_version_payload
    )

    response = await client.post(
        f"/api/v1/print-labels/{label_id}/versions", json={"change_notes": "duplicado"}
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
