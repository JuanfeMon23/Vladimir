"""Tests del controller de `lab_tests` (sin HTTP)."""

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError, ValidationAppError
from app.modules.consent_documents.models import ConsentDocumentVersion
from app.modules.lab_areas.models import LabArea
from app.modules.lab_tests import controller
from app.modules.lab_tests.exceptions import (
    LabTestSampleTypePreferredCountError,
    LabTestSampleTypesRequiredError,
)
from app.modules.lab_tests.models import (
    LabTest,
    LabTestConsentDocument,
    LabTestPrecondition,
    LabTestSampleType,
)
from app.modules.lab_tests.schemas import (
    LabTestConsentDocumentInput,
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestSampleTypeInput,
    LabTestUpdate,
)
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabelVersion
from app.modules.result_templates.models import ResultTemplateVersion
from app.modules.samples.models import SampleType


async def test_create_lab_test(session: AsyncSession, lab_test_payload: dict) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    assert created.code == lab_test_payload["code"]
    assert created.is_active is True
    assert created.preconditions == []
    assert len(created.sample_types) == 1
    assert created.sample_types[0].is_preferred is True
    assert created.consent_documents == []


async def test_create_lab_test_rejects_empty_sample_types(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    payload = {**lab_test_payload, "sample_types": []}

    with pytest.raises(LabTestSampleTypesRequiredError):
        await controller.create_lab_test(session, LabTestCreate(**payload))
    assert (
        await session.scalar(select(LabTest).where(LabTest.code == payload["code"]))
        is None
    )


async def test_create_lab_test_rejects_zero_preferred(
    session: AsyncSession, lab_test_payload: dict, sample_type: SampleType
) -> None:
    payload = {
        **lab_test_payload,
        "sample_types": [{"sample_type_id": sample_type.id, "sort_order": 1}],
    }

    with pytest.raises(LabTestSampleTypePreferredCountError):
        await controller.create_lab_test(session, LabTestCreate(**payload))


async def test_create_lab_test_rejects_unknown_sample_type_without_leftovers(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    payload = {
        **lab_test_payload,
        "sample_types": [
            {"sample_type_id": uuid4(), "is_preferred": True, "sort_order": 1}
        ],
    }

    with pytest.raises(
        ValidationAppError, match="Los siguientes tipos de muestra no existen"
    ):
        await controller.create_lab_test(session, LabTestCreate(**payload))
    assert (
        await session.scalar(select(LabTest).where(LabTest.code == payload["code"]))
        is None
    )


async def test_create_lab_test_rejects_inactive_sample_type(
    session: AsyncSession, lab_test_payload: dict, sample_type: SampleType
) -> None:
    sample_type.is_active = False
    await session.commit()

    with pytest.raises(InactiveReferenceError):
        await controller.create_lab_test(session, LabTestCreate(**lab_test_payload))
    assert (
        await session.scalar(
            select(LabTest).where(LabTest.code == lab_test_payload["code"])
        )
        is None
    )


async def test_create_lab_test_duplicate_code_raises_conflict(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    await controller.create_lab_test(session, LabTestCreate(**lab_test_payload))

    with pytest.raises(CodeConflictError, match="Ya existe un examen con el código"):
        await controller.create_lab_test(session, LabTestCreate(**lab_test_payload))


async def test_create_lab_test_invalid_area_raises(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    payload = {**lab_test_payload, "area_id": str(uuid4())}

    with pytest.raises(ValidationAppError, match="No existe un area con id"):
        await controller.create_lab_test(session, LabTestCreate(**payload))


async def test_get_lab_test_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe un examen con id"):
        await controller.get_lab_test(session, uuid4())


async def test_list_lab_tests_filters_by_area(
    session: AsyncSession, lab_test_payload: dict, lab_area: LabArea
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    page = await controller.list_lab_tests(
        session,
        PaginationParams(page=1, page_size=20),
        ActiveOnlyFilter(active=None),
        area_id=lab_area.id,
    )
    assert any(item.id == created.id for item in page.items)

    other_area_page = await controller.list_lab_tests(
        session,
        PaginationParams(page=1, page_size=20),
        ActiveOnlyFilter(active=None),
        area_id=uuid4(),
    )
    assert all(item.id != created.id for item in other_area_page.items)


# --- version publicada requerida (print_label / result_template) ---


async def test_create_lab_test_rejects_unpublished_print_label_version(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_print_label_version: PrintLabelVersion,
) -> None:
    payload = {
        **lab_test_payload,
        "print_label_version_id": str(draft_print_label_version.id),
    }

    with pytest.raises(ValidationAppError, match="La version de etiqueta"):
        await controller.create_lab_test(session, LabTestCreate(**payload))


async def test_create_lab_test_accepts_published_print_label_version(
    session: AsyncSession,
    lab_test_payload: dict,
    published_print_label_version: PrintLabelVersion,
) -> None:
    payload = {
        **lab_test_payload,
        "print_label_version_id": str(published_print_label_version.id),
    }

    created = await controller.create_lab_test(session, LabTestCreate(**payload))

    assert created.print_label_version_id == published_print_label_version.id


async def test_update_lab_test_rejects_unpublished_result_template_version(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_result_template_version: ResultTemplateVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    with pytest.raises(
        ValidationAppError, match="La version de plantilla de resultados"
    ):
        await controller.update_lab_test(
            session,
            created.id,
            LabTestUpdate(result_template_version_id=draft_result_template_version.id),
        )


async def test_update_lab_test_accepts_published_result_template_version(
    session: AsyncSession,
    lab_test_payload: dict,
    published_result_template_version: ResultTemplateVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    updated = await controller.update_lab_test(
        session,
        created.id,
        LabTestUpdate(result_template_version_id=published_result_template_version.id),
    )

    assert updated.result_template_version_id == published_result_template_version.id


# --- precondiciones: override efectivo resuelto ---


async def test_set_preconditions_resolves_effective_override(
    session: AsyncSession, lab_test_payload: dict, precondition: Precondition
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestPreconditionInput(
            precondition_id=precondition.id,
            is_mandatory=True,
            sort_order=1,
            name_override="Ayuno estricto de 12 horas",
            duration_value_override=12,
        )
    ]

    result = await controller.set_preconditions(session, created.id, items)

    assert len(result) == 1
    resolved = result[0]
    assert resolved.name == "Ayuno estricto de 12 horas"
    assert resolved.duration_value == 12
    # Sin override: cae al valor del catalogo.
    assert resolved.duration_unit == precondition.duration_unit
    assert resolved.patient_instructions == precondition.patient_instructions


async def test_set_preconditions_without_override_uses_catalog_values(
    session: AsyncSession, lab_test_payload: dict, precondition: Precondition
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestPreconditionInput(
            precondition_id=precondition.id, is_mandatory=False, sort_order=1
        )
    ]

    result = await controller.set_preconditions(session, created.id, items)

    assert result[0].name == precondition.name
    assert result[0].description == precondition.description
    assert result[0].duration_value == precondition.duration_value


async def test_set_preconditions_invalid_id_raises(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestPreconditionInput(precondition_id=uuid4(), sort_order=1),
    ]

    with pytest.raises(
        ValidationAppError, match="Las siguientes precondiciones no existen"
    ):
        await controller.set_preconditions(session, created.id, items)


async def test_get_preconditions_reflects_last_set(
    session: AsyncSession, lab_test_payload: dict, precondition: Precondition
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )
    await controller.set_preconditions(
        session,
        created.id,
        [LabTestPreconditionInput(precondition_id=precondition.id, sort_order=1)],
    )

    result = await controller.get_preconditions(session, created.id)

    assert len(result) == 1
    assert result[0].precondition_id == precondition.id


# --- tipos de muestra: al menos uno, exactamente un preferido ---


async def test_set_sample_types_rejects_empty_list_and_keeps_assignments(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    with pytest.raises(LabTestSampleTypesRequiredError):
        await controller.set_sample_types(session, created.id, [])

    assert len(await controller.get_sample_types(session, created.id)) == 1


async def test_set_sample_types_rejects_zero_preferred(
    session: AsyncSession, lab_test_payload: dict, sample_type: SampleType
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestSampleTypeInput(
            sample_type_id=sample_type.id, is_preferred=False, sort_order=1
        )
    ]

    with pytest.raises(LabTestSampleTypePreferredCountError):
        await controller.set_sample_types(session, created.id, items)


async def test_set_sample_types_rejects_multiple_preferred(
    session: AsyncSession,
    lab_test_payload: dict,
    sample_type: SampleType,
    other_sample_type: SampleType,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestSampleTypeInput(
            sample_type_id=sample_type.id, is_preferred=True, sort_order=1
        ),
        LabTestSampleTypeInput(
            sample_type_id=other_sample_type.id, is_preferred=True, sort_order=2
        ),
    ]

    with pytest.raises(LabTestSampleTypePreferredCountError):
        await controller.set_sample_types(session, created.id, items)


async def test_set_sample_types_accepts_exactly_one_preferred(
    session: AsyncSession,
    lab_test_payload: dict,
    sample_type: SampleType,
    other_sample_type: SampleType,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestSampleTypeInput(
            sample_type_id=sample_type.id,
            is_preferred=True,
            required_volume_ml=5,
            sort_order=1,
        ),
        LabTestSampleTypeInput(
            sample_type_id=other_sample_type.id, is_preferred=False, sort_order=2
        ),
    ]

    result = await controller.set_sample_types(session, created.id, items)

    assert len(result) == 2
    preferred = [item for item in result if item.is_preferred]
    assert len(preferred) == 1
    assert preferred[0].sample_type_id == sample_type.id


async def test_set_sample_types_invalid_id_raises(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestSampleTypeInput(sample_type_id=uuid4(), is_preferred=True, sort_order=1)
    ]

    with pytest.raises(
        ValidationAppError, match="Los siguientes tipos de muestra no existen"
    ):
        await controller.set_sample_types(session, created.id, items)


# --- documentos a firmar: version publicada requerida ---


async def test_set_consent_documents_rejects_unpublished_version(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_consent_document_version: ConsentDocumentVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestConsentDocumentInput(
            consent_document_version_id=draft_consent_document_version.id
        )
    ]

    with pytest.raises(
        ValidationAppError, match="Las siguientes versiones de documento"
    ):
        await controller.set_consent_documents(session, created.id, items)


async def test_set_consent_documents_accepts_published_version(
    session: AsyncSession,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    items = [
        LabTestConsentDocumentInput(
            consent_document_version_id=published_consent_document_version.id,
            is_mandatory=True,
        )
    ]

    result = await controller.set_consent_documents(session, created.id, items)

    assert len(result) == 1
    assert (
        result[0].consent_document_version_id == published_consent_document_version.id
    )


# --- GET /lab-tests/{id}: detalle embebido ---


async def test_get_lab_test_embeds_resolved_collections(
    session: AsyncSession,
    lab_test_payload: dict,
    precondition: Precondition,
    sample_type: SampleType,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    await controller.set_preconditions(
        session,
        created.id,
        [
            LabTestPreconditionInput(
                precondition_id=precondition.id,
                sort_order=1,
                name_override="Override de prueba",
            )
        ],
    )
    await controller.set_sample_types(
        session,
        created.id,
        [
            LabTestSampleTypeInput(
                sample_type_id=sample_type.id, is_preferred=True, sort_order=1
            )
        ],
    )
    await controller.set_consent_documents(
        session,
        created.id,
        [
            LabTestConsentDocumentInput(
                consent_document_version_id=published_consent_document_version.id
            )
        ],
    )

    detail = await controller.get_lab_test(session, created.id)

    assert len(detail.preconditions) == 1
    assert detail.preconditions[0].name == "Override de prueba"
    assert len(detail.sample_types) == 1
    assert detail.sample_types[0].is_preferred is True
    assert len(detail.consent_documents) == 1


async def test_assignments_expose_their_own_row_id(
    session: AsyncSession,
    lab_test_payload: dict,
    precondition: Precondition,
    sample_type: SampleType,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    """El `id` de cada asignacion es el de su fila (no el del catalogo), para
    consultar `/activity?entity_type=lab_test_*&entity_id=<id>`."""
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )

    preconditions = await controller.set_preconditions(
        session,
        created.id,
        [LabTestPreconditionInput(precondition_id=precondition.id, sort_order=1)],
    )
    sample_types = await controller.set_sample_types(
        session,
        created.id,
        [
            LabTestSampleTypeInput(
                sample_type_id=sample_type.id, is_preferred=True, sort_order=1
            )
        ],
    )
    consent_documents = await controller.set_consent_documents(
        session,
        created.id,
        [
            LabTestConsentDocumentInput(
                consent_document_version_id=published_consent_document_version.id
            )
        ],
    )

    precondition_row_id = await session.scalar(
        select(LabTestPrecondition.id).where(
            LabTestPrecondition.lab_test_id == created.id
        )
    )
    sample_type_row_id = await session.scalar(
        select(LabTestSampleType.id).where(LabTestSampleType.lab_test_id == created.id)
    )
    consent_document_row_id = await session.scalar(
        select(LabTestConsentDocument.id).where(
            LabTestConsentDocument.lab_test_id == created.id
        )
    )

    assert preconditions[0].id == precondition_row_id
    assert sample_types[0].id == sample_type_row_id
    assert consent_documents[0].id == consent_document_row_id

    detail = await controller.get_lab_test(session, created.id)

    assert detail.preconditions[0].id == precondition_row_id
    assert detail.sample_types[0].id == sample_type_row_id
    assert detail.consent_documents[0].id == consent_document_row_id
