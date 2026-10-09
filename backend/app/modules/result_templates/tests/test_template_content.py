"""Contenido de una version de plantilla (secciones, analitos): sin borrado
fisico, referencias validas y activas, publicacion y clonado solo con lo
activo."""

from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.exceptions import ConflictError, ValidationAppError
from app.modules.result_templates import controller
from app.modules.result_templates.exceptions import (
    ResultTemplateVersionIncompleteError,
)
from app.modules.result_templates.models import Unit
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    AnalyteRead,
    AnalyteUpdate,
    ReferenceRangeCreate,
    ReferenceRangeUpdate,
    ResultOptionCreate,
    ResultOptionSetCreate,
    ResultOptionSetUpdate,
    ResultOptionUpdate,
    ResultTemplateAnalyteCreate,
    ResultTemplateAnalyteUpdate,
    ResultTemplateCreate,
    ResultTemplateSectionCreate,
    ResultTemplateSectionUpdate,
    ResultTemplateVersionCreate,
    ResultTemplateVersionRead,
)
from app.modules.result_templates.tests.conftest import make_unit, unique_code


async def _analyte(session: AsyncSession, unit: Unit | None = None) -> AnalyteRead:
    return await controller.create_analyte(
        session,
        AnalyteCreate(
            code=unique_code("analyte"),
            name="Analito",
            default_unit_id=unit.id if unit else None,
        ),
    )


async def _option_set(session: AsyncSession, *, is_active: bool = True):
    option_set = await controller.create_option_set(
        session,
        ResultOptionSetCreate(
            code=unique_code("set"), name="Reactivo/No reactivo", is_active=is_active
        ),
    )
    return option_set


async def _add(session: AsyncSession, draft: ResultTemplateVersionRead, **fields):
    return await controller.create_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        ResultTemplateAnalyteCreate(**{"sort_order": 1, **fields}),
    )


async def _numeric(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit, **extra
):
    analyte = await _analyte(session, unit)
    return await _add(
        session,
        draft,
        analyte_id=analyte.id,
        result_type="numeric",
        unit_id=unit.id,
        decimals=1,
        **extra,
    )


async def _range(session, draft, template_analyte_id: UUID, **fields):
    return await controller.create_reference_range(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte_id,
        ReferenceRangeCreate(**fields),
    )


async def _publish(session, draft):
    return await controller.publish_version(session, draft.result_template_id, draft.id)


# --- crear version / opcion bajo padre inactivo ---


async def test_create_version_under_inactive_template_raises(
    session: AsyncSession, result_template_payload: dict
) -> None:
    template = await controller.create_template(
        session, ResultTemplateCreate(**{**result_template_payload, "is_active": False})
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_version(
            session, template.id, ResultTemplateVersionCreate(report_settings={})
        )
    assert exc_info.value.details == {"result_template_id": str(template.id)}


async def test_create_option_under_inactive_set_raises(
    session: AsyncSession, option_payload: dict
) -> None:
    option_set = await _option_set(session, is_active=False)

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_option(
            session, option_set.id, ResultOptionCreate(**option_payload)
        )
    assert exc_info.value.details == {"option_set_id": str(option_set.id)}


# --- analito de plantilla: referencias ---


async def test_template_analyte_exposes_unit_symbol_and_detail(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    created = await _numeric(session, draft, unit)

    assert created.unit_id == unit.id
    assert created.unit == "mg/dL"
    assert created.unit_detail is not None
    assert created.unit_detail.code == unit.code
    assert created.is_active is True


@pytest.mark.parametrize("field", ["analyte_id", "option_set_id", "unit_id"])
async def test_template_analyte_unknown_reference_returns_invalid_reference(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit, field: str
) -> None:
    analyte = await _analyte(session, unit)
    fields = {"analyte_id": analyte.id, "result_type": "numeric", field: uuid4()}

    with pytest.raises(ValidationAppError) as exc_info:
        await _add(session, draft, **fields)
    assert exc_info.value.code == "invalid_reference"
    assert set(exc_info.value.details) == {field}


async def test_template_analyte_rejects_inactive_analyte(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    analyte = await _analyte(session, unit)
    await controller.update_analyte(session, analyte.id, AnalyteUpdate(is_active=False))

    with pytest.raises(InactiveReferenceError) as exc_info:
        await _add(session, draft, analyte_id=analyte.id, result_type="numeric")
    assert exc_info.value.message == f"El analito «{analyte.code}» está inactivo."


async def test_template_analyte_rejects_inactive_option_set(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    option_set = await _option_set(session, is_active=False)

    with pytest.raises(InactiveReferenceError):
        await _add(
            session,
            draft,
            analyte_id=analyte.id,
            result_type="qualitative",
            option_set_id=option_set.id,
        )


async def test_template_analyte_rejects_inactive_unit(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    inactive = await make_unit(session, is_active=False)

    with pytest.raises(InactiveReferenceError):
        await _add(
            session,
            draft,
            analyte_id=analyte.id,
            result_type="numeric",
            unit_id=inactive.id,
        )


async def test_template_analyte_section_must_be_of_same_version(
    session: AsyncSession,
    draft: ResultTemplateVersionRead,
    unit: Unit,
    result_template_version_payload: dict,
) -> None:
    other_template = await controller.create_template(
        session, ResultTemplateCreate(code=unique_code("tpl"), name="Otra")
    )
    other_draft = await controller.create_version(
        session,
        other_template.id,
        ResultTemplateVersionCreate(**result_template_version_payload),
    )
    foreign_section = await controller.create_section(
        session,
        other_template.id,
        other_draft.id,
        ResultTemplateSectionCreate(name="Ajena", sort_order=1),
    )
    analyte = await _analyte(session, unit)

    with pytest.raises(ValidationAppError) as exc_info:
        await _add(
            session,
            draft,
            analyte_id=analyte.id,
            result_type="numeric",
            section_id=foreign_section.id,
        )
    assert exc_info.value.code == "invalid_reference"
    assert set(exc_info.value.details) == {"section_id"}


async def test_template_analyte_rejects_inactive_section(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    section = await controller.create_section(
        session,
        draft.result_template_id,
        draft.id,
        ResultTemplateSectionCreate(name="Serie roja", sort_order=1),
    )
    await controller.update_section(
        session,
        draft.result_template_id,
        draft.id,
        section.id,
        ResultTemplateSectionUpdate(is_active=False),
    )
    analyte = await _analyte(session, unit)

    with pytest.raises(InactiveReferenceError):
        await _add(
            session,
            draft,
            analyte_id=analyte.id,
            result_type="numeric",
            section_id=section.id,
        )


async def test_same_analyte_twice_active_in_version_is_conflict(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    first = await _numeric(session, draft, unit)

    with pytest.raises(ConflictError):
        await _add(session, draft, analyte_id=first.analyte_id, result_type="numeric")


async def test_deactivated_template_analyte_is_hidden_and_analyte_can_be_added_again(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    first = await _numeric(session, draft, unit)
    await controller.update_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        first.id,
        ResultTemplateAnalyteUpdate(is_active=False, activity_reason="Repetido"),
    )

    visible = await controller.list_template_analytes(
        session, draft.result_template_id, draft.id
    )
    everything = await controller.list_template_analytes(
        session, draft.result_template_id, draft.id, include_inactive=True
    )
    assert visible == []
    assert [(a.id, a.is_active) for a in everything] == [(first.id, False)]

    again = await _add(
        session, draft, analyte_id=first.analyte_id, result_type="numeric"
    )
    assert again.id != first.id

    # Reactivar la fila vieja chocaria con la nueva activa: 409, no un 500.
    with pytest.raises(ConflictError):
        await controller.update_template_analyte(
            session,
            draft.result_template_id,
            draft.id,
            first.id,
            ResultTemplateAnalyteUpdate(is_active=True),
        )


# --- secciones: sin DELETE ---


async def test_section_delete_returns_405_and_patch_deactivates(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    base = (
        f"/api/v1/result-templates/{draft.result_template_id}"
        f"/versions/{draft.id}/sections"
    )
    section = (await client.post(base, json={"name": "Serie", "sort_order": 1})).json()

    deleted = await client.delete(f"{base}/{section['id']}")
    assert deleted.status_code == 405

    patched = await client.patch(f"{base}/{section['id']}", json={"is_active": False})
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False
    assert (await client.get(base)).json() == []
    everything = (await client.get(base, params={"include_inactive": True})).json()
    assert [s["id"] for s in everything] == [section["id"]]


async def test_template_analyte_and_range_delete_return_405(
    client: AsyncClient, session: AsyncSession, draft: ResultTemplateVersionRead, unit
) -> None:
    template_analyte = await _numeric(session, draft, unit)
    reference_range = await _range(session, draft, template_analyte.id, low=1, high=2)
    base = (
        f"/api/v1/result-templates/{draft.result_template_id}/versions/{draft.id}"
        f"/analytes/{template_analyte.id}"
    )

    assert (await client.delete(base)).status_code == 405
    assert (
        await client.delete(f"{base}/reference-ranges/{reference_range.id}")
    ).status_code == 405


async def test_content_patch_on_published_version_is_rejected(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_analyte = await _numeric(session, draft, unit)
    await _range(session, draft, template_analyte.id, low=1, high=2)
    await _publish(session, draft)

    with pytest.raises(ValidationAppError):
        await controller.update_template_analyte(
            session,
            draft.result_template_id,
            draft.id,
            template_analyte.id,
            ResultTemplateAnalyteUpdate(is_active=False),
        )


# --- publicar ---


def _missing_by_id(error: ResultTemplateVersionIncompleteError) -> dict:
    return {item["template_analyte_id"]: item for item in error.details["missing"]}


async def test_publish_numeric_reportable_requires_active_range(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_analyte = await _numeric(session, draft, unit)
    reference_range = await _range(session, draft, template_analyte.id, low=1, high=2)
    await controller.update_reference_range(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        reference_range.id,
        ReferenceRangeUpdate(is_active=False),
    )

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await _publish(session, draft)
    missing = _missing_by_id(exc_info.value)
    assert missing[str(template_analyte.id)]["missing_fields"] == ["reference_ranges"]


async def test_publish_numeric_not_reportable_does_not_require_range(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    await _numeric(session, draft, unit, is_reportable=False)

    published = await _publish(session, draft)
    assert published.status == "published"


async def test_publish_calculated_requires_formula_unit_and_decimals(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    template_analyte = await _add(
        session, draft, analyte_id=analyte.id, result_type="calculated"
    )

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await _publish(session, draft)
    missing = _missing_by_id(exc_info.value)[str(template_analyte.id)]
    assert sorted(missing["missing_fields"]) == ["decimals", "formula", "unit_id"]


async def test_publish_titer_requires_option_set(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    template_analyte = await _add(
        session, draft, analyte_id=analyte.id, result_type="titer"
    )

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await _publish(session, draft)
    missing = _missing_by_id(exc_info.value)[str(template_analyte.id)]
    assert missing["missing_fields"] == ["option_set_id"]


async def test_publish_titer_with_option_set_succeeds(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    option_set = await _option_set(session)
    await _add(
        session,
        draft,
        analyte_id=analyte.id,
        result_type="titer",
        option_set_id=option_set.id,
    )

    published = await _publish(session, draft)
    assert published.status == "published"


async def test_publish_ignores_inactive_template_analytes(
    session: AsyncSession, draft: ResultTemplateVersionRead
) -> None:
    analyte = await _analyte(session)
    incomplete = await _add(
        session, draft, analyte_id=analyte.id, result_type="qualitative"
    )
    await controller.update_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        incomplete.id,
        ResultTemplateAnalyteUpdate(is_active=False),
    )

    published = await _publish(session, draft)
    assert published.status == "published"


async def test_publish_reports_inactive_catalog_references(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    numeric = await _numeric(session, draft, unit)
    await _range(session, draft, numeric.id, low=1, high=2)
    option_set = await _option_set(session)
    option = await controller.create_option(
        session,
        option_set.id,
        ResultOptionCreate(code="R", label="Reactivo", sort_order=1),
    )
    qualitative_analyte = await _analyte(session)
    qualitative = await _add(
        session,
        draft,
        analyte_id=qualitative_analyte.id,
        result_type="qualitative",
        option_set_id=option_set.id,
        sort_order=2,
    )
    reference_range = await _range(
        session, draft, qualitative.id, expected_option_id=option.id
    )

    await controller.update_analyte(
        session, numeric.analyte_id, AnalyteUpdate(is_active=False)
    )
    unit.is_active = False
    await session.commit()
    await controller.update_option_set(
        session, option_set.id, ResultOptionSetUpdate(is_active=False)
    )
    await controller.update_option(
        session, option.id, ResultOptionUpdate(is_active=False)
    )

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await _publish(session, draft)

    inactive = {
        (item["template_analyte_id"], item["field"], item["id"])
        for item in exc_info.value.details["inactive"]
    }
    assert inactive == {
        (str(numeric.id), "analyte_id", str(numeric.analyte_id)),
        (str(numeric.id), "unit_id", str(unit.id)),
        (str(qualitative.id), "option_set_id", str(option_set.id)),
        (str(qualitative.id), "expected_option_id", str(option.id)),
    }
    assert exc_info.value.details["missing"] == []
    assert reference_range.id  # el rango sigue existiendo


async def test_publish_reports_ranges_incompatible_with_new_result_type(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_analyte = await _numeric(session, draft, unit)
    reference_range = await _range(session, draft, template_analyte.id, low=1, high=2)
    option_set = await _option_set(session)
    await controller.update_template_analyte(
        session,
        draft.result_template_id,
        draft.id,
        template_analyte.id,
        ResultTemplateAnalyteUpdate(
            result_type="qualitative", option_set_id=option_set.id
        ),
    )

    with pytest.raises(ResultTemplateVersionIncompleteError) as exc_info:
        await _publish(session, draft)
    missing = _missing_by_id(exc_info.value)[str(template_analyte.id)]
    assert missing["incompatible_reference_range_ids"] == [str(reference_range.id)]


# --- clonar: solo filas activas ---


async def test_clone_copies_only_active_content(
    session: AsyncSession, draft: ResultTemplateVersionRead, unit: Unit
) -> None:
    template_id = draft.result_template_id
    kept_section = await controller.create_section(
        session,
        template_id,
        draft.id,
        ResultTemplateSectionCreate(name="A", sort_order=1),
    )
    dropped_section = await controller.create_section(
        session,
        template_id,
        draft.id,
        ResultTemplateSectionCreate(name="B", sort_order=2),
    )
    await controller.update_section(
        session,
        template_id,
        draft.id,
        dropped_section.id,
        ResultTemplateSectionUpdate(is_active=False),
    )
    kept = await _numeric(session, draft, unit, section_id=kept_section.id)
    kept_range = await _range(session, draft, kept.id, low=1, high=2)
    dropped_range = await _range(
        session, draft, kept.id, condition="Embarazo", low=3, high=4
    )
    await controller.update_reference_range(
        session,
        template_id,
        draft.id,
        kept.id,
        dropped_range.id,
        ReferenceRangeUpdate(is_active=False),
    )
    dropped = await _numeric(session, draft, unit, sort_order=2)
    await controller.update_template_analyte(
        session,
        template_id,
        draft.id,
        dropped.id,
        ResultTemplateAnalyteUpdate(is_active=False),
    )
    await _publish(session, draft)
    # Un catalogo desactivado despues de publicar SI se copia (publicar el
    # nuevo borrador lo bloqueara).
    await controller.update_analyte(
        session, kept.analyte_id, AnalyteUpdate(is_active=False)
    )

    clone = await controller.create_version(
        session, template_id, ResultTemplateVersionCreate(change_notes="v2")
    )

    sections = await controller.list_sections(
        session, template_id, clone.id, include_inactive=True
    )
    analytes = await controller.list_template_analytes(
        session, template_id, clone.id, include_inactive=True
    )
    assert [s.name for s in sections] == ["A"]
    assert [(a.analyte_id, a.section_id) for a in analytes] == [
        (kept.analyte_id, sections[0].id)
    ]
    ranges = await controller.list_reference_ranges(
        session, template_id, clone.id, analytes[0].id, include_inactive=True
    )
    assert [(r.low, r.high) for r in ranges] == [(kept_range.low, kept_range.high)]
