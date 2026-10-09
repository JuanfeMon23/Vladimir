"""`LabTestPreconditionRead` expone los `*_override` crudos (null si no hay
override) ademas del valor efectivo resuelto."""

from httpx import AsyncClient

from app.modules.preconditions.models import Precondition

OVERRIDE_FIELDS = (
    "name_override",
    "description_override",
    "duration_value_override",
    "duration_unit_override",
    "patient_instructions_override",
)


async def _assign(
    client: AsyncClient, lab_test_payload: dict, item: dict
) -> tuple[str, list[dict]]:
    lab_test_id = (
        await client.post("/api/v1/lab-tests", json=lab_test_payload)
    ).json()["id"]
    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/preconditions", json=[item]
    )
    assert response.status_code == 200
    return lab_test_id, response.json()


async def test_precondition_read_exposes_null_overrides_when_none_set(
    client: AsyncClient, lab_test_payload: dict, precondition: Precondition
) -> None:
    _, body = await _assign(
        client,
        lab_test_payload,
        {"precondition_id": str(precondition.id), "sort_order": 1},
    )

    for field in OVERRIDE_FIELDS:
        assert body[0][field] is None
    assert body[0]["name"] == precondition.name
    assert body[0]["duration_value"] == float(precondition.duration_value)


async def test_precondition_read_exposes_raw_overrides_and_resolved_values(
    client: AsyncClient, lab_test_payload: dict, precondition: Precondition
) -> None:
    lab_test_id, body = await _assign(
        client,
        lab_test_payload,
        {
            "precondition_id": str(precondition.id),
            "sort_order": 1,
            "duration_value_override": 12,
            "duration_unit_override": "horas",
            "patient_instructions_override": "Solo agua.",
        },
    )

    item = body[0]
    assert item["name_override"] is None
    assert item["description_override"] is None
    assert item["duration_value_override"] == 12
    assert item["duration_unit_override"] == "horas"
    assert item["patient_instructions_override"] == "Solo agua."
    assert item["duration_value"] == 12
    assert item["name"] == precondition.name

    # Mismos campos en el GET de la coleccion y en el detalle del examen.
    listed = (
        await client.get(f"/api/v1/lab-tests/{lab_test_id}/preconditions")
    ).json()[0]
    detail = (await client.get(f"/api/v1/lab-tests/{lab_test_id}")).json()
    for source in (listed, detail["preconditions"][0]):
        assert source["duration_value_override"] == 12
        assert source["name_override"] is None
