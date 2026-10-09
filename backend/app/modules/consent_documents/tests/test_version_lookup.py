"""Lookup de una version por su id (con su documento dueno) y filtro
`?status=` del listado de versiones."""

from uuid import uuid4

from httpx import AsyncClient


async def _document_with_draft(
    client: AsyncClient, document_payload: dict, version_payload: dict
) -> tuple[dict, dict]:
    document = (
        await client.post("/api/v1/consent-documents", json=document_payload)
    ).json()
    draft = (
        await client.post(
            f"/api/v1/consent-documents/{document['id']}/versions",
            json=version_payload,
        )
    ).json()
    return document, draft


async def test_get_consent_document_version_by_id_includes_owner(
    client: AsyncClient,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document, draft = await _document_with_draft(
        client, consent_document_payload, consent_document_version_payload
    )

    response = await client.get(f"/api/v1/consent-document-versions/{draft['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == draft["id"]
    assert body["consent_document_id"] == document["id"]
    assert body["owner"] == {
        "id": document["id"],
        "code": document["code"],
        "name": document["name"],
        "is_active": True,
    }


async def test_get_unknown_consent_document_version_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get(f"/api/v1/consent-document-versions/{uuid4()}")
    assert response.status_code == 404


async def test_list_consent_document_versions_filters_by_status(
    client: AsyncClient,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document, draft = await _document_with_draft(
        client, consent_document_payload, consent_document_version_payload
    )
    url = f"/api/v1/consent-documents/{document['id']}/versions"

    drafts = (await client.get(url, params={"status": "draft"})).json()
    retired = (await client.get(url, params={"status": "retired"})).json()

    assert [item["id"] for item in drafts["items"]] == [draft["id"]]
    assert retired["total"] == 0
