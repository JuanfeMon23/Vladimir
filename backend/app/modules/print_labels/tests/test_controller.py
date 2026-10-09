"""Tests del controller de `print_labels` (sin HTTP). Cubre el ciclo de vida
completo de version: draft -> published -> retired, mas los errores de
negocio.
"""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import InactiveReferenceError
from app.core.dependencies import ActiveOnlyFilter, PaginationParams
from app.core.exceptions import CodeConflictError, NotFoundError, ValidationAppError
from app.core.versioning import VersionDraftExistsError, VersionMissingFieldsError
from app.modules.print_labels import controller
from app.modules.print_labels.schemas import (
    PrintLabelCreate,
    PrintLabelUpdate,
    PrintLabelVersionCreate,
    PrintLabelVersionUpdate,
)


async def test_create_print_label(
    session: AsyncSession, print_label_payload: dict
) -> None:
    created = await controller.create_label(
        session, PrintLabelCreate(**print_label_payload)
    )

    assert created.code == print_label_payload["code"]
    assert created.is_active is True


async def test_create_print_label_duplicate_code_raises_conflict(
    session: AsyncSession, print_label_payload: dict
) -> None:
    await controller.create_label(session, PrintLabelCreate(**print_label_payload))

    with pytest.raises(CodeConflictError, match="Ya existe una etiqueta con el código"):
        await controller.create_label(session, PrintLabelCreate(**print_label_payload))


async def test_get_print_label_not_found_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError, match="No existe una etiqueta con id"):
        await controller.get_label(session, uuid4())


async def test_update_print_label(
    session: AsyncSession, print_label_payload: dict
) -> None:
    created = await controller.create_label(
        session, PrintLabelCreate(**print_label_payload)
    )

    updated = await controller.update_label(
        session, created.id, PrintLabelUpdate(name="Etiqueta de tubo (nueva)")
    )

    assert updated.name == "Etiqueta de tubo (nueva)"
    assert updated.code == print_label_payload["code"]


async def test_create_first_version_missing_fields_raises(
    session: AsyncSession, print_label_payload: dict
) -> None:
    label = await controller.create_label(
        session, PrintLabelCreate(**print_label_payload)
    )

    with pytest.raises(VersionMissingFieldsError):
        await controller.create_version(
            session, label.id, PrintLabelVersionCreate(change_notes="incompleta")
        )


async def test_create_version_under_missing_label_raises_not_found(
    session: AsyncSession, print_label_version_payload: dict
) -> None:
    with pytest.raises(NotFoundError, match="No existe una etiqueta con id"):
        await controller.create_version(
            session, uuid4(), PrintLabelVersionCreate(**print_label_version_payload)
        )


async def test_full_version_lifecycle(
    session: AsyncSession,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label = await controller.create_label(
        session, PrintLabelCreate(**print_label_payload)
    )

    # Primer draft: version 1, creada desde cero (no hay nada que clonar).
    first_draft = await controller.create_version(
        session, label.id, PrintLabelVersionCreate(**print_label_version_payload)
    )
    assert first_draft.version_number == 1
    assert first_draft.status == "draft"

    # Editar el borrador.
    edited = await controller.update_version(
        session,
        label.id,
        first_draft.id,
        PrintLabelVersionUpdate(copies=2),
    )
    assert edited.copies == 2

    # Publicar fija `published_at` y la vuelve inmutable.
    published = await controller.publish_version(session, label.id, first_draft.id)
    assert published.status == "published"
    assert published.published_at is not None

    with pytest.raises(ValidationAppError):
        await controller.update_version(
            session, label.id, first_draft.id, PrintLabelVersionUpdate(copies=5)
        )

    # Segundo draft: clona la version publicada.
    second_draft = await controller.create_version(
        session, label.id, PrintLabelVersionCreate(change_notes="v2")
    )
    assert second_draft.version_number == 2
    assert second_draft.status == "draft"
    assert (
        second_draft.template_content == print_label_version_payload["template_content"]
    )
    assert second_draft.change_notes == "v2"

    # No se puede crear un tercer draft mientras el segundo siga abierto.
    with pytest.raises(VersionDraftExistsError):
        await controller.create_version(
            session, label.id, PrintLabelVersionCreate(change_notes="v3 prematura")
        )

    second_published = await controller.publish_version(
        session, label.id, second_draft.id
    )
    assert second_published.status == "published"

    # Retirar la primera version (ya publicada, no la mas reciente).
    retired = await controller.retire_version(session, label.id, first_draft.id)
    assert retired.status == "retired"

    with pytest.raises(ValidationAppError):
        await controller.retire_version(session, label.id, first_draft.id)


async def test_get_version_under_wrong_label_raises_not_found(
    session: AsyncSession,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label = await controller.create_label(
        session, PrintLabelCreate(**print_label_payload)
    )
    version = await controller.create_version(
        session, label.id, PrintLabelVersionCreate(**print_label_version_payload)
    )

    other_payload = {**print_label_payload, "code": f"{print_label_payload['code']}-2"}
    other_label = await controller.create_label(
        session, PrintLabelCreate(**other_payload)
    )

    with pytest.raises(NotFoundError, match="No existe una version con id"):
        await controller.update_version(
            session, other_label.id, version.id, PrintLabelVersionUpdate(copies=3)
        )


async def test_list_versions_under_missing_label_raises_not_found(
    session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError, match="No existe una etiqueta con id"):
        await controller.list_versions(
            session, uuid4(), PaginationParams(page=1, page_size=50)
        )


async def test_list_print_labels(
    session: AsyncSession, print_label_payload: dict
) -> None:
    await controller.create_label(session, PrintLabelCreate(**print_label_payload))

    page = await controller.list_labels(
        session, PaginationParams(page=1, page_size=50), ActiveOnlyFilter(active=None)
    )

    assert any(item.code == print_label_payload["code"] for item in page.items)


async def test_create_version_under_inactive_label_raises_inactive_reference(
    session: AsyncSession,
    print_label_payload: dict,
    print_label_version_payload: dict,
) -> None:
    label = await controller.create_label(
        session, PrintLabelCreate(**{**print_label_payload, "is_active": False})
    )

    with pytest.raises(InactiveReferenceError) as exc_info:
        await controller.create_version(
            session, label.id, PrintLabelVersionCreate(**print_label_version_payload)
        )
    assert exc_info.value.details == {"print_label_id": str(label.id)}
