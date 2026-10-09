"""Tests del controller de `consent_documents` (sin HTTP). Cubre el ciclo
de vida completo de version: draft -> published -> retired, mas los errores
de negocio.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError, ValidationAppError
from app.core.versioning import VersionDraftExistsError, VersionMissingFieldsError
from app.modules.consent_documents import controller
from app.modules.consent_documents.schemas import (
    ConsentDocumentCreate,
    ConsentDocumentUpdate,
    ConsentDocumentVersionCreate,
    ConsentDocumentVersionUpdate,
)


async def test_create_consent_document(
    session: AsyncSession, consent_document_payload: dict
) -> None:
    created = await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    assert created.code == consent_document_payload["code"]
    assert created.is_active is True


async def test_create_consent_document_duplicate_code_raises_conflict(
    session: AsyncSession, consent_document_payload: dict
) -> None:
    await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    with pytest.raises(CodeConflictError, match="Ya existe un documento con el código"):
        await controller.create_document(
            session, ConsentDocumentCreate(**consent_document_payload)
        )


async def test_get_consent_document_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe un documento con id"):
        await controller.get_document(session, uuid4())


async def test_update_consent_document(
    session: AsyncSession, consent_document_payload: dict
) -> None:
    created = await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    updated = await controller.update_document(
        session, created.id, ConsentDocumentUpdate(name="Consentimiento (nuevo)")
    )

    assert updated.name == "Consentimiento (nuevo)"
    assert updated.code == consent_document_payload["code"]


async def test_create_first_version_missing_fields_raises(
    session: AsyncSession, consent_document_payload: dict
) -> None:
    document = await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    with pytest.raises(VersionMissingFieldsError):
        await controller.create_version(
            session,
            document.id,
            ConsentDocumentVersionCreate(change_notes="incompleta"),
        )


async def test_create_version_under_missing_document_raises_not_found(
    session: AsyncSession, consent_document_version_payload: dict
) -> None:
    with pytest.raises(NotFoundError, match="No existe un documento con id"):
        await controller.create_version(
            session,
            uuid4(),
            ConsentDocumentVersionCreate(**consent_document_version_payload),
        )


async def test_full_version_lifecycle(
    session: AsyncSession,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document = await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    # Primer draft: version 1, creada desde cero (no hay nada que clonar).
    first_draft = await controller.create_version(
        session,
        document.id,
        ConsentDocumentVersionCreate(**consent_document_version_payload),
    )
    assert first_draft.version_number == 1
    assert first_draft.status == "draft"

    # Editar el borrador.
    edited = await controller.update_version(
        session,
        document.id,
        first_draft.id,
        ConsentDocumentVersionUpdate(signer="paciente_o_representante"),
    )
    assert edited.signer == "paciente_o_representante"

    # Publicar fija `published_at` y la vuelve inmutable.
    published = await controller.publish_version(session, document.id, first_draft.id)
    assert published.status == "published"
    assert published.published_at is not None

    with pytest.raises(ValidationAppError):
        await controller.update_version(
            session,
            document.id,
            first_draft.id,
            ConsentDocumentVersionUpdate(signer="paciente"),
        )

    # Segundo draft: clona la version publicada.
    second_draft = await controller.create_version(
        session, document.id, ConsentDocumentVersionCreate(change_notes="v2")
    )
    assert second_draft.version_number == 2
    assert second_draft.status == "draft"
    assert second_draft.content == consent_document_version_payload["content"]
    assert second_draft.change_notes == "v2"

    # No se puede crear un tercer draft mientras el segundo siga abierto.
    with pytest.raises(VersionDraftExistsError):
        await controller.create_version(
            session,
            document.id,
            ConsentDocumentVersionCreate(change_notes="v3 prematura"),
        )

    second_published = await controller.publish_version(
        session, document.id, second_draft.id
    )
    assert second_published.status == "published"

    # Retirar la primera version (ya publicada, no la mas reciente).
    retired = await controller.retire_version(session, document.id, first_draft.id)
    assert retired.status == "retired"

    with pytest.raises(ValidationAppError):
        await controller.retire_version(session, document.id, first_draft.id)


async def test_get_version_under_wrong_document_raises_not_found(
    session: AsyncSession,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document = await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )
    version = await controller.create_version(
        session,
        document.id,
        ConsentDocumentVersionCreate(**consent_document_version_payload),
    )

    other_payload = {
        **consent_document_payload,
        "code": f"{consent_document_payload['code']}-2",
    }
    other_document = await controller.create_document(
        session, ConsentDocumentCreate(**other_payload)
    )

    with pytest.raises(NotFoundError, match="No existe una version con id"):
        await controller.update_version(
            session,
            other_document.id,
            version.id,
            ConsentDocumentVersionUpdate(signer="paciente"),
        )


async def test_list_versions_under_missing_document_raises_not_found(
    session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError, match="No existe un documento con id"):
        await controller.list_versions(
            session, uuid4(), PaginationParams(page=1, page_size=50)
        )


async def test_list_consent_documents(
    session: AsyncSession, consent_document_payload: dict
) -> None:
    await controller.create_document(
        session, ConsentDocumentCreate(**consent_document_payload)
    )

    page = await controller.list_documents(
        session, PaginationParams(page=1, page_size=50), ActiveOnlyFilter(active=None)
    )

    assert any(item.code == consent_document_payload["code"] for item in page.items)


async def test_create_version_under_inactive_document_raises_inactive_reference(
    session: AsyncSession,
    consent_document_payload: dict,
    consent_document_version_payload: dict,
) -> None:
    document = await controller.create_document(
        session,
        ConsentDocumentCreate(**{**consent_document_payload, "is_active": False}),
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_version(
            session,
            document.id,
            ConsentDocumentVersionCreate(**consent_document_version_payload),
        )
    assert exc_info.value.details == {"consent_document_id": str(document.id)}
