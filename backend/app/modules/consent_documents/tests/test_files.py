"""Archivo PDF (base64) de las versiones de documentos a firmar, por HTTP:
validacion, hash/tamano calculados, quitar, clonar, publicar exige archivo,
endpoint `/file` y lectura sin `file_base64`."""

import base64
import hashlib
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tests.pdf import MINIMAL_PDF, pdf_base64, pdf_sha256
from app.modules.consent_documents.files import MAX_FILE_BYTES

DOCS = "/api/v1/consent-documents"
VERSIONS = "/api/v1/consent-document-versions"
BODY = {"content": "# Texto", "signer": "paciente"}


async def _document(client: AsyncClient, **extra: object) -> dict:
    response = await client.post(
        DOCS,
        json={
            "code": f"ZZf-{uuid4().hex[:12]}",
            "name": "Consentimiento",
            "document_type": "consentimiento_informado",
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _draft(client: AsyncClient, document_id: str, **extra: object) -> dict:
    response = await client.post(
        f"{DOCS}/{document_id}/versions", json={**BODY, **extra}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _version_url(document_id: str, version_id: str) -> str:
    return f"{DOCS}/{document_id}/versions/{version_id}"


def _assert_file_error(response: Response, reason: str) -> None:
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["details"]["field"] == "file_base64"
    assert body["details"]["reason"] == reason
    assert body["message"]


# --- validacion ---


async def test_create_version_with_file_computes_hash_and_size(
    client: AsyncClient,
) -> None:
    document = await _document(client)

    version = await _draft(client, document["id"], file_base64=pdf_base64())

    assert version["has_file"] is True
    assert version["file_content_type"] == "application/pdf"
    assert version["file_sha256"] == pdf_sha256()
    assert version["file_size_bytes"] == len(MINIMAL_PDF)
    assert "file_base64" not in version


async def test_version_without_file_has_no_file_fields(client: AsyncClient) -> None:
    document = await _document(client)

    version = await _draft(client, document["id"])

    assert version["has_file"] is False
    assert version["file_content_type"] is None
    assert version["file_sha256"] is None
    assert version["file_size_bytes"] is None


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("esto no es base64!", "invalid_base64"),
        ("data:application/pdf;base64," + pdf_base64(), "invalid_base64"),
        ("JVBERi0", "invalid_base64"),  # relleno incorrecto
        ("", "empty"),
        (base64.b64encode(b"GIF89a no es pdf").decode(), "not_pdf"),
        (base64.b64encode(b"  %PDF-1.4").decode(), "not_pdf"),
    ],
)
async def test_invalid_file_returns_422(
    client: AsyncClient, value: str, reason: str
) -> None:
    document = await _document(client)

    response = await client.post(
        f"{DOCS}/{document['id']}/versions", json={**BODY, "file_base64": value}
    )

    _assert_file_error(response, reason)


async def test_file_over_5_mb_returns_422(client: AsyncClient) -> None:
    document = await _document(client)
    big = b"%PDF-" + b"0" * MAX_FILE_BYTES  # 5 MB + 5 bytes

    response = await client.post(
        f"{DOCS}/{document['id']}/versions",
        json={**BODY, "file_base64": base64.b64encode(big).decode()},
    )

    _assert_file_error(response, "too_large")


async def test_file_of_exactly_5_mb_is_accepted(client: AsyncClient) -> None:
    document = await _document(client)
    exact = b"%PDF-" + b"0" * (MAX_FILE_BYTES - 5)

    version = await _draft(
        client, document["id"], file_base64=base64.b64encode(exact).decode()
    )

    assert version["file_size_bytes"] == MAX_FILE_BYTES
    assert version["file_sha256"] == hashlib.sha256(exact).hexdigest()


async def test_client_cannot_set_derived_file_fields(client: AsyncClient) -> None:
    document = await _document(client)

    version = await _draft(
        client,
        document["id"],
        file_base64=pdf_base64(),
        file_sha256="f" * 64,
        file_size_bytes=1,
        file_content_type="text/plain",
    )

    assert version["file_sha256"] == pdf_sha256()
    assert version["file_size_bytes"] == len(MINIMAL_PDF)
    assert version["file_content_type"] == "application/pdf"


# --- editar / quitar ---


async def test_patch_sets_replaces_and_removes_file(client: AsyncClient) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"])
    url = _version_url(document["id"], version["id"])

    added = (await client.patch(url, json={"file_base64": pdf_base64()})).json()
    assert added["has_file"] is True

    other = MINIMAL_PDF + b"% otra version\n"
    replaced = (await client.patch(url, json={"file_base64": pdf_base64(other)})).json()
    assert replaced["file_sha256"] == pdf_sha256(other)
    assert replaced["file_size_bytes"] == len(other)

    untouched = (await client.patch(url, json={"content": "Otro"})).json()
    assert untouched["file_sha256"] == pdf_sha256(other)

    removed = (await client.patch(url, json={"file_base64": None})).json()
    assert removed["has_file"] is False
    assert removed["file_sha256"] is None
    assert removed["file_size_bytes"] is None
    assert removed["file_content_type"] is None
    assert (await client.get(f"{VERSIONS}/{version['id']}/file")).status_code == 404


async def test_patch_with_invalid_file_returns_422(client: AsyncClient) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"], file_base64=pdf_base64())

    response = await client.patch(
        _version_url(document["id"], version["id"]), json={"file_base64": "###"}
    )

    _assert_file_error(response, "invalid_base64")


async def test_cannot_change_file_of_published_version(client: AsyncClient) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"], file_base64=pdf_base64())
    url = _version_url(document["id"], version["id"])
    assert (await client.post(f"{url}/publish")).status_code == 200

    response = await client.patch(url, json={"file_base64": pdf_base64(MINIMAL_PDF)})

    assert response.status_code == 422
    assert response.json()["details"] == {"status": "published"}


async def _clone(client: AsyncClient, document_id: str, body: dict) -> dict:
    response = await client.post(f"{DOCS}/{document_id}/versions", json=body)
    assert response.status_code == 201, response.text
    return response.json()


async def test_cloned_draft_inherits_file_and_can_override_it(
    client: AsyncClient,
) -> None:
    document = await _document(client)
    first = await _draft(client, document["id"], file_base64=pdf_base64())
    url = _version_url(document["id"], first["id"])
    assert (await client.post(f"{url}/publish")).status_code == 200

    clone = await _clone(client, document["id"], {})
    assert clone["has_file"] is True
    assert clone["file_sha256"] == pdf_sha256()
    file = (await client.get(f"{VERSIONS}/{clone['id']}/file")).json()
    assert base64.b64decode(file["base64"]) == MINIMAL_PDF

    other = MINIMAL_PDF + b"% v3\n"
    clone_url = _version_url(document["id"], clone["id"])
    assert (await client.post(f"{clone_url}/publish")).status_code == 200
    third = await _clone(client, document["id"], {"file_base64": pdf_base64(other)})
    assert third["file_sha256"] == pdf_sha256(other)
    third_file = (await client.get(f"{VERSIONS}/{third['id']}/file")).json()
    assert base64.b64decode(third_file["base64"]) == other


# --- publicar ---


async def test_publish_without_file_returns_422_with_missing_field(
    client: AsyncClient,
) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"])

    response = await client.post(
        f"{_version_url(document['id'], version['id'])}/publish"
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "validation_error",
        "message": "Faltan campos obligatorios para publicar la version: file_base64.",
        "details": {"missing_fields": ["file_base64"]},
    }
    detail = await client.get(f"{VERSIONS}/{version['id']}")
    assert detail.json()["status"] == "draft"


async def test_publish_with_file_returns_200(client: AsyncClient) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"], file_base64=pdf_base64())

    response = await client.post(
        f"{_version_url(document['id'], version['id'])}/publish"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "published"
    assert response.json()["has_file"] is True


# --- GET /consent-document-versions/{id}/file ---


async def test_get_version_file(client: AsyncClient) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"], file_base64=pdf_base64())

    response = await client.get(f"{VERSIONS}/{version['id']}/file")

    assert response.status_code == 200
    assert response.json() == {
        "content_type": "application/pdf",
        "sha256": pdf_sha256(),
        "size_bytes": len(MINIMAL_PDF),
        "base64": pdf_base64(),
    }


async def test_get_file_of_unknown_version_returns_404(client: AsyncClient) -> None:
    response = await client.get(f"{VERSIONS}/{uuid4()}/file")

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"
    assert "No existe una versión" in response.json()["message"]


async def test_get_file_of_version_without_file_returns_404(
    client: AsyncClient,
) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"])

    response = await client.get(f"{VERSIONS}/{version['id']}/file")

    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "not_found"
    assert "no tiene archivo" in body["message"]
    assert body["details"] == {"id": version["id"]}


# --- lectura sin file_base64 ---


async def test_reads_never_select_file_base64(
    client: AsyncClient, session: AsyncSession
) -> None:
    document = await _document(client)
    version = await _draft(client, document["id"], file_base64=pdf_base64())
    session.expire_all()  # que las lecturas vayan a la BD de verdad

    statements: list[str] = []

    def capture(conn, cursor, statement, *args) -> None:
        statements.append(statement)

    sync_engine = session.bind.sync_engine  # type: ignore[union-attr]
    event.listen(sync_engine, "before_cursor_execute", capture)
    try:
        listing = await client.get(f"{DOCS}/{document['id']}/versions")
        detail = await client.get(f"{VERSIONS}/{version['id']}")
    finally:
        event.remove(sync_engine, "before_cursor_execute", capture)

    assert listing.status_code == detail.status_code == 200
    assert listing.json()["items"][0]["has_file"] is True
    assert detail.json()["has_file"] is True
    selects = [s for s in statements if "consent_document_versions" in s]
    assert selects
    assert not [s for s in selects if "file_base64" in s]
    assert "file_base64" not in listing.text
    assert "file_base64" not in detail.text
