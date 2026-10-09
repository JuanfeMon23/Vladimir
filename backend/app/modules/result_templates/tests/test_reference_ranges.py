"""Rangos de referencia: campos segun `result_type`, orden de limites,
opcion esperada del conjunto correcto y no solapamiento."""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.exceptions import ValidationAppError
from app.modules.result_templates import controller
from app.modules.result_templates.exceptions import ReferenceRangeOverlapError
from app.modules.result_templates.models import Unit
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    ReferenceRangeCreate,
    ReferenceRangeUpdate,
    ResultOptionCreate,
    ResultOptionSetCreate,
    ResultOptionUpdate,
    ResultTemplateAnalyteCreate,
    ResultTemplateVersionRead,
)
from app.modules.result_templates.tests.conftest import unique_code


async def _template_analyte(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    result_type: str,
    **fields,
):
    analyte = await controller.create_analyte(
        session, AnalyteCreate(code=unique_code("analyte"), name="Analito")
    )
    return await controller.create_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        ResultTemplateAnalyteCreate(
            analyte_id=analyte.id, sort_order=1, result_type=result_type, **fields
        ),
    )


async def _option_set_with_option(session: AsyncSession):
    option_set = await controller.create_option_set(
        session, ResultOptionSetCreate(code=unique_code("set"), name="Conjunto")
    )
    option = await controller.create_option(
        session,
        option_set.id,
        ResultOptionCreate(code="NR", label="No reactivo", sort_order=1),
    )
    return option_set, option


async def _create(session, draft, template_analyte, **fields):
    return await controller.create_reference_range(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        ReferenceRangeCreate(**fields),
    )


async def _update(session, draft, template_analyte, reference_range, **fields):
    return await controller.update_reference_range(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        reference_range.id,
        ReferenceRangeUpdate(**fields),
    )


# --- orden de limites (espejo de los CHECK de BD) ---


@pytest.mark.parametrize(
    "fields",
    [
        {"low": 10, "high": 5},
        {"critical_low": 6, "low": 5},
        {"high": 10, "critical_high": 9},
        {"age_min": 18, "age_max": 1},
    ],
)
@pytest.mark.parametrize("schema", [ReferenceRangeCreate, ReferenceRangeUpdate])
def test_schema_rejects_inverted_bounds(schema: type, fields: dict) -> None:
    with pytest.raises(ValidationError):
        schema(**fields)


def test_schema_accepts_open_and_equal_bounds() -> None:
    ReferenceRangeCreate(low=None, high=5, critical_low=1)
    ReferenceRangeCreate(low=5, high=5, critical_low=5, critical_high=5)


async def test_update_checks_bounds_against_stored_values(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    reference_range = await _create(session, draft, template_analyte, low=70, high=100)

    with pytest.raises(ValidationAppError) as exc_info:
        await _update(session, draft, template_analyte, reference_range, high=50)
    assert "high" in exc_info.value.details["invalid_bounds"][0]


async def test_http_inverted_bounds_returns_422(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    response = await client.post(
        f"/api/v1/result-templates/{draft.result_template_id}/versions/{draft.id}"
        f"/analytes/{template_analyte.id}/reference-ranges",
        json={"low": 10, "high": 1},
    )
    assert response.status_code == 422


# --- campos permitidos segun result_type ---


@pytest.mark.parametrize(
    ("result_type", "fields"),
    [
        ("qualitative", {"low": 1}),
        ("semi_quantitative", {"critical_high": 1}),
        ("qualitative", {"expected_boolean": True}),
        ("numeric", {"expected_boolean": True}),
        ("calculated", {"expected_boolean": False}),
        ("boolean", {"low": 1}),
        ("text", {"high": 1}),
        ("text", {"expected_boolean": True}),
        ("titer", {"low": 1}),
        ("titer", {"high": 1, "critical_high": 2}),
        ("titer", {"expected_boolean": True}),
    ],
)
async def test_range_fields_must_match_result_type(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    result_type: str,
    fields: dict,
) -> None:
    template_analyte = await _template_analyte(session, draft, result_type)

    with pytest.raises(ValidationAppError) as exc_info:
        await _create(session, draft, template_analyte, **fields)
    assert exc_info.value.details["not_allowed"] == sorted(fields)
    assert exc_info.value.details["result_type"] == result_type


@pytest.mark.parametrize(
    ("result_type", "fields"),
    [
        ("numeric", {"low": 1, "high": 2, "critical_low": 0, "critical_high": 3}),
        ("calculated", {"low": 1}),
        ("boolean", {"expected_boolean": False}),
        ("text", {"display_text": "Ver nota", "interpretation": "Libre"}),
        ("titer", {"display_text": "< 1:40", "interpretation": "Normal"}),
    ],
)
async def test_range_fields_allowed_by_result_type(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    result_type: str,
    fields: dict,
) -> None:
    template_analyte = await _template_analyte(session, draft, result_type)
    created = await _create(session, draft, template_analyte, **fields)
    assert created.is_active is True


async def test_titer_range_accepts_expected_option_of_its_set(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    """`titer` se comporta como `semi_quantitative`: el valor esperado es una
    opcion (dilucion) del conjunto del analito."""
    option_set, option = await _option_set_with_option(session)
    template_analyte = await _template_analyte(
        session, draft, "titer", option_set_id=option_set.id
    )

    created = await _create(
        session, draft, template_analyte, expected_option_id=option.id
    )
    assert created.expected_option_id == option.id


async def test_http_low_on_qualitative_analyte_returns_422(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "qualitative")
    response = await client.post(
        f"/api/v1/result-templates/{draft.result_template_id}/versions/{draft.id}"
        f"/analytes/{template_analyte.id}/reference-ranges",
        json={"low": 1},
    )
    assert response.status_code == 422
    assert response.json()["details"]["not_allowed"] == ["low"]


async def test_update_range_checks_fields_after_merge(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "boolean")
    reference_range = await _create(
        session, draft, template_analyte, expected_boolean=True
    )

    with pytest.raises(ValidationAppError):
        await _update(session, draft, template_analyte, reference_range, low=1)


# --- expected_option_id ---


async def test_expected_option_must_belong_to_template_analyte_set(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    own_set, own_option = await _option_set_with_option(session)
    _, foreign_option = await _option_set_with_option(session)
    template_analyte = await _template_analyte(
        session, draft, "qualitative", option_set_id=own_set.id
    )

    created = await _create(
        session, draft, template_analyte, expected_option_id=own_option.id
    )
    assert created.expected_option_id == own_option.id

    with pytest.raises(ValidationAppError) as exc_info:
        await _create(
            session,
            draft,
            template_analyte,
            sex="male",
            expected_option_id=foreign_option.id,
        )
    assert exc_info.value.code == "invalid_reference"
    assert set(exc_info.value.details) == {"expected_option_id"}


async def test_expected_option_must_be_active(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    option_set, option = await _option_set_with_option(session)
    await controller.update_option(
        session, option.id, ResultOptionUpdate(is_active=False)
    )
    template_analyte = await _template_analyte(
        session, draft, "qualitative", option_set_id=option_set.id
    )

    with pytest.raises(InactiveReferenceError):
        await _create(session, draft, template_analyte, expected_option_id=option.id)


# --- no solapamiento ---


@pytest.mark.parametrize(
    ("first", "second"),
    [
        # `any` solapa con male/female.
        (
            {"sex": "any", "age_min": 0, "age_max": 10, "age_unit": "anos"},
            {"sex": "male", "age_min": 5, "age_max": 20, "age_unit": "anos"},
        ),
        # Sin limite de edad (NULL) = abierto.
        ({"sex": "female"}, {"sex": "female", "age_min": 50, "age_unit": "anos"}),
        (
            {"age_max": 10, "age_unit": "anos"},
            {"age_min": 5, "age_unit": "anos"},
        ),
        # Distinta unidad de edad: 0-12 meses vs 0-2 anos.
        (
            {"age_min": 0, "age_max": 12, "age_unit": "meses"},
            {"age_min": 0, "age_max": 2, "age_unit": "anos"},
        ),
        # Condicion normalizada (espacios y mayusculas).
        ({"condition": " Embarazo T1 "}, {"condition": "embarazo t1"}),
    ],
)
async def test_overlapping_ranges_are_rejected(
    session: AsyncSession, draft: ResultTemplateVersionRead, first: dict, second: dict
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    existing = await _create(session, draft, template_analyte, low=1, high=2, **first)

    with pytest.raises(ReferenceRangeOverlapError) as exc_info:
        await _create(session, draft, template_analyte, low=3, high=4, **second)
    assert exc_info.value.code == "reference_range_overlap"
    assert exc_info.value.status_code == 422
    assert exc_info.value.details == {"overlapping_id": str(existing.id)}


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ({"sex": "male"}, {"sex": "female"}),
        # Intervalos [min, max) contiguos no se solapan.
        (
            {"age_min": 0, "age_max": 1, "age_unit": "anos"},
            {"age_min": 1, "age_max": 18, "age_unit": "anos"},
        ),
        ({"condition": "Embarazo"}, {}),
    ],
)
async def test_non_overlapping_ranges_are_accepted(
    session: AsyncSession, draft: ResultTemplateVersionRead, first: dict, second: dict
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    await _create(session, draft, template_analyte, low=1, high=2, **first)
    await _create(session, draft, template_analyte, low=3, high=4, **second)


async def test_overlap_ignores_inactive_ranges_and_itself(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    old = await _create(session, draft, template_analyte, low=1, high=2)
    await _update(session, draft, template_analyte, old, is_active=False)

    new = await _create(session, draft, template_analyte, low=3, high=4)
    await _update(session, draft, template_analyte, new, high=5)

    with pytest.raises(ReferenceRangeOverlapError):
        await _update(session, draft, template_analyte, old, is_active=True)


async def test_http_overlap_returns_422_reference_range_overlap(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    url = (
        f"/api/v1/result-templates/{draft.result_template_id}/versions/{draft.id}"
        f"/analytes/{template_analyte.id}/reference-ranges"
    )
    await client.post(url, json={"sex": "any", "low": 1, "high": 2})

    response = await client.post(url, json={"sex": "female", "low": 1, "high": 3})

    assert response.status_code == 422
    assert response.json()["code"] == "reference_range_overlap"


async def test_list_ranges_hides_inactive_unless_requested(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    reference_range = await _create(session, draft, template_analyte, low=1, high=2)
    await _update(session, draft, template_analyte, reference_range, is_active=False)
    url = (
        f"/api/v1/result-templates/{draft.result_template_id}/versions/{draft.id}"
        f"/analytes/{template_analyte.id}/reference-ranges"
    )

    assert (await client.get(url)).json() == []
    everything = (await client.get(url, params={"include_inactive": True})).json()
    assert [(r["id"], r["is_active"]) for r in everything] == [
        (str(reference_range.id), False)
    ]
