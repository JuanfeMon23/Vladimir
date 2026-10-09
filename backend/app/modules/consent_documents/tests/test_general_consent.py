"""Consentimiento general de tratamiento de datos: un solo documento activo,
endpoint `/data-treatment/current` y que no se enlaza a examenes."""

import base64
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tests.pdf import MINIMAL_PDF, pdf_base64, pdf_sha256
from app.modules.consent_documents import controller

DOCS = "/api/v1/consent-documents"
GENERAL = "tratamiento_datos"
CONFLICT_CODE = "conflict"

pytestmark = pytest.mark.usefixtures("no_active_general_consent")


async def _document(
    client: AsyncClient,
    document_type: str = GENERAL,
    *,
    is_active: bool = True,
) -> dict:
    response = await client.post(
        DOCS,
        json={
            "code": f"ZZg-{uuid4().hex[:12]}",
            "name": "Tratamiento de datos",
            "document_type": document_type,
            "is_active": is_active,
        },
    )
    return response


async def _created(client: AsyncClient, *args: object, **kwargs: object) -> dict:
    response = await _document(client, *args, **kwargs)  # type: ignore[arg-type]
    assert response.status_code == 201, response.text
    return response.json()


async def _published(client: AsyncClient, document_id: str, pdf: bytes) -> dict:
    created = await client.post(
        f"{DOCS}/{document_id}/versions",
        json={"content": "Texto", "signer": "paciente", "file_base64": pdf_base64(pdf)},
    )
    assert created.status_code == 201, created.text
    version = created.json()
    published = await client.post(
        f"{DOCS}/{document_id}/versions/{version['id']}/publish"
    )
    assert published.status_code == 200, published.text
    return published.json()


# --- un solo general activo ---


async def test_create_second_active_general_returns_409(client: AsyncClient) -> None:
    first = await _created(client)

    response = await _document(client)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == CONFLICT_CODE
    assert body["message"] == (
        f"Ya existe un documento activo de tratamiento de datos personales "
        f"({first['code']}). Desactívalo antes de activar otro."
    )
    assert body["details"] == {"code": first["code"], "id": first["id"]}


async def test_create_inactive_general_is_allowed(client: AsyncClient) -> None:
    await _created(client)

    response = await _document(client, is_active=False)

    assert response.status_code == 201


async def test_other_types_do_not_conflict(client: AsyncClient) -> None:
    await _created(client)

    for document_type in ("consentimiento_informado", "otro"):
        assert (await _document(client, document_type)).status_code == 201


async def test_activate_general_while_another_is_active_returns_409(
    client: AsyncClient,
) -> None:
    first = await _created(client)
    second = await _created(client, is_active=False)

    response = await client.patch(f"{DOCS}/{second['id']}", json={"is_active": True})

    assert response.status_code == 409
    assert response.json()["details"] == {"code": first["code"], "id": first["id"]}


async def test_change_type_to_general_while_another_is_active_returns_409(
    client: AsyncClient,
) -> None:
    first = await _created(client)
    other = await _created(client, "consentimiento_informado")

    response = await client.patch(
        f"{DOCS}/{other['id']}", json={"document_type": GENERAL}
    )

    assert response.status_code == 409
    assert response.json()["details"]["id"] == first["id"]


async def test_deactivate_then_activate_another_general_works(
    client: AsyncClient,
) -> None:
    first = await _created(client)
    second = await _created(client, is_active=False)

    off = await client.patch(f"{DOCS}/{first['id']}", json={"is_active": False})
    on = await client.patch(f"{DOCS}/{second['id']}", json={"is_active": True})

    assert off.status_code == 200
    assert on.status_code == 200


async def test_patching_the_active_general_itself_does_not_conflict(
    client: AsyncClient,
) -> None:
    first = await _created(client)

    response = await client.patch(
        f"{DOCS}/{first['id']}", json={"name": "Otro nombre", "document_type": GENERAL}
    )

    assert response.status_code == 200


async def test_integrity_error_of_unique_index_becomes_409(
    client: AsyncClient,
    session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Red de seguridad: si la comprobacion previa no ve al existente (carrera),
    el indice unico de la BD se traduce al mismo 409, sin 500."""
    first = await _created(client)

    async def blind(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(controller, "_ensure_single_general", blind)

    response = await _document(client)

    assert response.status_code == 409
    assert response.json()["code"] == CONFLICT_CODE
    assert response.json()["details"] == {"code": first["code"], "id": first["id"]}
    # La sesion sigue usable tras el rollback del savepoint.
    again = await client.get(f"{DOCS}/{first['id']}")
    assert again.status_code == 200


async def test_integrity_error_on_update_becomes_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = await _created(client)
    second = await _created(client, is_active=False)

    async def blind(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr(controller, "_ensure_single_general", blind)

    response = await client.patch(f"{DOCS}/{second['id']}", json={"is_active": True})

    assert response.status_code == 409
    assert response.json()["details"] == {"code": first["code"], "id": first["id"]}


# --- GET /data-treatment/current ---


async def test_current_returns_active_general_with_latest_published_file(
    client: AsyncClient,
) -> None:
    document = await _created(client)
    await _published(client, document["id"], MINIMAL_PDF)
    newer_pdf = MINIMAL_PDF + b"% version 2\n"
    second = await client.post(f"{DOCS}/{document['id']}/versions", json={})
    assert second.status_code == 201
    patched = await client.patch(
        f"{DOCS}/{document['id']}/versions/{second.json()['id']}",
        json={"file_base64": pdf_base64(newer_pdf)},
    )
    assert patched.status_code == 200
    await client.post(f"{DOCS}/{document['id']}/versions/{second.json()['id']}/publish")
    # Un tercer borrador no cuenta: solo la ultima PUBLICADA.
    await client.post(f"{DOCS}/{document['id']}/versions", json={})

    response = await client.get(f"{DOCS}/data-treatment/current")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["document"]["id"] == document["id"]
    assert body["document"]["document_type"] == GENERAL
    assert body["version"]["version_number"] == 2
    assert body["version"]["status"] == "published"
    assert body["version"]["has_file"] is True
    assert "file_base64" not in body["version"]
    file = body["file"]
    assert file["content_type"] == "application/pdf"
    assert file["sha256"] == pdf_sha256(newer_pdf)
    assert file["size_bytes"] == len(newer_pdf)
    assert base64.b64decode(file["base64"]) == newer_pdf


async def test_current_without_active_general_returns_404(
    client: AsyncClient,
) -> None:
    document = await _created(client)
    await _published(client, document["id"], MINIMAL_PDF)
    await client.patch(f"{DOCS}/{document['id']}", json={"is_active": False})

    response = await client.get(f"{DOCS}/data-treatment/current")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_current_without_published_version_returns_404(
    client: AsyncClient,
) -> None:
    document = await _created(client)
    await client.post(
        f"{DOCS}/{document['id']}/versions",
        json={"content": "Texto", "signer": "paciente"},
    )

    response = await client.get(f"{DOCS}/data-treatment/current")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert response.json()["message"] != ""


async def test_current_is_not_captured_by_the_uuid_route(client: AsyncClient) -> None:
    response = await client.get(f"{DOCS}/data-treatment/current")

    assert response.status_code != 422
