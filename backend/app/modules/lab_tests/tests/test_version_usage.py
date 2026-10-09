"""Regla de Versionado "no retirar mientras la usen examenes activos".

`lab_tests` registra en el nucleo (`core.versioning.register_version_usage`)
quien usa cada tabla de versiones; los modulos versionados no conocen
`lab_tests`. Se prueba de punta a punta contra los endpoints `retire` de
`print_labels`, `result_templates` y `consent_documents`.
"""

from httpx import AsyncClient

from app.modules.consent_documents.models import ConsentDocumentVersion
from app.modules.print_labels.models import PrintLabelVersion
from app.modules.result_templates.models import ResultTemplateVersion


async def _create_lab_test(client: AsyncClient, payload: dict, **extra: str) -> dict:
    response = await client.post("/api/v1/lab-tests", json={**payload, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def _assert_in_use(response, codes: list[str], version_id: str) -> None:
    assert response.status_code == 409, response.text
    assert response.json() == {
        "code": "version_in_use",
        "message": (
            "No se puede retirar la versión: la usan exámenes activos "
            f"({', '.join(sorted(codes))})."
        ),
        "details": {"id": version_id, "lab_test_codes": sorted(codes)},
    }


# --- print_labels ---


def _label_retire_url(version: PrintLabelVersion) -> str:
    return f"/api/v1/print-labels/{version.print_label_id}/versions/{version.id}/retire"


async def test_retire_print_label_version_used_by_active_lab_test_returns_409(
    client: AsyncClient,
    lab_test_payload: dict,
    published_print_label_version: PrintLabelVersion,
) -> None:
    lab_test = await _create_lab_test(
        client,
        lab_test_payload,
        print_label_version_id=str(published_print_label_version.id),
    )

    response = await client.post(_label_retire_url(published_print_label_version))

    _assert_in_use(
        response,
        [lab_test["code"]],
        str(published_print_label_version.id),
    )


async def test_retire_print_label_version_used_only_by_inactive_lab_test_succeeds(
    client: AsyncClient,
    lab_test_payload: dict,
    published_print_label_version: PrintLabelVersion,
) -> None:
    lab_test = await _create_lab_test(
        client,
        lab_test_payload,
        print_label_version_id=str(published_print_label_version.id),
    )
    await client.patch(f"/api/v1/lab-tests/{lab_test['id']}", json={"is_active": False})

    response = await client.post(_label_retire_url(published_print_label_version))

    assert response.status_code == 200
    assert response.json()["status"] == "retired"


async def test_retire_unused_print_label_version_succeeds(
    client: AsyncClient, published_print_label_version: PrintLabelVersion
) -> None:
    response = await client.post(_label_retire_url(published_print_label_version))
    assert response.status_code == 200


# --- result_templates ---


async def test_retire_result_template_version_used_by_active_lab_tests_lists_codes(
    client: AsyncClient,
    lab_test_payload: dict,
    published_result_template_version: ResultTemplateVersion,
) -> None:
    version_id = str(published_result_template_version.id)
    first = await _create_lab_test(
        client, lab_test_payload, result_template_version_id=version_id
    )
    second = await _create_lab_test(
        client,
        lab_test_payload,
        code=f"{lab_test_payload['code']}-b",
        result_template_version_id=version_id,
    )

    response = await client.post(
        f"/api/v1/result-templates/{published_result_template_version.result_template_id}"
        f"/versions/{version_id}/retire"
    )

    _assert_in_use(response, [first["code"], second["code"]], version_id)


# --- consent_documents ---


def _document_retire_url(version: ConsentDocumentVersion) -> str:
    return (
        f"/api/v1/consent-documents/{version.consent_document_id}"
        f"/versions/{version.id}/retire"
    )


async def test_retire_consent_document_version_with_active_assignment_returns_409(
    client: AsyncClient,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    lab_test = await _create_lab_test(client, lab_test_payload)
    put = await client.put(
        f"/api/v1/lab-tests/{lab_test['id']}/consent-documents",
        json=[
            {"consent_document_version_id": str(published_consent_document_version.id)}
        ],
    )
    assert put.status_code == 200

    response = await client.post(
        _document_retire_url(published_consent_document_version)
    )

    _assert_in_use(
        response,
        [lab_test["code"]],
        str(published_consent_document_version.id),
    )


async def test_retire_consent_document_version_with_removed_assignment_succeeds(
    client: AsyncClient,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    lab_test = await _create_lab_test(client, lab_test_payload)
    url = f"/api/v1/lab-tests/{lab_test['id']}/consent-documents"
    item = {"consent_document_version_id": str(published_consent_document_version.id)}
    await client.put(url, json=[item])
    await client.put(url, json=[])  # quitar = desactivar la asignacion

    response = await client.post(
        _document_retire_url(published_consent_document_version)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "retired"


async def test_retire_consent_document_version_assigned_to_inactive_lab_test_succeeds(
    client: AsyncClient,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    lab_test = await _create_lab_test(client, lab_test_payload)
    item = {"consent_document_version_id": str(published_consent_document_version.id)}
    await client.put(
        f"/api/v1/lab-tests/{lab_test['id']}/consent-documents", json=[item]
    )
    await client.patch(f"/api/v1/lab-tests/{lab_test['id']}", json={"is_active": False})

    response = await client.post(
        _document_retire_url(published_consent_document_version)
    )

    assert response.status_code == 200
