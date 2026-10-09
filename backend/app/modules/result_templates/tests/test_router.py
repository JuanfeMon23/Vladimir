"""Tests end-to-end (HTTP) del modulo `result_templates`."""

from httpx import AsyncClient


async def test_create_and_get_analyte(
    client: AsyncClient, analyte_payload: dict
) -> None:
    create_response = await client.post("/api/v1/analytes", json=analyte_payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["code"] == analyte_payload["code"]

    get_response = await client.get(f"/api/v1/analytes/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == created["id"]


async def test_create_analyte_duplicate_code_returns_409(
    client: AsyncClient, analyte_payload: dict
) -> None:
    first = await client.post("/api/v1/analytes", json=analyte_payload)
    assert first.status_code == 201

    second = await client.post("/api/v1/analytes", json=analyte_payload)
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_result_option_set_and_options(
    client: AsyncClient, option_set_payload: dict, option_payload: dict
) -> None:
    set_response = await client.post(
        "/api/v1/result-option-sets", json=option_set_payload
    )
    assert set_response.status_code == 201
    option_set_id = set_response.json()["id"]

    option_response = await client.post(
        f"/api/v1/result-option-sets/{option_set_id}/options", json=option_payload
    )
    assert option_response.status_code == 201
    option = option_response.json()
    assert option["option_set_id"] == option_set_id

    patch_response = await client.patch(
        f"/api/v1/result-options/{option['id']}",
        json={"label": "Positivo (confirmado)"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["label"] == "Positivo (confirmado)"

    list_response = await client.get(
        f"/api/v1/result-option-sets/{option_set_id}/options"
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1


async def test_full_result_template_lifecycle_over_http(
    client: AsyncClient,
    result_template_payload: dict,
    result_template_version_payload: dict,
    analyte_payload: dict,
) -> None:
    template_response = await client.post(
        "/api/v1/result-templates", json=result_template_payload
    )
    assert template_response.status_code == 201
    template_id = template_response.json()["id"]

    draft_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions",
        json=result_template_version_payload,
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["version_number"] == 1
    assert draft["status"] == "draft"

    section_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft['id']}/sections",
        json={"name": "Quimica sanguinea", "sort_order": 1},
    )
    assert section_response.status_code == 201
    section = section_response.json()

    analyte_response = await client.post("/api/v1/analytes", json=analyte_payload)
    analyte_id = analyte_response.json()["id"]

    template_analyte_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft['id']}/analytes",
        json={
            "section_id": section["id"],
            "analyte_id": analyte_id,
            "sort_order": 1,
            "result_type": "numeric",
            "unit_id": analyte_payload["default_unit_id"],
            "decimals": 1,
        },
    )
    assert template_analyte_response.status_code == 201
    template_analyte = template_analyte_response.json()

    range_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft['id']}"
        f"/analytes/{template_analyte['id']}/reference-ranges",
        json={"sex": "any", "low": 70, "high": 100},
    )
    assert range_response.status_code == 201

    publish_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft['id']}/publish"
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"

    retire_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft['id']}/retire"
    )
    assert retire_response.status_code == 200
    assert retire_response.json()["status"] == "retired"


async def test_publish_fails_with_incomplete_qualitative_analyte_returns_422(
    client: AsyncClient,
    result_template_payload: dict,
    result_template_version_payload: dict,
    analyte_payload: dict,
) -> None:
    template_response = await client.post(
        "/api/v1/result-templates", json=result_template_payload
    )
    template_id = template_response.json()["id"]

    draft_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions",
        json=result_template_version_payload,
    )
    draft_id = draft_response.json()["id"]

    analyte_response = await client.post("/api/v1/analytes", json=analyte_payload)
    analyte_id = analyte_response.json()["id"]

    await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft_id}/analytes",
        json={
            "analyte_id": analyte_id,
            "sort_order": 1,
            "result_type": "qualitative",
        },
    )

    publish_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft_id}/publish"
    )
    assert publish_response.status_code == 422
    assert publish_response.json()["code"] == "validation_error"
    assert publish_response.json() == {
        "code": "validation_error",
        "message": "La plantilla no se puede publicar: hay analitos con campos faltantes.",
        "details": {
            "missing": [
                {
                    "template_analyte_id": publish_response.json()["details"][
                        "missing"
                    ][0]["template_analyte_id"],
                    "result_type": "qualitative",
                    "missing_fields": ["option_set_id"],
                }
            ],
            "inactive": [],
            "invalid_formula": [],
        },
    }
    # la version sigue en borrador
    version = await client.get(f"/api/v1/result-template-versions/{draft_id}")
    assert version.json()["status"] == "draft"


async def test_edit_section_after_publish_returns_422(
    client: AsyncClient,
    result_template_payload: dict,
    result_template_version_payload: dict,
) -> None:
    template_response = await client.post(
        "/api/v1/result-templates", json=result_template_payload
    )
    template_id = template_response.json()["id"]

    draft_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions",
        json=result_template_version_payload,
    )
    draft_id = draft_response.json()["id"]

    await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft_id}/publish"
    )

    section_response = await client.post(
        f"/api/v1/result-templates/{template_id}/versions/{draft_id}/sections",
        json={"name": "tardia", "sort_order": 1},
    )
    assert section_response.status_code == 422
    assert section_response.json()["code"] == "validation_error"
