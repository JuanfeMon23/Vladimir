"""Tests end-to-end (HTTP) del modulo `lab_tests`."""

from httpx import AsyncClient

from app.modules.consent_documents.models import ConsentDocumentVersion
from app.modules.lab_areas.models import LabArea
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabelVersion
from app.modules.samples.models import SampleType


async def test_create_and_get_lab_test(
    client: AsyncClient, lab_test_payload: dict
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == lab_test_payload["code"]
    assert created["is_active"] is True
    assert created["preconditions"] == []
    assert [st["sample_type_id"] for st in created["sample_types"]] == [
        lab_test_payload["sample_types"][0]["sample_type_id"]
    ]
    assert created["sample_types"][0]["is_preferred"] is True
    assert created["consent_documents"] == []

    get_response = await client.get(f"/api/v1/lab-tests/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_lab_test_without_sample_types_returns_422(
    client: AsyncClient, lab_test_payload: dict
) -> None:
    payload = {k: v for k, v in lab_test_payload.items() if k != "sample_types"}

    response = await client.post("/api/v1/lab-tests", json=payload)
    assert response.status_code == 422


async def test_create_lab_test_with_empty_sample_types_returns_422_message(
    client: AsyncClient, lab_test_payload: dict
) -> None:
    response = await client.post(
        "/api/v1/lab-tests", json={**lab_test_payload, "sample_types": []}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == "El examen debe tener al menos un tipo de muestra."


async def test_create_lab_test_with_two_preferred_returns_422_and_creates_nothing(
    client: AsyncClient,
    lab_test_payload: dict,
    sample_type: SampleType,
    other_sample_type: SampleType,
) -> None:
    payload = {
        **lab_test_payload,
        "sample_types": [
            {
                "sample_type_id": str(sample_type.id),
                "is_preferred": True,
                "sort_order": 1,
            },
            {
                "sample_type_id": str(other_sample_type.id),
                "is_preferred": True,
                "sort_order": 2,
            },
        ],
    }

    response = await client.post("/api/v1/lab-tests", json=payload)
    assert response.status_code == 422
    assert response.json()["details"] == {"preferred_count": 2}

    listing = await client.get("/api/v1/lab-tests", params={"page_size": 200})
    assert payload["code"] not in {i["code"] for i in listing.json()["items"]}


async def test_create_lab_test_duplicate_code_returns_409(
    client: AsyncClient, lab_test_payload: dict
) -> None:
    first = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_get_lab_test_not_found_returns_404(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/lab-tests/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_list_lab_tests_is_paginated_and_filters_by_area(
    client: AsyncClient, lab_test_payload: dict, lab_area: LabArea
) -> None:
    await client.post("/api/v1/lab-tests", json=lab_test_payload)

    response = await client.get(
        "/api/v1/lab-tests",
        params={"page": 1, "page_size": 10, "area_id": str(lab_area.id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["total"] >= 1
    codes = {item["code"] for item in body["items"]}
    assert lab_test_payload["code"] in codes


async def test_update_lab_test(client: AsyncClient, lab_test_payload: dict) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"/api/v1/lab-tests/{lab_test_id}", json={"description": "Actualizado"}
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Actualizado"


async def test_create_lab_test_rejects_unpublished_print_label_version(
    client: AsyncClient,
    lab_test_payload: dict,
    draft_print_label_version: PrintLabelVersion,
) -> None:
    payload = {
        **lab_test_payload,
        "print_label_version_id": str(draft_print_label_version.id),
    }

    response = await client.post("/api/v1/lab-tests", json=payload)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_create_lab_test_accepts_published_print_label_version(
    client: AsyncClient,
    lab_test_payload: dict,
    published_print_label_version: PrintLabelVersion,
) -> None:
    payload = {
        **lab_test_payload,
        "print_label_version_id": str(published_print_label_version.id),
    }

    response = await client.post("/api/v1/lab-tests", json=payload)
    assert response.status_code == 201
    assert response.json()["print_label_version_id"] == str(
        published_print_label_version.id
    )


async def test_set_preconditions_with_and_without_override(
    client: AsyncClient, lab_test_payload: dict, precondition: Precondition
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    put_response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/preconditions",
        json=[
            {
                "precondition_id": str(precondition.id),
                "is_mandatory": True,
                "sort_order": 1,
                "name_override": "Ayuno estricto",
            }
        ],
    )
    assert put_response.status_code == 200
    body = put_response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Ayuno estricto"
    assert body[0]["duration_unit"] == precondition.duration_unit

    get_response = await client.get(f"/api/v1/lab-tests/{lab_test_id}/preconditions")
    assert get_response.status_code == 200
    assert get_response.json()[0]["name"] == "Ayuno estricto"


async def test_set_sample_types_fails_without_preferred(
    client: AsyncClient, lab_test_payload: dict, sample_type: SampleType
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/sample-types",
        json=[
            {
                "sample_type_id": str(sample_type.id),
                "is_preferred": False,
                "sort_order": 1,
            }
        ],
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_set_sample_types_fails_with_two_preferred(
    client: AsyncClient,
    lab_test_payload: dict,
    sample_type: SampleType,
    other_sample_type: SampleType,
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/sample-types",
        json=[
            {
                "sample_type_id": str(sample_type.id),
                "is_preferred": True,
                "sort_order": 1,
            },
            {
                "sample_type_id": str(other_sample_type.id),
                "is_preferred": True,
                "sort_order": 2,
            },
        ],
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_set_sample_types_fails_with_empty_list(
    client: AsyncClient, lab_test_payload: dict
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/sample-types", json=[]
    )
    assert response.status_code == 422
    assert response.json()["message"] == (
        "El examen debe tener al menos un tipo de muestra."
    )

    kept = await client.get(f"/api/v1/lab-tests/{lab_test_id}/sample-types")
    assert len(kept.json()) == 1


async def test_set_sample_types_succeeds_with_one_preferred(
    client: AsyncClient, lab_test_payload: dict, sample_type: SampleType
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/sample-types",
        json=[
            {
                "sample_type_id": str(sample_type.id),
                "is_preferred": True,
                "required_volume_ml": 5,
                "sort_order": 1,
            }
        ],
    )
    assert response.status_code == 200
    assert response.json()[0]["is_preferred"] is True


async def test_set_consent_documents_rejects_unpublished_version(
    client: AsyncClient,
    lab_test_payload: dict,
    draft_consent_document_version: ConsentDocumentVersion,
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/consent-documents",
        json=[{"consent_document_version_id": str(draft_consent_document_version.id)}],
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_set_consent_documents_accepts_published_version(
    client: AsyncClient,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    create_response = await client.post("/api/v1/lab-tests", json=lab_test_payload)
    lab_test_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/consent-documents",
        json=[
            {"consent_document_version_id": str(published_consent_document_version.id)}
        ],
    )
    assert response.status_code == 200
    assert response.json()[0]["consent_document_version_id"] == str(
        published_consent_document_version.id
    )

    detail_response = await client.get(f"/api/v1/lab-tests/{lab_test_id}")
    assert len(detail_response.json()["consent_documents"]) == 1
