"""Lookup de una version por su id (con su etiqueta duena) y filtro
`?status=` del listado de versiones."""

from uuid import uuid4

from httpx import AsyncClient


async def _label_with_draft(
    client: AsyncClient, label_payload: dict, version_payload: dict
) -> tuple[dict, dict]:
    label = (await client.post("/api/v1/print-labels", json=label_payload)).json()
    draft = (
        await client.post(
            f"/api/v1/print-labels/{label['id']}/versions", json=version_payload
        )
    ).json()
    return label, draft


async def test_get_print_label_version_by_id_includes_owner(
    client: AsyncClient,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label, draft = await _label_with_draft(
        client, print_label_payload, print_label_version_payload
    )

    response = await client.get(f"/api/v1/print-label-versions/{draft['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == draft["id"]
    assert body["print_label_id"] == label["id"]
    assert body["status"] == "draft"
    assert body["template_content"] == print_label_version_payload["template_content"]
    assert body["owner"] == {
        "id": label["id"],
        "code": label["code"],
        "name": label["name"],
        "is_active": True,
    }


async def test_get_unknown_print_label_version_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/print-label-versions/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_list_print_label_versions_filters_by_status(
    client: AsyncClient,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label, draft = await _label_with_draft(
        client, print_label_payload, print_label_version_payload
    )
    url = f"/api/v1/print-labels/{label['id']}/versions"

    drafts = (await client.get(url, params={"status": "draft"})).json()
    published = (await client.get(url, params={"status": "published"})).json()
    invalid = await client.get(url, params={"status": "otro"})

    assert [item["id"] for item in drafts["items"]] == [draft["id"]]
    assert published["total"] == 0
    assert invalid.status_code == 422
