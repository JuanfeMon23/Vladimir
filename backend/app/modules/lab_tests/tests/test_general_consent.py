"""El consentimiento general de tratamiento de datos no se asocia a examenes."""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.consent_documents.models import ConsentDocument, ConsentDocumentVersion

MESSAGE = (
    "El consentimiento general de tratamiento de datos se firma antes de "
    "cualquier examen; no se asocia a exámenes."
)


async def _general_version(
    session: AsyncSession, code: str, *, published: bool = True
) -> ConsentDocumentVersion:
    document = ConsentDocument(
        code=code, name="Datos personales", document_type="tratamiento_datos"
    )
    session.add(document)
    await session.flush()
    version = ConsentDocumentVersion(
        consent_document_id=document.id,
        version_number=1,
        status="published" if published else "draft",
        published_at=datetime.now(UTC) if published else None,
        content="Autorizo el tratamiento de mis datos.",
        signer="paciente",
    )
    session.add(version)
    await session.commit()
    return version


@pytest.mark.usefixtures("no_active_general_consent")
async def test_put_with_general_consent_returns_422(
    client: AsyncClient, session: AsyncSession, lab_test_payload: dict
) -> None:
    version = await _general_version(session, "ZZ-general-put")
    lab_test_id = (
        await client.post("/api/v1/lab-tests", json=lab_test_payload)
    ).json()["id"]

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/consent-documents",
        json=[{"consent_document_version_id": str(version.id)}],
    )

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["message"] == f"{MESSAGE}"
    assert body["details"] == {"invalid_ids": [str(version.id)]}


@pytest.mark.usefixtures("no_active_general_consent")
async def test_put_keeps_already_associated_general_consent(
    client: AsyncClient,
    session: AsyncSession,
    lab_test_payload: dict,
    published_consent_document_version: ConsentDocumentVersion,
) -> None:
    """Lo ya asociado (datos viejos) no rompe un PUT que lo reenvia."""
    from app.modules.lab_tests.models import LabTestConsentDocument

    version = await _general_version(session, "ZZ-general-old")
    lab_test_id = (
        await client.post("/api/v1/lab-tests", json=lab_test_payload)
    ).json()["id"]
    session.add(
        LabTestConsentDocument(
            lab_test_id=lab_test_id, consent_document_version_id=version.id
        )
    )
    await session.commit()

    response = await client.put(
        f"/api/v1/lab-tests/{lab_test_id}/consent-documents",
        json=[
            {"consent_document_version_id": str(version.id)},
            {"consent_document_version_id": str(published_consent_document_version.id)},
        ],
    )

    assert response.status_code == 200, response.text
    assert len(response.json()) == 2
