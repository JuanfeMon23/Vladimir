"""Caracterizacion del ciclo de vida de versiones (`draft -> published ->
retired`) contra los TRES modulos versionados con el MISMO conjunto de
aserciones (status, code, message, details), por HTTP.

Fija el comportamiento observable que comparten `print_labels`,
`consent_documents` y `result_templates` (la implementacion comun vive en
`core/versioning.py`). Las diferencias legitimas de cada modulo son datos de
cada `Case`. El caso "retirar en uso" (409 `version_in_use`) se prueba en
`lab_tests/tests/test_version_usage.py`, que es quien registra los usos.
"""

from dataclasses import dataclass
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response

from app.core.tests.pdf import pdf_base64


@dataclass(frozen=True)
class Case:
    key: str
    base: str  # /api/v1/<padre>
    flat: str  # /api/v1/<x>-versions (lookup por id)
    fk: str  # columna FK al padre (clave de details)
    parent_payload: dict
    first_payload: dict
    missing_text: str  # campos que faltan con body vacio
    parent_noun: str  # "la etiqueta"
    parent_indef: str  # "una etiqueta"
    inactive_adjective: str
    patch_payload: dict
    # Campos que se envian pero la lectura no devuelve (p. ej. un archivo base64).
    write_only: tuple[str, ...] = ()


CASES = [
    Case(
        key="print_labels",
        base="/api/v1/print-labels",
        flat="/api/v1/print-label-versions",
        fk="print_label_id",
        parent_payload={"name": "Etiqueta de tubo"},
        first_payload={
            "width_mm": 40,
            "height_mm": 25,
            "dpi": 203,
            "output_format": "zpl",
            "barcode_type": "code128",
            "copies": 1,
            "template_content": "^XA^FD{{code}}^FS^XZ",
            "placeholders": {"code": "Codigo"},
        },
        missing_text=(
            "width_mm, height_mm, dpi, output_format, copies, "
            "template_content, placeholders"
        ),
        parent_noun="la etiqueta",
        parent_indef="una etiqueta",
        inactive_adjective="inactiva",
        patch_payload={"copies": 3},
    ),
    Case(
        key="consent_documents",
        base="/api/v1/consent-documents",
        flat="/api/v1/consent-document-versions",
        fk="consent_document_id",
        parent_payload={
            "name": "Consentimiento",
            "document_type": "consentimiento_informado",
        },
        first_payload={
            "content": "# Consentimiento",
            "signer": "paciente",
            "file_base64": pdf_base64(),
        },
        write_only=("file_base64",),
        missing_text="content, signer",
        parent_noun="el documento",
        parent_indef="un documento",
        inactive_adjective="inactivo",
        patch_payload={"content": "# Otro texto"},
    ),
    Case(
        key="result_templates",
        base="/api/v1/result-templates",
        flat="/api/v1/result-template-versions",
        fk="result_template_id",
        parent_payload={"name": "Perfil basico"},
        first_payload={"report_settings": {"logo": True}},
        missing_text="report_settings",
        parent_noun="la plantilla",
        parent_indef="una plantilla",
        inactive_adjective="inactiva",
        patch_payload={"report_settings": {"logo": False}},
    ),
]

pytestmark = pytest.mark.parametrize("case", CASES, ids=lambda c: c.key)


async def _parent(client: AsyncClient, case: Case) -> dict:
    code = f"ZZvl-{case.key}-{uuid4().hex[:12]}"
    response = await client.post(case.base, json={"code": code, **case.parent_payload})
    assert response.status_code == 201, response.text
    return response.json()


def _versions_url(case: Case, parent_id: str) -> str:
    return f"{case.base}/{parent_id}/versions"


async def _draft(client: AsyncClient, case: Case, parent_id: str) -> dict:
    response = await client.post(
        _versions_url(case, parent_id), json=case.first_payload
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _publish(client: AsyncClient, case: Case, parent_id: str, vid: str) -> dict:
    response = await client.post(f"{_versions_url(case, parent_id)}/{vid}/publish")
    assert response.status_code == 200, response.text
    return response.json()


def _assert_error(
    response: Response, status: int, code: str, message: str, details: dict
) -> None:
    assert response.status_code == status, response.text
    assert response.json() == {"code": code, "message": message, "details": details}


# --- crear primera version ---


async def test_first_version_without_required_fields_returns_422(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)

    response = await client.post(_versions_url(case, parent["id"]), json={})

    _assert_error(
        response,
        422,
        "validation_error",
        f"Faltan campos obligatorios para crear la primera version: {case.missing_text}.",
        {"missing_fields": case.missing_text.split(", ")},
    )


async def test_first_version_creates_draft_number_one(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)

    response = await client.post(
        _versions_url(case, parent["id"]),
        json={**case.first_payload, "change_notes": "Primera"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version_number"] == 1
    assert body["status"] == "draft"
    assert body["published_at"] is None
    assert body["change_notes"] == "Primera"
    assert body[case.fk] == parent["id"]
    for field, value in case.first_payload.items():
        if field not in case.write_only:
            assert body[field] == value


# --- crear borrador cuando ya hay uno / padre inactivo ---


async def test_second_draft_while_one_is_open_returns_409(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    await _draft(client, case, parent["id"])

    response = await client.post(_versions_url(case, parent["id"]), json={})

    article = case.parent_noun[:1].upper() + case.parent_noun[1:]
    _assert_error(
        response,
        409,
        "conflict",
        f"{article} '{parent['id']}' ya tiene un borrador; "
        "edítalo en vez de crear uno nuevo.",
        {case.fk: parent["id"]},
    )


async def test_draft_after_publish_clones_with_next_number_and_overrides(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    first = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], first["id"])

    response = await client.post(
        _versions_url(case, parent["id"]),
        json={**case.patch_payload, "change_notes": "Segunda"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] != first["id"]
    assert body["version_number"] == 2
    assert body["status"] == "draft"
    assert body["published_at"] is None
    assert body["change_notes"] == "Segunda"
    for field, value in {**case.first_payload, **case.patch_payload}.items():
        if field not in case.write_only:
            assert body[field] == value


async def test_draft_over_inactive_parent_returns_422(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    patch = await client.patch(f"{case.base}/{parent['id']}", json={"is_active": False})
    assert patch.status_code == 200, patch.text

    response = await client.post(
        _versions_url(case, parent["id"]), json=case.first_payload
    )

    _assert_error(
        response,
        422,
        "inactive_reference",
        f"{case.parent_noun[:1].upper() + case.parent_noun[1:]} "
        f"«{parent['code']}» está {case.inactive_adjective}.",
        {case.fk: parent["id"]},
    )


async def test_draft_under_unknown_parent_returns_404(
    client: AsyncClient, case: Case
) -> None:
    unknown = str(uuid4())

    response = await client.post(_versions_url(case, unknown), json=case.first_payload)

    _assert_error(
        response,
        404,
        "not_found",
        f"No existe {case.parent_indef} con id '{unknown}'.",
        {"id": unknown},
    )


# --- editar / publicar / retirar ---


async def test_update_draft_applies_changes(client: AsyncClient, case: Case) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])

    response = await client.patch(
        f"{_versions_url(case, parent['id'])}/{draft['id']}", json=case.patch_payload
    )

    assert response.status_code == 200, response.text
    for field, value in case.patch_payload.items():
        assert response.json()[field] == value


async def test_update_non_draft_version_returns_422(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], draft["id"])

    response = await client.patch(
        f"{_versions_url(case, parent['id'])}/{draft['id']}", json=case.patch_payload
    )

    _assert_error(
        response,
        422,
        "validation_error",
        "Solo se puede editar o publicar una version en borrador "
        "(estado actual: 'published').",
        {"status": "published"},
    )


async def test_publish_draft_sets_status_and_published_at(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])

    published = await _publish(client, case, parent["id"], draft["id"])

    assert published["status"] == "published"
    assert published["published_at"] is not None
    assert published["id"] == draft["id"]


async def test_publish_already_published_returns_422(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], draft["id"])

    response = await client.post(
        f"{_versions_url(case, parent['id'])}/{draft['id']}/publish"
    )

    _assert_error(
        response,
        422,
        "validation_error",
        "Solo se puede editar o publicar una version en borrador "
        "(estado actual: 'published').",
        {"status": "published"},
    )


async def test_retire_published_version_ok(client: AsyncClient, case: Case) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], draft["id"])

    response = await client.post(
        f"{_versions_url(case, parent['id'])}/{draft['id']}/retire"
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "retired"
    assert response.json()["id"] == draft["id"]


async def test_retire_draft_returns_422(client: AsyncClient, case: Case) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])

    response = await client.post(
        f"{_versions_url(case, parent['id'])}/{draft['id']}/retire"
    )

    _assert_error(
        response,
        422,
        "validation_error",
        "Solo se puede retirar una version publicada (estado actual: 'draft').",
        {"status": "draft"},
    )


async def test_draft_after_retire_clones_the_retired_version(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], draft["id"])
    await client.post(f"{_versions_url(case, parent['id'])}/{draft['id']}/retire")

    response = await client.post(_versions_url(case, parent["id"]), json={})

    assert response.status_code == 201, response.text
    assert response.json()["version_number"] == 2
    for field, value in case.first_payload.items():
        if field not in case.write_only:
            assert response.json()[field] == value


# --- 404 de version, listado y lookup por id ---


async def test_version_of_other_parent_or_unknown_returns_404(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    other = await _parent(client, case)
    draft = await _draft(client, case, other["id"])
    unknown = str(uuid4())

    for version_id in (draft["id"], unknown):
        for method, suffix in (
            ("patch", ""),
            ("post", "/publish"),
            ("post", "/retire"),
        ):
            response = await client.request(
                method.upper(),
                f"{_versions_url(case, parent['id'])}/{version_id}{suffix}",
                **({"json": {}} if method == "patch" else {}),
            )
            _assert_error(
                response,
                404,
                "not_found",
                f"No existe una version con id '{version_id}' para "
                f"{case.parent_noun} '{parent['id']}'.",
                {case.fk: parent["id"], "id": version_id},
            )


async def test_list_versions_paginates_newest_first_and_filters_by_status(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    first = await _draft(client, case, parent["id"])
    await _publish(client, case, parent["id"], first["id"])
    second = await client.post(_versions_url(case, parent["id"]), json={})
    assert second.status_code == 201

    everything = await client.get(_versions_url(case, parent["id"]))
    published = await client.get(
        _versions_url(case, parent["id"]), params={"status": "published"}
    )
    page = await client.get(
        _versions_url(case, parent["id"]), params={"page": 2, "page_size": 1}
    )

    body = everything.json()
    assert body["total"] == 2
    assert [v["version_number"] for v in body["items"]] == [2, 1]
    assert [v["id"] for v in published.json()["items"]] == [first["id"]]
    assert published.json()["total"] == 1
    assert [v["version_number"] for v in page.json()["items"]] == [1]
    assert page.json()["total"] == 2
    assert page.json()["page"] == 2


async def test_list_versions_under_unknown_parent_returns_404(
    client: AsyncClient, case: Case
) -> None:
    unknown = str(uuid4())

    response = await client.get(_versions_url(case, unknown))

    _assert_error(
        response,
        404,
        "not_found",
        f"No existe {case.parent_indef} con id '{unknown}'.",
        {"id": unknown},
    )


async def test_get_version_by_id_includes_owner(
    client: AsyncClient, case: Case
) -> None:
    parent = await _parent(client, case)
    draft = await _draft(client, case, parent["id"])

    response = await client.get(f"{case.flat}/{draft['id']}")

    assert response.status_code == 200, response.text
    assert response.json() == {
        **draft,
        "owner": {
            "id": parent["id"],
            "code": parent["code"],
            "name": parent["name"],
            "is_active": True,
        },
    }


async def test_get_unknown_version_by_id_returns_404(
    client: AsyncClient, case: Case
) -> None:
    unknown = str(uuid4())

    response = await client.get(f"{case.flat}/{unknown}")

    subject = {
        "print_labels": "una versión de etiqueta",
        "consent_documents": "una versión de documento",
        "result_templates": "una versión de plantilla",
    }[case.key]
    _assert_error(
        response,
        404,
        "not_found",
        f"No existe {subject} con id '{unknown}'.",
        {"id": unknown},
    )
