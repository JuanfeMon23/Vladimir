"""Fixtures de test del modulo `lab_tests`: BD real local, aislada por test.
Mismo patron que `app/modules/lab_areas/tests/conftest.py`.

`lab_tests` depende de `lab_areas`, `preconditions`, `samples`,
`print_labels`, `result_templates` y `consent_documents`: las fixtures de
catalogo/version de esos modulos se crean aqui directamente via sus
`models`, mismo patron de `lab_areas/tests/conftest.py` con `Staff`.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consent_documents.models import ConsentDocument, ConsentDocumentVersion
from app.modules.lab_areas.models import LabArea
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabel, PrintLabelVersion
from app.modules.result_templates.models import ResultTemplate, ResultTemplateVersion
from app.modules.samples.models import Sample, SampleType


def unique_code(prefix: str) -> str:
    """Genera un `code` unico para aislar los tests de filas preexistentes."""
    return f"{prefix}-{uuid4().hex[:24]}"


@pytest_asyncio.fixture
async def lab_area(session: AsyncSession) -> LabArea:
    area = LabArea(code=unique_code("area"), name="Quimica clinica", is_active=True)
    session.add(area)
    await session.commit()
    await session.refresh(area)
    return area


@pytest.fixture
def lab_test_payload(lab_area: LabArea, sample_type: SampleType) -> dict:
    """Body valido de `POST /lab-tests`: un examen siempre nace con al menos
    un tipo de muestra (exactamente uno preferido)."""
    return {
        "code": unique_code("lab-test"),
        "name": "Hemograma completo",
        "abbreviation": "HEM",
        "description": "Conteo celular completo",
        "area_id": str(lab_area.id),
        "method": "Citometria de flujo",
        "turnaround_hours": 4,
        "loinc_code": "58410-2",
        "cups_code": "902210",
        "sample_types": [
            {
                "sample_type_id": str(sample_type.id),
                "is_preferred": True,
                "sort_order": 1,
            }
        ],
    }


@pytest_asyncio.fixture
async def precondition(session: AsyncSession) -> Precondition:
    precondition = Precondition(
        code=unique_code("precond"),
        name="Ayuno de 8 horas",
        description="Ayuno previo a la toma de muestra",
        kind="precondition",
        category="ayuno",
        duration_value=8,
        duration_unit="horas",
        patient_instructions="No consumir alimentos ni bebidas, excepto agua.",
        is_active=True,
    )
    session.add(precondition)
    await session.commit()
    await session.refresh(precondition)
    return precondition


@pytest_asyncio.fixture
async def sample(session: AsyncSession) -> Sample:
    sample = Sample(code=unique_code("sample"), name="Sangre")
    session.add(sample)
    await session.commit()
    await session.refresh(sample)
    return sample


@pytest_asyncio.fixture
async def sample_type(session: AsyncSession, sample: Sample) -> SampleType:
    sample_type = SampleType(
        sample_id=sample.id,
        code=unique_code("sample-type"),
        name="Tubo tapa roja",
        specimen="suero",
        is_active=True,
    )
    session.add(sample_type)
    await session.commit()
    await session.refresh(sample_type)
    return sample_type


@pytest_asyncio.fixture
async def other_sample_type(session: AsyncSession, sample: Sample) -> SampleType:
    sample_type = SampleType(
        sample_id=sample.id,
        code=unique_code("sample-type"),
        name="Tubo tapa lila",
        specimen="sangre_total",
        is_active=True,
    )
    session.add(sample_type)
    await session.commit()
    await session.refresh(sample_type)
    return sample_type


@pytest_asyncio.fixture
async def print_label(session: AsyncSession) -> PrintLabel:
    label = PrintLabel(code=unique_code("print-label"), name="Etiqueta de tubo")
    session.add(label)
    await session.commit()
    await session.refresh(label)
    return label


@pytest_asyncio.fixture
async def published_print_label_version(
    session: AsyncSession, print_label: PrintLabel
) -> PrintLabelVersion:
    version = PrintLabelVersion(
        print_label_id=print_label.id,
        version_number=1,
        status="published",
        published_at=datetime.now(UTC),
        width_mm=40,
        height_mm=25,
        dpi=203,
        output_format="zpl",
        copies=1,
        template_content="^XA^FD{{code}}^FS^XZ",
        placeholders={"code": "Codigo de la muestra"},
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@pytest_asyncio.fixture
async def draft_print_label_version(
    session: AsyncSession, print_label: PrintLabel
) -> PrintLabelVersion:
    version = PrintLabelVersion(
        print_label_id=print_label.id,
        version_number=2,
        status="draft",
        width_mm=40,
        height_mm=25,
        dpi=203,
        output_format="zpl",
        copies=1,
        template_content="^XA^FD{{code}}^FS^XZ",
        placeholders={"code": "Codigo de la muestra"},
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@pytest_asyncio.fixture
async def result_template(session: AsyncSession) -> ResultTemplate:
    template = ResultTemplate(
        code=unique_code("result-template"), name="Plantilla basica"
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@pytest_asyncio.fixture
async def published_result_template_version(
    session: AsyncSession, result_template: ResultTemplate
) -> ResultTemplateVersion:
    version = ResultTemplateVersion(
        result_template_id=result_template.id,
        version_number=1,
        status="published",
        published_at=datetime.now(UTC),
        report_settings={},
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@pytest_asyncio.fixture
async def draft_result_template_version(
    session: AsyncSession, result_template: ResultTemplate
) -> ResultTemplateVersion:
    version = ResultTemplateVersion(
        result_template_id=result_template.id,
        version_number=2,
        status="draft",
        report_settings={},
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@pytest_asyncio.fixture
async def consent_document(session: AsyncSession) -> ConsentDocument:
    document = ConsentDocument(
        code=unique_code("consent-document"),
        name="Consentimiento informado general",
        document_type="consentimiento_informado",
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


@pytest_asyncio.fixture
async def published_consent_document_version(
    session: AsyncSession, consent_document: ConsentDocument
) -> ConsentDocumentVersion:
    version = ConsentDocumentVersion(
        consent_document_id=consent_document.id,
        version_number=1,
        status="published",
        published_at=datetime.now(UTC),
        content="Acepto el procedimiento descrito.",
        signer="paciente",
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version


@pytest_asyncio.fixture
async def draft_consent_document_version(
    session: AsyncSession, consent_document: ConsentDocument
) -> ConsentDocumentVersion:
    version = ConsentDocumentVersion(
        consent_document_id=consent_document.id,
        version_number=2,
        status="draft",
        content="Borrador sin publicar.",
        signer="paciente",
    )
    session.add(version)
    await session.commit()
    await session.refresh(version)
    return version
