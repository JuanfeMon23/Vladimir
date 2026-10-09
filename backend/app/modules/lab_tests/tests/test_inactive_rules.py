"""Reglas "nada se elimina, solo se desactiva" y "no se relaciona con
desactivados" del modulo `lab_tests` (controller + HTTP)."""

from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.modules.consent_documents.models import ConsentDocument, ConsentDocumentVersion
from app.modules.lab_areas.models import LabArea
from app.modules.lab_tests import controller
from app.modules.lab_tests.models import LabTestPrecondition
from app.modules.lab_tests.schemas import (
    LabTestConsentDocumentInput,
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestSampleTypeInput,
    LabTestUpdate,
)
from app.modules.lab_tests.tests.conftest import unique_code
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabel, PrintLabelVersion
from app.modules.result_templates.models import ResultTemplate, ResultTemplateVersion
from app.modules.samples.models import SampleType


async def _save[T](session: AsyncSession, obj: T) -> T:
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def _deactivate(session: AsyncSession, obj: object) -> None:
    obj.is_active = False  # type: ignore[attr-defined]
    await session.commit()


async def _precondition(session: AsyncSession, *, is_active: bool = True):
    return await _save(
        session,
        Precondition(
            code=unique_code("precond"),
            name="Precondicion",
            kind="precondition",
            category="ayuno",
            is_active=is_active,
        ),
    )


async def _published_consent_version(
    session: AsyncSession, *, document_active: bool = True
) -> ConsentDocumentVersion:
    document = await _save(
        session,
        ConsentDocument(
            code=unique_code("consent"),
            name="Consentimiento",
            document_type="otro",
            is_active=document_active,
        ),
    )
    return await _save(
        session,
        ConsentDocumentVersion(
            consent_document_id=document.id,
            version_number=1,
            status="published",
            published_at=datetime.now(UTC),
            content="Texto",
            signer="paciente",
        ),
    )


async def _lab_test(session: AsyncSession, payload: dict):
    return await controller.create_lab_test(session, LabTestCreate(**payload))


def _precondition_input(precondition_id: UUID, sort_order: int = 1, **extra):
    return LabTestPreconditionInput(
        precondition_id=precondition_id, sort_order=sort_order, **extra
    )


# --- referencias directas del examen ---


async def test_create_with_inactive_area_raises(
    session: AsyncSession, lab_test_payload: dict, lab_area: LabArea
) -> None:
    await _deactivate(session, lab_area)

    with pytest.raises(InactiveReferenceError) as exc_info:
        await _lab_test(session, lab_test_payload)
    assert exc_info.value.details == {"area_id": str(lab_area.id)}


async def test_update_to_inactive_area_raises(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    other = await _save(
        session, LabArea(code=unique_code("area"), name="Otra", is_active=False)
    )

    with pytest.raises(InactiveReferenceError):
        await controller.update_lab_test(
            session, lab_test.id, LabTestUpdate(area_id=other.id)
        )


async def test_update_keeping_inactive_area_is_allowed(
    session: AsyncSession, lab_test_payload: dict, lab_area: LabArea
) -> None:
    """La relacion existente se conserva aunque el area se desactive."""
    lab_test = await _lab_test(session, lab_test_payload)
    await _deactivate(session, lab_area)

    # El formulario reenvia el mismo `area_id`: no es una relacion nueva.
    updated = await controller.update_lab_test(
        session, lab_test.id, LabTestUpdate(name="Renombrado", area_id=lab_area.id)
    )
    assert updated.area_id == lab_area.id


async def test_create_with_version_of_inactive_print_label_raises(
    session: AsyncSession,
    lab_test_payload: dict,
    print_label: PrintLabel,
    published_print_label_version: PrintLabelVersion,
) -> None:
    await _deactivate(session, print_label)

    with pytest.raises(InactiveReferenceError) as exc_info:
        await _lab_test(
            session,
            {
                **lab_test_payload,
                "print_label_version_id": str(published_print_label_version.id),
            },
        )
    assert exc_info.value.details == {"print_label_id": str(print_label.id)}


async def test_update_with_version_of_inactive_result_template_raises(
    session: AsyncSession,
    lab_test_payload: dict,
    result_template: ResultTemplate,
    published_result_template_version: ResultTemplateVersion,
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    await _deactivate(session, result_template)

    with pytest.raises(InactiveReferenceError):
        await controller.update_lab_test(
            session,
            lab_test.id,
            LabTestUpdate(
                result_template_version_id=published_result_template_version.id
            ),
        )


# --- colecciones: diff en vez de borrar ---


async def test_replace_non_empty_preconditions_deactivates_and_reactivates(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    a = await _precondition(session)
    b = await _precondition(session)
    c = await _precondition(session)

    await controller.set_preconditions(
        session, lab_test.id, [_precondition_input(a.id), _precondition_input(b.id, 2)]
    )
    result = await controller.set_preconditions(
        session,
        lab_test.id,
        [_precondition_input(b.id, 1), _precondition_input(c.id, 2)],
    )

    assert [item.precondition_id for item in result] == [b.id, c.id]
    assert all(item.is_active for item in result)

    with_inactive = await controller.get_preconditions(
        session, lab_test.id, include_inactive=True
    )
    states = {item.precondition_id: item.is_active for item in with_inactive}
    assert states == {a.id: False, b.id: True, c.id: True}

    # Volver a poner `a` reactiva la misma fila, con los campos nuevos.
    result = await controller.set_preconditions(
        session,
        lab_test.id,
        [_precondition_input(a.id, 5, name_override="Ayuno estricto")],
    )
    assert [(i.precondition_id, i.name, i.sort_order) for i in result] == [
        (a.id, "Ayuno estricto", 5)
    ]
    rows = (
        await session.execute(
            select(func.count())
            .select_from(LabTestPrecondition)
            .where(
                LabTestPrecondition.lab_test_id == lab_test.id,
                LabTestPrecondition.precondition_id == a.id,
            )
        )
    ).scalar_one()
    assert rows == 1


async def test_set_preconditions_rejects_new_inactive_precondition(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    inactive = await _precondition(session, is_active=False)

    with pytest.raises(InactiveReferenceError):
        await controller.set_preconditions(
            session, lab_test.id, [_precondition_input(inactive.id)]
        )


async def test_set_preconditions_keeps_already_associated_inactive_precondition(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    a = await _precondition(session)
    await controller.set_preconditions(
        session, lab_test.id, [_precondition_input(a.id)]
    )
    await _deactivate(session, a)

    result = await controller.set_preconditions(
        session, lab_test.id, [_precondition_input(a.id, 3)]
    )
    assert [(i.precondition_id, i.sort_order) for i in result] == [(a.id, 3)]


async def test_set_sample_types_diff_and_preferred_swap(
    session: AsyncSession,
    lab_test_payload: dict,
    sample_type: SampleType,
    other_sample_type: SampleType,
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    await controller.set_sample_types(
        session,
        lab_test.id,
        [
            LabTestSampleTypeInput(
                sample_type_id=sample_type.id, is_preferred=True, sort_order=1
            ),
            LabTestSampleTypeInput(sample_type_id=other_sample_type.id, sort_order=2),
        ],
    )

    swapped = await controller.set_sample_types(
        session,
        lab_test.id,
        [
            LabTestSampleTypeInput(sample_type_id=sample_type.id, sort_order=1),
            LabTestSampleTypeInput(
                sample_type_id=other_sample_type.id, is_preferred=True, sort_order=2
            ),
        ],
    )
    assert {i.sample_type_id: i.is_preferred for i in swapped} == {
        sample_type.id: False,
        other_sample_type.id: True,
    }

    reduced = await controller.set_sample_types(
        session,
        lab_test.id,
        [
            LabTestSampleTypeInput(
                sample_type_id=sample_type.id, is_preferred=True, sort_order=1
            )
        ],
    )
    assert [i.sample_type_id for i in reduced] == [sample_type.id]
    everything = await controller.get_sample_types(
        session, lab_test.id, include_inactive=True
    )
    assert {i.sample_type_id: i.is_active for i in everything} == {
        sample_type.id: True,
        other_sample_type.id: False,
    }


async def test_set_sample_types_rejects_new_inactive_sample_type(
    session: AsyncSession, lab_test_payload: dict, other_sample_type: SampleType
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    await _deactivate(session, other_sample_type)

    with pytest.raises(InactiveReferenceError):
        await controller.set_sample_types(
            session,
            lab_test.id,
            [
                LabTestSampleTypeInput(
                    sample_type_id=other_sample_type.id, is_preferred=True, sort_order=1
                )
            ],
        )


async def test_set_sample_types_keeps_already_assigned_sample_type_deactivated_later(
    session: AsyncSession, lab_test_payload: dict, sample_type: SampleType
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    await _deactivate(session, sample_type)

    kept = await controller.set_sample_types(
        session,
        lab_test.id,
        [
            LabTestSampleTypeInput(
                sample_type_id=sample_type.id, is_preferred=True, sort_order=1
            )
        ],
    )
    assert [row.sample_type_id for row in kept] == [sample_type.id]


async def test_set_consent_documents_rejects_version_of_inactive_document(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    version = await _published_consent_version(session, document_active=False)

    with pytest.raises(InactiveReferenceError):
        await controller.set_consent_documents(
            session,
            lab_test.id,
            [LabTestConsentDocumentInput(consent_document_version_id=version.id)],
        )


async def test_set_consent_documents_diff(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    first = await _published_consent_version(session)
    second = await _published_consent_version(session)

    await controller.set_consent_documents(
        session,
        lab_test.id,
        [LabTestConsentDocumentInput(consent_document_version_id=first.id)],
    )
    result = await controller.set_consent_documents(
        session,
        lab_test.id,
        [
            LabTestConsentDocumentInput(
                consent_document_version_id=second.id, is_mandatory=False
            )
        ],
    )

    assert [(i.consent_document_version_id, i.is_mandatory) for i in result] == [
        (second.id, False)
    ]
    everything = await controller.get_consent_documents(
        session, lab_test.id, include_inactive=True
    )
    assert {i.consent_document_version_id: i.is_active for i in everything} == {
        first.id: False,
        second.id: True,
    }


async def test_detail_embeds_only_active_associations(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    lab_test = await _lab_test(session, lab_test_payload)
    a = await _precondition(session)
    b = await _precondition(session)
    await controller.set_preconditions(
        session, lab_test.id, [_precondition_input(a.id), _precondition_input(b.id, 2)]
    )
    await controller.set_preconditions(
        session, lab_test.id, [_precondition_input(b.id)]
    )

    detail = await controller.get_lab_test(session, lab_test.id)
    assert [item.precondition_id for item in detail.preconditions] == [b.id]


async def test_http_get_preconditions_include_inactive(
    client: AsyncClient, session: AsyncSession, lab_test_payload: dict
) -> None:
    created = (await client.post("/api/v1/lab-tests", json=lab_test_payload)).json()
    a = await _precondition(session)
    b = await _precondition(session)
    url = f"/api/v1/lab-tests/{created['id']}/preconditions"
    await client.put(
        url,
        json=[
            {"precondition_id": str(a.id), "sort_order": 1},
            {"precondition_id": str(b.id), "sort_order": 2},
        ],
    )
    put = await client.put(url, json=[{"precondition_id": str(b.id), "sort_order": 1}])
    assert put.status_code == 200

    active_only = (await client.get(url)).json()
    everything = (await client.get(url, params={"include_inactive": True})).json()

    assert [i["precondition_id"] for i in active_only] == [str(b.id)]
    assert {i["precondition_id"]: i["is_active"] for i in everything} == {
        str(a.id): False,
        str(b.id): True,
    }


async def test_http_create_with_inactive_area_returns_422_inactive_reference(
    client: AsyncClient, session: AsyncSession, lab_test_payload: dict, lab_area
) -> None:
    await _deactivate(session, lab_area)

    response = await client.post("/api/v1/lab-tests", json=lab_test_payload)

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "inactive_reference"
    assert body["message"] == f"El área «{lab_area.code}» está inactiva."
