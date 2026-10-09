"""Casos de uso / logica de negocio del modulo `lab_tests`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`, solo excepciones
de `app.modules.lab_tests.exceptions` que el nucleo traduce a HTTP.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active
from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError, ValidationAppError
from app.core.repository import get_by_ids, get_or_404, update_entity
from app.core.schemas import Page
from app.core.versioning import PUBLISHED, register_version_usage
from app.modules.consent_documents import DATA_TREATMENT_TYPE
from app.modules.consent_documents.models import ConsentDocument, ConsentDocumentVersion
from app.modules.lab_areas.models import LabArea
from app.modules.lab_tests import repository
from app.modules.lab_tests.exceptions import (
    LabTestSampleTypePreferredCountError,
    LabTestSampleTypesRequiredError,
)
from app.modules.lab_tests.models import (
    LabTest,
    LabTestPrecondition,
    LabTestSampleType,
)
from app.modules.lab_tests.schemas import (
    LabTestConsentDocumentInput,
    LabTestConsentDocumentRead,
    LabTestCreate,
    LabTestPreconditionInput,
    LabTestPreconditionRead,
    LabTestRead,
    LabTestSampleTypeInput,
    LabTestSampleTypeRead,
    LabTestUpdate,
)
from app.modules.preconditions.models import Precondition
from app.modules.print_labels.models import PrintLabel, PrintLabelVersion
from app.modules.result_templates.models import ResultTemplate, ResultTemplateVersion
from app.modules.samples.models import SampleType


def _invalid_ids(message: str, invalid_ids: list[str]) -> ValidationAppError:
    """422 por ids del body que no existen (o no estan publicados)."""
    return ValidationAppError(
        message=f"{message}: {', '.join(invalid_ids)}.",
        details={"invalid_ids": invalid_ids},
    )


def _resolve_precondition(
    row: LabTestPrecondition, catalog: Precondition
) -> LabTestPreconditionRead:
    """Valor efectivo de una precondicion asignada: el override si existe,
    si no el del catalogo `preconditions`. Primer uso de este patron en el
    proyecto (ver `backend/app/core/CATALOG.md` "Resolucion de overrides");
    se generaliza a `core/utils.py` si un 2do modulo lo necesita, no antes.
    """
    return LabTestPreconditionRead(
        id=row.id,
        precondition_id=row.precondition_id,
        is_mandatory=row.is_mandatory,
        sort_order=row.sort_order,
        is_active=row.is_active,
        name=row.name_override or catalog.name,
        description=row.description_override or catalog.description,
        duration_value=(
            row.duration_value_override
            if row.duration_value_override is not None
            else catalog.duration_value
        ),
        duration_unit=row.duration_unit_override or catalog.duration_unit,
        patient_instructions=(
            row.patient_instructions_override or catalog.patient_instructions
        ),
        name_override=row.name_override,
        description_override=row.description_override,
        duration_value_override=row.duration_value_override,
        duration_unit_override=row.duration_unit_override,
        patient_instructions_override=row.patient_instructions_override,
    )


async def _resolve_preconditions(
    session: AsyncSession, rows: list[LabTestPrecondition]
) -> list[LabTestPreconditionRead]:
    catalog = await get_by_ids(
        session, Precondition, [row.precondition_id for row in rows]
    )
    return [_resolve_precondition(row, catalog[row.precondition_id]) for row in rows]


async def _validate_area(session: AsyncSession, area_id: UUID) -> None:
    area = await session.get(LabArea, area_id)
    if area is None:
        raise ValidationAppError(
            message=f"No existe un area con id '{area_id}'.",
            details={"area_id": str(area_id)},
        )
    ensure_active(area, subject="el área", field="area_id", feminine=True)


async def _validate_print_label_version(
    session: AsyncSession, version_id: UUID
) -> None:
    """Publicada y de una etiqueta activa."""
    version = await session.get(PrintLabelVersion, version_id)
    if version is None or version.status != PUBLISHED:
        raise ValidationAppError(
            message=(
                f"La version de etiqueta '{version_id}' no existe o no esta publicada."
            ),
            details={"print_label_version_id": str(version_id)},
        )
    label = await session.get(PrintLabel, version.print_label_id)
    ensure_active(label, subject="la etiqueta", field="print_label_id", feminine=True)


async def _validate_result_template_version(
    session: AsyncSession, version_id: UUID
) -> None:
    """Publicada y de una plantilla activa."""
    version = await session.get(ResultTemplateVersion, version_id)
    if version is None or version.status != PUBLISHED:
        raise ValidationAppError(
            message=(
                f"La version de plantilla de resultados '{version_id}' no "
                "existe o no esta publicada."
            ),
            details={"result_template_version_id": str(version_id)},
        )
    template = await session.get(ResultTemplate, version.result_template_id)
    ensure_active(
        template, subject="la plantilla", field="result_template_id", feminine=True
    )


def _active_keys(rows: list, key: str) -> set[UUID]:
    """Claves ya asociadas y activas: las unicas que no se validan contra
    el catalogo al reemplazar el set (la relacion existente se conserva
    aunque el elemento se haya desactivado despues)."""
    return {getattr(row, key) for row in rows if row.is_active}


async def list_lab_tests(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    area_id: UUID | None,
    search: SearchFilter = NO_SEARCH,
) -> Page[LabTestRead]:
    """Listado "resumen": no embebe precondiciones/tipos de muestra/
    documentos (evita resolverlos para cada fila de cada pagina). El detalle
    completo esta en `get_lab_test`."""
    items, total = await repository.list_lab_tests(
        session, pagination, active_filter, area_id, search
    )
    return Page[LabTestRead](
        items=[LabTestRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


async def create_lab_test(session: AsyncSession, data: LabTestCreate) -> LabTestRead:
    existing = await repository.get_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un examen", data.code)

    await _validate_area(session, data.area_id)
    if data.print_label_version_id is not None:
        await _validate_print_label_version(session, data.print_label_version_id)
    if data.result_template_version_id is not None:
        await _validate_result_template_version(
            session, data.result_template_version_id
        )

    sample_types = await _validate_sample_types(session, data.sample_types, [])

    lab_test = await repository.create(session, data, sample_types)
    return await get_lab_test(session, lab_test.id)


async def get_lab_test(session: AsyncSession, lab_test_id: UUID) -> LabTestRead:
    """Detalle completo: precondiciones (valor efectivo resuelto), tipos de
    muestra y documentos embebidos, sin N+1 (una consulta por coleccion mas
    una bulk para el catalogo de precondiciones)."""
    lab_test = await get_or_404(session, LabTest, lab_test_id, "un examen")

    precondition_rows = await repository.list_preconditions(session, lab_test.id)
    preconditions = await _resolve_preconditions(session, precondition_rows)

    sample_type_rows = await repository.list_sample_types(session, lab_test.id)
    sample_types = [
        LabTestSampleTypeRead.model_validate(row) for row in sample_type_rows
    ]

    consent_document_rows = await repository.list_consent_documents(
        session, lab_test.id
    )
    consent_documents = [
        LabTestConsentDocumentRead.model_validate(row) for row in consent_document_rows
    ]

    base = LabTestRead.model_validate(lab_test)
    return base.model_copy(
        update={
            "preconditions": preconditions,
            "sample_types": sample_types,
            "consent_documents": consent_documents,
        }
    )


async def update_lab_test(
    session: AsyncSession, lab_test_id: UUID, data: LabTestUpdate
) -> LabTestRead:
    lab_test = await get_or_404(session, LabTest, lab_test_id, "un examen")
    changes = data.model_dump(exclude_unset=True)

    new_code = changes.get("code")
    if new_code is not None and new_code != lab_test.code:
        existing = await repository.get_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un examen", new_code)

    def changed(field: str) -> bool:
        """Solo una referencia NUEVA se valida: reenviar la misma (aunque se
        haya desactivado/retirado despues) conserva la relacion existente."""
        value = changes.get(field)
        return value is not None and value != getattr(lab_test, field)

    if changed("area_id"):
        await _validate_area(session, changes["area_id"])
    if changed("print_label_version_id"):
        await _validate_print_label_version(session, changes["print_label_version_id"])
    if changed("result_template_version_id"):
        await _validate_result_template_version(
            session, changes["result_template_version_id"]
        )

    lab_test = await update_entity(session, lab_test, data)
    return LabTestRead.model_validate(lab_test)


# --- lab_test_preconditions ---


async def get_preconditions(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestPreconditionRead]:
    await get_or_404(session, LabTest, lab_test_id, "un examen")
    rows = await repository.list_preconditions(
        session, lab_test_id, include_inactive=include_inactive
    )
    return await _resolve_preconditions(session, rows)


async def set_preconditions(
    session: AsyncSession,
    lab_test_id: UUID,
    items: list[LabTestPreconditionInput],
) -> list[LabTestPreconditionRead]:
    """Reemplaza el set: lo quitado se desactiva, lo que vuelve reactiva su
    fila, lo nuevo se inserta. Solo lo AGREGADO debe estar activo."""
    await get_or_404(session, LabTest, lab_test_id, "un examen")

    precondition_ids = [item.precondition_id for item in items]
    catalog = await get_by_ids(session, Precondition, precondition_ids)
    missing = [str(pid) for pid in precondition_ids if pid not in catalog]
    if missing:
        raise _invalid_ids("Las siguientes precondiciones no existen", missing)

    current = await repository.list_preconditions(
        session, lab_test_id, include_inactive=True
    )
    kept = _active_keys(current, "precondition_id")
    for precondition_id in precondition_ids:
        if precondition_id not in kept:
            ensure_active(
                catalog[precondition_id],
                subject="la precondición",
                field="precondition_id",
                feminine=True,
            )

    desired = {
        item.precondition_id: item.model_dump(exclude={"precondition_id"})
        for item in items
    }
    saved_rows = await repository.replace_preconditions(session, lab_test_id, desired)
    return await _resolve_preconditions(session, saved_rows)


# --- lab_test_sample_types ---


async def _validate_sample_types(
    session: AsyncSession,
    items: list[LabTestSampleTypeInput],
    current: list[LabTestSampleType],
) -> dict[UUID, dict]:
    """Regla unica de los tipos de muestra de un examen, compartida por
    `create_lab_test` y `set_sample_types`: al menos uno, exactamente un
    preferido, todos existentes y (los NUEVOS respecto de `current`, las filas
    ya asociadas) activos. Devuelve el set deseado `{sample_type_id: valores}`.
    """
    if not items:
        raise LabTestSampleTypesRequiredError
    preferred_count = sum(1 for item in items if item.is_preferred)
    if preferred_count != 1:
        raise LabTestSampleTypePreferredCountError(preferred_count)

    sample_type_ids = [item.sample_type_id for item in items]
    catalog = await get_by_ids(session, SampleType, sample_type_ids)
    missing = [str(sid) for sid in sample_type_ids if sid not in catalog]
    if missing:
        raise _invalid_ids("Los siguientes tipos de muestra no existen", missing)

    kept = _active_keys(current, "sample_type_id")
    for sample_type_id in sample_type_ids:
        if sample_type_id not in kept:
            ensure_active(
                catalog[sample_type_id],
                subject="el tipo de muestra",
                field="sample_type_id",
            )

    return {
        item.sample_type_id: item.model_dump(exclude={"sample_type_id"})
        for item in items
    }


async def get_sample_types(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestSampleTypeRead]:
    await get_or_404(session, LabTest, lab_test_id, "un examen")
    rows = await repository.list_sample_types(
        session, lab_test_id, include_inactive=include_inactive
    )
    return [LabTestSampleTypeRead.model_validate(row) for row in rows]


async def set_sample_types(
    session: AsyncSession,
    lab_test_id: UUID,
    items: list[LabTestSampleTypeInput],
) -> list[LabTestSampleTypeRead]:
    await get_or_404(session, LabTest, lab_test_id, "un examen")

    current = await repository.list_sample_types(
        session, lab_test_id, include_inactive=True
    )
    desired = await _validate_sample_types(session, items, current)
    saved_rows = await repository.replace_sample_types(session, lab_test_id, desired)
    return [LabTestSampleTypeRead.model_validate(row) for row in saved_rows]


# --- lab_test_consent_documents ---


async def get_consent_documents(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestConsentDocumentRead]:
    await get_or_404(session, LabTest, lab_test_id, "un examen")
    rows = await repository.list_consent_documents(
        session, lab_test_id, include_inactive=include_inactive
    )
    return [LabTestConsentDocumentRead.model_validate(row) for row in rows]


async def set_consent_documents(
    session: AsyncSession,
    lab_test_id: UUID,
    items: list[LabTestConsentDocumentInput],
) -> list[LabTestConsentDocumentRead]:
    await get_or_404(session, LabTest, lab_test_id, "un examen")

    version_ids = [item.consent_document_version_id for item in items]
    catalog = await get_by_ids(session, ConsentDocumentVersion, version_ids)
    invalid = [
        str(vid)
        for vid in version_ids
        if vid not in catalog or catalog[vid].status != PUBLISHED
    ]
    if invalid:
        raise _invalid_ids(
            "Las siguientes versiones de documento no existen o no estan publicadas",
            invalid,
        )

    current = await repository.list_consent_documents(
        session, lab_test_id, include_inactive=True
    )
    kept = _active_keys(current, "consent_document_version_id")
    added = [vid for vid in version_ids if vid not in kept]
    documents = await get_by_ids(
        session, ConsentDocument, [catalog[vid].consent_document_id for vid in added]
    )
    general = [
        str(vid)
        for vid in added
        if documents[catalog[vid].consent_document_id].document_type
        == DATA_TREATMENT_TYPE
    ]
    if general:
        raise ValidationAppError(
            message=(
                "El consentimiento general de tratamiento de datos se firma "
                "antes de cualquier examen; no se asocia a exámenes."
            ),
            details={"invalid_ids": general},
        )
    for vid in added:
        ensure_active(
            documents[catalog[vid].consent_document_id],
            subject="el documento",
            field="consent_document_version_id",
        )

    desired = {
        item.consent_document_version_id: item.model_dump(
            exclude={"consent_document_version_id"}
        )
        for item in items
    }
    saved_rows = await repository.replace_consent_documents(
        session, lab_test_id, desired
    )
    return [LabTestConsentDocumentRead.model_validate(row) for row in saved_rows]


# --- usos de versiones (regla "no retirar mientras la usen examenes activos") ---


def register_version_usages() -> None:
    """Registra en el nucleo que examenes ACTIVOS usan cada tabla de
    versiones, para que `VersioningService.retire` bloquee el retiro sin que
    `print_labels`/`result_templates`/`consent_documents` importen
    `lab_tests` (que ya depende de ellos). Se llama una vez desde
    `app/main.py`; es idempotente.
    """
    for version_table, finder in (
        ("print_label_versions", repository.codes_using_print_label_version),
        ("result_template_versions", repository.codes_using_result_template_version),
        (
            "consent_document_versions",
            repository.codes_using_consent_document_version,
        ),
    ):
        register_version_usage(version_table, finder)
