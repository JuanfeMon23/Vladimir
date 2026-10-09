"""Lookup de una version por su id (con su plantilla duena) y filtro
`?status=` del listado de versiones."""

from uuid import uuid4

from httpx import AsyncClient

from app.modules.result_templates.schemas import ResultTemplateVersionRead


async def test_get_result_template_version_by_id_includes_owner(
    client: AsyncClient,
    draft: ResultTemplateVersionRead,
    result_template_payload: dict,
) -> None:
    response = await client.get(f"/api/v1/result-template-versions/{draft.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(draft.id)
    assert body["result_template_id"] == str(draft.result_template_id)
    assert body["owner"] == {
        "id": str(draft.result_template_id),
        "code": result_template_payload["code"],
        "name": result_template_payload["name"],
        "is_active": True,
    }


async def test_get_unknown_result_template_version_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/result-template-versions/{uuid4()}")
    assert response.status_code == 404


async def test_list_result_template_versions_filters_by_status(
    client: AsyncClient, draft: ResultTemplateVersionRead
) -> None:
    url = f"/api/v1/result-templates/{draft.result_template_id}/versions"

    drafts = (await client.get(url, params={"status": "draft"})).json()
    published = (await client.get(url, params={"status": "published"})).json()

    assert [item["id"] for item in drafts["items"]] == [str(draft.id)]
    assert published["total"] == 0
