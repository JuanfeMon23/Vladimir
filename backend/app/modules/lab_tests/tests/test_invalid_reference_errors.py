"""Contrato de los 422 por referencias inexistentes o no publicadas de
`lab_tests`: status, `code`, mensaje (byte a byte) y `details`."""

from collections.abc import Awaitable
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationAppError
from app.modules.consent_documents.models import ConsentDocumentVersion
from app.modules.lab_tests import controller
from app.modules.lab_tests.schemas import (
    LabTestConsentDocumentInput,
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestSampleTypeInput,
    LabTestUpdate,
)
from app.modules.print_labels.models import PrintLabelVersion
from app.modules.result_templates.models import ResultTemplateVersion


async def _rejected(call: Awaitable) -> ValidationAppError:
    with pytest.raises(ValidationAppError) as exc_info:
        await call
    error = exc_info.value
    assert error.status_code == 422
    assert error.code == "validation_error"
    return error


async def test_area_inexistente(session: AsyncSession, lab_test_payload: dict) -> None:
    area_id = str(uuid4())
    payload = {**lab_test_payload, "area_id": area_id}

    error = await _rejected(
        controller.create_lab_test(session, LabTestCreate(**payload))
    )

    assert error.message == f"No existe un area con id '{area_id}'."
    assert error.details == {"area_id": area_id}


async def test_version_de_etiqueta_no_publicada(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_print_label_version: PrintLabelVersion,
) -> None:
    version_id = str(draft_print_label_version.id)
    payload = {**lab_test_payload, "print_label_version_id": version_id}

    error = await _rejected(
        controller.create_lab_test(session, LabTestCreate(**payload))
    )

    assert error.message == (
        f"La version de etiqueta '{version_id}' no existe o no esta publicada."
    )
    assert error.details == {"print_label_version_id": version_id}


async def test_version_de_plantilla_no_publicada(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_result_template_version: ResultTemplateVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )
    version_id = str(draft_result_template_version.id)

    error = await _rejected(
        controller.update_lab_test(
            session,
            created.id,
            LabTestUpdate(result_template_version_id=draft_result_template_version.id),
        )
    )

    assert error.message == (
        f"La version de plantilla de resultados '{version_id}' no existe o no "
        "esta publicada."
    )
    assert error.details == {"result_template_version_id": version_id}


async def test_precondiciones_inexistentes(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )
    ids = [uuid4(), uuid4()]
    items = [LabTestPreconditionInput(precondition_id=i, sort_order=1) for i in ids]

    error = await _rejected(controller.set_preconditions(session, created.id, items))

    listed = ", ".join(str(i) for i in ids)
    assert error.message == f"Las siguientes precondiciones no existen: {listed}."
    assert error.details == {"invalid_ids": [str(i) for i in ids]}


async def test_tipos_de_muestra_inexistentes(
    session: AsyncSession, lab_test_payload: dict
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )
    missing_id = uuid4()
    items = [
        LabTestSampleTypeInput(
            sample_type_id=missing_id, is_preferred=True, sort_order=1
        )
    ]

    error = await _rejected(controller.set_sample_types(session, created.id, items))

    assert error.message == (
        f"Los siguientes tipos de muestra no existen: {missing_id}."
    )
    assert error.details == {"invalid_ids": [str(missing_id)]}


async def test_version_de_documento_no_publicada(
    session: AsyncSession,
    lab_test_payload: dict,
    draft_consent_document_version: ConsentDocumentVersion,
) -> None:
    created = await controller.create_lab_test(
        session, LabTestCreate(**lab_test_payload)
    )
    version_id = str(draft_consent_document_version.id)
    items = [
        LabTestConsentDocumentInput(
            consent_document_version_id=draft_consent_document_version.id
        )
    ]

    error = await _rejected(
        controller.set_consent_documents(session, created.id, items)
    )

    assert error.message == (
        "Las siguientes versiones de documento no existen o no estan publicadas: "
        f"{version_id}."
    )
    assert error.details == {"invalid_ids": [version_id]}
