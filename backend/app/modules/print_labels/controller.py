"""Casos de uso / logica de negocio del modulo `print_labels`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`. Las reglas de
ciclo de vida (`draft` -> `published` -> `retired`) las aplica
`VersioningService` (ver `app.core.versioning`), instanciado una sola vez
para este modulo.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError
from app.core.repository import create_entity, get_or_404, update_entity
from app.core.schemas import Page
from app.core.versioning import VersioningService
from app.modules.print_labels import repository
from app.modules.print_labels.models import PrintLabel, PrintLabelVersion
from app.modules.print_labels.schemas import (
    PrintLabelCreate,
    PrintLabelRead,
    PrintLabelUpdate,
    PrintLabelVersionRead,
    PrintLabelVersionWithOwnerRead,
)

versioning = VersioningService(
    PrintLabelVersion,
    "print_label_id",
    parent_model=PrintLabel,
    parent_noun="etiqueta",
    feminine=True,
    read_schema=PrintLabelVersionRead,
    owner_read_schema=PrintLabelVersionWithOwnerRead,
    # `barcode_type` y `change_notes` son opcionales en cualquier version.
    required_fields=(
        "width_mm",
        "height_mm",
        "dpi",
        "output_format",
        "copies",
        "template_content",
        "placeholders",
    ),
)

# Ciclo de versiones (rutas `/print-labels/{id}/versions...`): lo resuelve el
# servicio generico, este modulo solo declara lo especifico arriba.
list_versions = versioning.list_versions
get_version_with_owner = versioning.read_with_owner
get_version = versioning.read_version
create_version = versioning.create_version
update_version = versioning.update_version
publish_version = versioning.publish_version
retire_version = versioning.retire_version


async def list_labels(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[PrintLabelRead]:
    labels, total = await repository.list_labels(
        session, pagination, active_filter, search
    )
    return Page[PrintLabelRead](
        items=[PrintLabelRead.model_validate(label) for label in labels],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_label(session: AsyncSession, data: PrintLabelCreate) -> PrintLabelRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("una etiqueta", data.code)
    label = await create_entity(session, PrintLabel, data)
    return PrintLabelRead.model_validate(label)


async def get_label(session: AsyncSession, print_label_id: UUID) -> PrintLabelRead:
    label = await get_or_404(session, PrintLabel, print_label_id, "una etiqueta")
    return PrintLabelRead.model_validate(label)


async def update_label(
    session: AsyncSession, print_label_id: UUID, data: PrintLabelUpdate
) -> PrintLabelRead:
    label = await get_or_404(session, PrintLabel, print_label_id, "una etiqueta")

    new_code = data.code
    if new_code is not None and new_code != label.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("una etiqueta", new_code)

    label = await update_entity(session, label, data)
    return PrintLabelRead.model_validate(label)
