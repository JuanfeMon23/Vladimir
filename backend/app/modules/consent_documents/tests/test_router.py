"""Tests end-to-end (HTTP) del modulo `consent_documents`."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import get_category
from app.modules.consent_documents.models import ConsentDocumentType, ConsentSigner


async def test_create_and_get_consent_document(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == consent_document_payload["code"]

    get_response = await client.get(f"/api/v1/consent-documents/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_consent_document_duplicate_code_returns_409(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    first = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_get_consent_document_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/consent-documents/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_update_consent_document(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    create_response = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    document_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/consent-documents/{document_id}",
        json={"name": "Nuevo consentimiento"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["name"] == "Nuevo consentimiento"


async def test_full_version_lifecycle_over_http(
    client: AsyncClient,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document_response = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    document_id = document_response.json()["id"]

    # Crear documento -> primer draft.
    first_draft_response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions",
        json=consent_document_version_payload,
    )
    assert first_draft_response.status_code == 201
    first_draft = first_draft_response.json()
    assert first_draft["version_number"] == 1
    assert first_draft["status"] == "draft"

    # Editar el borrador.
    edit_response = await client.patch(
        f"/api/v1/consent-documents/{document_id}/versions/{first_draft['id']}",
        json={"signer": "paciente_o_representante"},
    )
    assert edit_response.status_code == 200
    assert edit_response.json()["signer"] == "paciente_o_representante"

    # Publicar.
    publish_response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions/{first_draft['id']}/publish"
    )
    assert publish_response.status_code == 200
    published = publish_response.json()
    assert published["status"] == "published"
    assert published["published_at"] is not None

    # Editar una version publicada debe fallar.
    edit_published_response = await client.patch(
        f"/api/v1/consent-documents/{document_id}/versions/{first_draft['id']}",
        json={"signer": "paciente"},
    )
    assert edit_published_response.status_code == 422
    assert edit_published_response.json()["code"] == "validation_error"

    # Crear 2a version clonando la publicada.
    second_draft_response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions",
        json={"change_notes": "segunda version"},
    )
    assert second_draft_response.status_code == 201
    second_draft = second_draft_response.json()
    assert second_draft["version_number"] == 2
    assert second_draft["content"] == consent_document_version_payload["content"]

    # Publicar la 2a version.
    second_publish_response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions/{second_draft['id']}/publish"
    )
    assert second_publish_response.status_code == 200
    assert second_publish_response.json()["status"] == "published"

    # Retirar la 1a version.
    retire_response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions/{first_draft['id']}/retire"
    )
    assert retire_response.status_code == 200
    assert retire_response.json()["status"] == "retired"

    # Listar versiones del documento.
    list_response = await client.get(
        f"/api/v1/consent-documents/{document_id}/versions"
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 2


async def test_create_version_missing_fields_returns_422(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    document_response = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    document_id = document_response.json()["id"]

    response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions",
        json={"change_notes": "incompleta"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_create_second_draft_while_one_open_returns_409(
    client: AsyncClient,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document_response = await client.post(
        "/api/v1/consent-documents", json=consent_document_payload
    )
    document_id = document_response.json()["id"]

    await client.post(
        f"/api/v1/consent-documents/{document_id}/versions",
        json=consent_document_version_payload,
    )

    response = await client.post(
        f"/api/v1/consent-documents/{document_id}/versions",
        json={"change_notes": "duplicado"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


async def _deactivate_category(session: AsyncSession, model: type, code: str) -> None:
    row = await get_category(session, model, code)
    assert row is not None
    row.is_active = False
    await session.flush()


async def test_create_document_with_unknown_type_returns_422(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/consent-documents",
        json={**consent_document_payload, "document_type": "no-existe"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"
    assert response.json()["details"] == {"document_type": "no-existe"}


async def test_create_document_with_inactive_type_returns_422(
    client: AsyncClient, session: AsyncSession, consent_document_payload: dict
) -> None:
    await _deactivate_category(session, ConsentDocumentType, "otro")

    response = await client.post(
        "/api/v1/consent-documents",
        json={**consent_document_payload, "document_type": "otro"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "inactive_reference"


async def test_patch_document_with_unknown_type_returns_422(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    created = (
        await client.post("/api/v1/consent-documents", json=consent_document_payload)
    ).json()

    response = await client.patch(
        f"/api/v1/consent-documents/{created['id']}",
        json={"document_type": "no-existe"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"


async def test_patch_document_keeps_its_inactive_type(
    client: AsyncClient, session: AsyncSession, consent_document_payload: dict
) -> None:
    created = (
        await client.post("/api/v1/consent-documents", json=consent_document_payload)
    ).json()
    await _deactivate_category(session, ConsentDocumentType, "consentimiento_informado")

    response = await client.patch(
        f"/api/v1/consent-documents/{created['id']}",
        json={"name": "Nuevo nombre", "document_type": "consentimiento_informado"},
    )

    assert response.status_code == 200


async def test_create_version_with_unknown_signer_returns_422(
    client: AsyncClient, consent_document_payload: dict
) -> None:
    created = (
        await client.post("/api/v1/consent-documents", json=consent_document_payload)
    ).json()

    response = await client.post(
        f"/api/v1/consent-documents/{created['id']}/versions",
        json={"content": "Texto", "signer": "no-existe"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"
    assert response.json()["details"] == {"signer": "no-existe"}


async def test_patch_version_with_inactive_signer_returns_422(
    client: AsyncClient,
    session: AsyncSession,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    created = (
        await client.post("/api/v1/consent-documents", json=consent_document_payload)
    ).json()
    version = (
        await client.post(
            f"/api/v1/consent-documents/{created['id']}/versions",
            json=consent_document_version_payload,
        )
    ).json()
    await _deactivate_category(session, ConsentSigner, "paciente_o_representante")

    response = await client.patch(
        f"/api/v1/consent-documents/{created['id']}/versions/{version['id']}",
        json={"signer": "paciente_o_representante"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "inactive_reference"
