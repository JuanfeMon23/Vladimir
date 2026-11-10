"""Tipos de resultado, sexos y unidades de edad vienen de BD: validacion 422 de
la referencia y comportamiento por banderas (`result_types.uses_*`,
`sexes.is_wildcard`, `age_units.days`) sin listas en el codigo."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.categories import get_category
from app.core.exceptions import InvalidReferenceError, ValidationAppError
from app.modules.result_templates import controller
from app.modules.result_templates.exceptions import (
    ReferenceRangeOverlapError,
    ResultTemplateVersionIncompleteError,
)
from app.modules.result_templates.models import AgeUnit, ResultType, Sex
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    ReferenceRangeCreate,
    ResultTemplateAnalyteCreate,
    ResultTemplateAnalyteUpdate,
    ResultTemplateVersionRead,
)
from app.modules.result_templates.tests.conftest import unique_code


async def _template_analyte(
    session: AsyncSession, draft: ResultTemplateVersionRead, result_type: str, **fields
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


async def _create_range(session, draft, template_analyte, **fields):
    return await controller.create_reference_range(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        ReferenceRangeCreate(**fields),
    )


async def _set(session: AsyncSession, model: type, code: str, **columns) -> None:
    row = await get_category(session, model, code)
    assert row is not None
    for column, value in columns.items():
        setattr(row, column, value)
    await session.flush()


# --- referencia a catalogo: existe y esta activa ---


async def test_unknown_result_type_is_invalid_reference(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    with pytest.raises(InvalidReferenceError) as error:
        await _template_analyte(session, draft, "no-existe")

    assert error.value.details == {"result_type": "no-existe"}


async def test_inactive_result_type_is_rejected_only_when_new(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    existing = await _template_analyte(session, draft, "text")
    await _set(session, ResultType, "text", is_active=False)

    with pytest.raises(InactiveReferenceError):
        await _template_analyte(session, draft, "text")
    # Reenviar el tipo que el analito ya tenia no se revalida.
    updated = await controller.update_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        existing.id,
        ResultTemplateAnalyteUpdate(result_type="text", sort_order=5),
    )
    assert updated.sort_order == 5


async def test_unknown_sex_and_age_unit_in_range_are_invalid_references(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")

    with pytest.raises(InvalidReferenceError) as sex_error:
        await _create_range(session, draft, template_analyte, sex="X", low=1)
    with pytest.raises(InvalidReferenceError) as unit_error:
        await _create_range(
            session, draft, template_analyte, age_unit="siglos", age_min=1, low=1
        )

    assert sex_error.value.details == {"sex": "X"}
    assert unit_error.value.details == {"age_unit": "siglos"}


async def test_inactive_sex_in_range_is_rejected(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    await _set(session, Sex, "female", is_active=False)

    with pytest.raises(InactiveReferenceError):
        await _create_range(session, draft, template_analyte, sex="female", low=1)


async def test_http_unknown_result_type_returns_422_with_project_format(
    client: AsyncClient, draft: ResultTemplateVersionRead, analyte_payload: dict
) -> None:
    analyte = (await client.post("/api/v1/analytes", json=analyte_payload)).json()

    response = await client.post(
        f"/api/v1/result-templates/{draft.result_template_id}"
        f"/versions/{draft.id}/analytes",
        json={"analyte_id": analyte["id"], "sort_order": 1, "result_type": "no-existe"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_reference"


# --- comportamiento por banderas de result_types ---


async def test_range_fields_follow_result_type_flags(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "text")
    with pytest.raises(ValidationAppError):
        await _create_range(session, draft, template_analyte, expected_boolean=True)

    await _set(session, ResultType, "text", uses_boolean_range=True)

    created = await _create_range(
        session, draft, template_analyte, expected_boolean=True
    )
    assert created.expected_boolean is True


async def test_publish_required_fields_follow_result_type_flags(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    await _template_analyte(session, draft, "text")
    await _set(session, ResultType, "text", uses_unit=True, uses_formula=True)

    with pytest.raises(ResultTemplateVersionIncompleteError) as error:
        await controller.publish_version(session, draft.result_template_id, draft.id)

    missing = error.value.details["missing"][0]["missing_fields"]
    assert missing == ["formula", "unit_id", "decimals"]


async def test_requires_reference_range_flag_drives_the_range_rule(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    await _template_analyte(session, draft, "text")
    await _set(session, ResultType, "text", requires_reference_range=True)

    with pytest.raises(ResultTemplateVersionIncompleteError) as error:
        await controller.publish_version(session, draft.result_template_id, draft.id)

    assert error.value.details["missing"][0]["missing_fields"] == ["reference_ranges"]


async def test_publish_blocks_inactive_result_type(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    await _template_analyte(session, draft, "text")
    await _set(session, ResultType, "text", is_active=False)

    with pytest.raises(ResultTemplateVersionIncompleteError) as error:
        await controller.publish_version(session, draft.result_template_id, draft.id)

    assert {"field": "result_type", "id": "text"} == {
        key: error.value.details["inactive"][0][key] for key in ("field", "id")
    }


# --- solapamiento: sexes.is_wildcard y age_units.days ---


async def test_overlap_uses_the_wildcard_flag_not_the_any_code(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    await _create_range(session, draft, template_analyte, sex="any", low=1, high=2)

    with pytest.raises(ReferenceRangeOverlapError):
        await _create_range(session, draft, template_analyte, sex="male", low=3, high=4)

    # Sin la bandera, `any` es un sexo mas y ya no solapa con `male`.
    await _set(session, Sex, "any", is_wildcard=False)
    created = await _create_range(
        session, draft, template_analyte, sex="male", low=3, high=4
    )
    assert created.sex == "male"


async def test_overlap_normalizes_ages_with_age_units_days(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    template_analyte = await _template_analyte(session, draft, "numeric")
    await _create_range(
        session,
        draft,
        template_analyte,
        age_min=0,
        age_max=1,
        age_unit="anos",
        low=1,
        high=2,
    )
    # 365 dias < 1 ano (365,25): se solapan.
    with pytest.raises(ReferenceRangeOverlapError):
        await _create_range(
            session,
            draft,
            template_analyte,
            age_min=300,
            age_max=400,
            age_unit="dias",
            low=3,
            high=4,
        )

    # Con 1 ano = 100 dias el mismo rango (300-400 dias) ya no se solapa.
    await _set(session, AgeUnit, "anos", days=100)
    created = await _create_range(
        session,
        draft,
        template_analyte,
        age_min=300,
        age_max=400,
        age_unit="dias",
        low=3,
        high=4,
    )
    assert created.age_unit == "dias"
