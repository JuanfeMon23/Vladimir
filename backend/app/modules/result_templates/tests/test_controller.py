"""Tests del controller de `result_templates` (sin HTTP). Cubre los
catalogos basicos y el ciclo completo de una plantilla: crear -> draft ->
seccion -> analito numeric con rango -> publicar OK; y un caso de analito
qualitative sin `option_set_id` que debe fallar al publicar.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError, ValidationAppError
from app.core.versioning import VersionDraftExistsError, VersionMissingFieldsError
from app.modules.result_templates import controller
from app.modules.result_templates.exceptions import (
    ResultTemplateVersionIncompleteError,
)
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    ReferenceRangeCreate,
    ResultOptionCreate,
    ResultOptionSetCreate,
    ResultTemplateAnalyteCreate,
    ResultTemplateCreate,
    ResultTemplateSectionCreate,
    ResultTemplateVersionCreate,
)

# --------------------------------------------------------------------------
# Catalogos basicos
# --------------------------------------------------------------------------


async def test_create_analyte(session: AsyncSession, analyte_payload: dict) -> None:
    created = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    assert created.code == analyte_payload["code"]
    assert created.is_active is True


async def test_create_analyte_duplicate_code_raises_conflict(
    session: AsyncSession, analyte_payload: dict
) -> None:
    await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    with pytest.raises(CodeConflictError, match="Ya existe un analito con el código"):
        await controller.create_analyte(session, AnalyteCreate(**analyte_payload))


async def test_get_analyte_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe un analito con id"):
        await controller.get_analyte(session, uuid4())


async def test_list_analytes(session: AsyncSession, analyte_payload: dict) -> None:
    await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    # La BD de desarrollo puede tener muchos analitos (datos de demostracion):
    # se recorren todas las paginas en vez de suponer que cabe en la primera.
    codes: list[str] = []
    page_number = 1
    while True:
        page = await controller.list_analytes(
            session,
            PaginationParams(page=page_number, page_size=50),
            ActiveOnlyFilter(active=None),
        )
        codes += [item.code for item in page.items]
        if len(codes) >= page.total:
            break
        page_number += 1

    assert analyte_payload["code"] in codes


async def test_create_option_set_duplicate_code_raises_conflict(
    session: AsyncSession, option_set_payload: dict
) -> None:
    await controller.create_option_set(
        session, ResultOptionSetCreate(**option_set_payload)
    )

    with pytest.raises(
        CodeConflictError, match="Ya existe un conjunto de opciones con el código"
    ):
        await controller.create_option_set(
            session, ResultOptionSetCreate(**option_set_payload)
        )


async def test_create_option_and_duplicate_code_in_same_set_raises_conflict(
    session: AsyncSession, option_set_payload: dict, option_payload: dict
) -> None:
    option_set = await controller.create_option_set(
        session, ResultOptionSetCreate(**option_set_payload)
    )

    created_option = await controller.create_option(
        session, option_set.id, ResultOptionCreate(**option_payload)
    )
    assert created_option.option_set_id == option_set.id

    with pytest.raises(CodeConflictError, match="Ya existe una opción con el código"):
        await controller.create_option(
            session, option_set.id, ResultOptionCreate(**option_payload)
        )


async def test_create_result_template_duplicate_code_raises_conflict(
    session: AsyncSession, result_template_payload: dict
) -> None:
    await controller.create_template(
        session, ResultTemplateCreate(**result_template_payload)
    )

    with pytest.raises(
        CodeConflictError, match="Ya existe una plantilla con el código"
    ):
        await controller.create_template(
            session, ResultTemplateCreate(**result_template_payload)
        )


async def test_create_version_under_missing_template_raises_not_found(
    session: AsyncSession, result_template_version_payload: dict
) -> None:
    with pytest.raises(NotFoundError, match="No existe una plantilla con id"):
        await controller.create_version(
            session,
            uuid4(),
            ResultTemplateVersionCreate(**result_template_version_payload),
        )


async def test_create_first_version_missing_report_settings_raises(
    session: AsyncSession, result_template_payload: dict
) -> None:
    template = await controller.create_template(
        session, ResultTemplateCreate(**result_template_payload)
    )

    with pytest.raises(VersionMissingFieldsError):
        await controller.create_version(
            session, template.id, ResultTemplateVersionCreate(change_notes="incompleta")
        )


# --------------------------------------------------------------------------
# Ciclo completo de una plantilla
# --------------------------------------------------------------------------


async def test_full_template_lifecycle_publishes_when_complete(
    session: AsyncSession,
    result_template_payload: dict,
    result_template_version_payload: dict,
    analyte_payload: dict,
) -> None:
    template = await controller.create_template(
        session, ResultTemplateCreate(**result_template_payload)
    )

    draft = await controller.create_version(
        session,
        template.id,
        ResultTemplateVersionCreate(**result_template_version_payload),
    )
    assert draft.version_number == 1
    assert draft.status == "draft"

    section = await controller.create_section(
        session,
        template.id,
        draft.id,
        ResultTemplateSectionCreate(name="Quimica sanguinea", sort_order=1),
    )
    assert section.version_id == draft.id

    analyte = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    template_analyte = await controller.create_template_analyte(
        session,
        template.id,
        draft.id,
        ResultTemplateAnalyteCreate(
            section_id=section.id,
            analyte_id=analyte.id,
            sort_order=1,
            result_type="numeric",
            unit_id=analyte.default_unit_id,
            decimals=1,
        ),
    )
    assert template_analyte.result_type == "numeric"

    reference_range = await controller.create_reference_range(
        session,
        template.id,
        draft.id,
        template_analyte.id,
        ReferenceRangeCreate(sex="any", low=70, high=100),
    )
    assert reference_range.template_analyte_id == template_analyte.id

    published = await controller.publish_version(session, template.id, draft.id)
    assert published.status == "published"
    assert published.published_at is not None

    with pytest.raises(ValidationAppError):
        await controller.create_section(
            session,
            template.id,
            draft.id,
            ResultTemplateSectionCreate(name="tardia", sort_order=2),
        )

    # Segundo draft: clona secciones, analitos y rangos de la version publicada.
    second_draft = await controller.create_version(
        session, template.id, ResultTemplateVersionCreate(change_notes="v2")
    )
    assert second_draft.version_number == 2

    cloned_analytes = await controller.list_template_analytes(
        session, template.id, second_draft.id
    )
    assert len(cloned_analytes) == 1
    assert cloned_analytes[0].result_type == "numeric"
    assert cloned_analytes[0].unit == "mg/dL"

    cloned_ranges = await controller.list_reference_ranges(
        session, template.id, second_draft.id, cloned_analytes[0].id
    )
    assert len(cloned_ranges) == 1
    assert cloned_ranges[0].low == 70

    with pytest.raises(VersionDraftExistsError):
        await controller.create_version(
            session,
            template.id,
            ResultTemplateVersionCreate(change_notes="v3 prematura"),
        )


async def test_qualitative_analyte_without_option_set_fails_to_publish(
    session: AsyncSession,
    result_template_payload: dict,
    result_template_version_payload: dict,
    analyte_payload: dict,
) -> None:
    """Un analito `qualitative` se puede crear/editar libremente mientras la
    version esta en `draft` (construccion incremental); la completitud por
    `result_type` solo se exige al publicar.
    """
    template = await controller.create_template(
        session, ResultTemplateCreate(**result_template_payload)
    )
    draft = await controller.create_version(
        session,
        template.id,
        ResultTemplateVersionCreate(**result_template_version_payload),
    )
    analyte = await controller.create_analyte(session, AnalyteCreate(**analyte_payload))

    template_analyte = await controller.create_template_analyte(
        session,
        template.id,
        draft.id,
        ResultTemplateAnalyteCreate(
            analyte_id=analyte.id,
            sort_order=1,
            result_type="qualitative",
        ),
    )
    assert template_analyte.option_set_id is None

    with pytest.raises(ResultTemplateVersionIncompleteError):
        await controller.publish_version(session, template.id, draft.id)
