"""Acceso a datos del modulo `lab_tests`. Unico archivo que arma consultas.

`lab_tests` es el modulo central: depende de `lab_areas`, `preconditions`,
`samples`, `print_labels`, `result_templates` y `consent_documents`, y
ninguno de ellos expone todavia una interfaz publica de consulta (su
`__init__.py` solo expone routers, ver reporte de la tarea). Mismo patron de
deuda documentado en `app.modules.lab_areas.repository` para `staff`: se
importan sus `models` directamente aqui, no se duplican consultas por todo
el proyecto. Si un 2do modulo necesita lo mismo, esa consulta debe moverse
a la interfaz publica del modulo duenio.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.repository import (
    paginate,
    sync_collection,
)
from app.modules.lab_tests.models import (
    LabTest,
    LabTestConsentDocument,
    LabTestPrecondition,
    LabTestSampleType,
)
from app.modules.lab_tests.schemas import LabTestCreate

# --- lab_tests ---


async def get_by_code(session: AsyncSession, code: str) -> LabTest | None:
    stmt = select(LabTest).where(LabTest.code == code)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_lab_tests(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    area_id: UUID | None,
    search: SearchFilter = NO_SEARCH,
) -> tuple[list[LabTest], int]:
    stmt = active_filter.apply(select(LabTest), LabTest.is_active)
    if area_id is not None:
        stmt = stmt.where(LabTest.area_id == area_id)
    stmt = search.apply(
        stmt, LabTest.code, LabTest.name, LabTest.cups_code, LabTest.loinc_code
    )
    return await paginate(session, stmt, pagination, LabTest.name)


async def create(
    session: AsyncSession, data: LabTestCreate, sample_types: dict[UUID, dict]
) -> LabTest:
    """Examen + sus tipos de muestra en UNA transaccion (un solo commit): si
    algo falla no queda un examen sin tipo de muestra."""
    lab_test = LabTest(**data.model_dump(exclude={"sample_types"}))
    session.add(lab_test)
    await session.flush()
    session.add_all(
        LabTestSampleType(lab_test_id=lab_test.id, sample_type_id=key, **values)
        for key, values in sample_types.items()
    )
    await session.commit()
    await session.refresh(lab_test)
    return lab_test


# --- validacion de referencias externas (area, versiones publicadas) ---


# --- colecciones del examen: set completo sin borrar (ver `sync_collection`) ---


def _only_active(stmt, column, include_inactive: bool):
    return stmt if include_inactive else stmt.where(column.is_(True))


async def list_preconditions(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestPrecondition]:
    stmt = _only_active(
        select(LabTestPrecondition).where(
            LabTestPrecondition.lab_test_id == lab_test_id
        ),
        LabTestPrecondition.is_active,
        include_inactive,
    )
    stmt = stmt.order_by(LabTestPrecondition.sort_order, LabTestPrecondition.id)
    return list((await session.execute(stmt)).scalars().all())


async def replace_preconditions(
    session: AsyncSession, lab_test_id: UUID, desired: dict[UUID, dict]
) -> list[LabTestPrecondition]:
    """Reemplaza el set completo en una sola transaccion (ver AGENTS.md
    "Transacciones"): lo quitado se desactiva, lo que vuelve se reactiva."""
    rows = await list_preconditions(session, lab_test_id, include_inactive=True)
    await sync_collection(
        session,
        rows,
        "precondition_id",
        desired,
        lambda key, values: LabTestPrecondition(
            lab_test_id=lab_test_id, precondition_id=key, **values
        ),
    )
    await session.commit()
    return await list_preconditions(session, lab_test_id)


async def list_sample_types(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestSampleType]:
    stmt = _only_active(
        select(LabTestSampleType).where(LabTestSampleType.lab_test_id == lab_test_id),
        LabTestSampleType.is_active,
        include_inactive,
    )
    stmt = stmt.order_by(LabTestSampleType.sort_order, LabTestSampleType.id)
    return list((await session.execute(stmt)).scalars().all())


async def replace_sample_types(
    session: AsyncSession, lab_test_id: UUID, desired: dict[UUID, dict]
) -> list[LabTestSampleType]:
    rows = await list_sample_types(session, lab_test_id, include_inactive=True)
    # Primero se quita el preferido que deja de serlo: el indice unico
    # parcial (un preferido activo por examen) no admite dos a la vez.
    for row in rows:
        if row.is_preferred and not desired.get(row.sample_type_id, {}).get(
            "is_preferred"
        ):
            row.is_preferred = False
    await session.flush()
    await sync_collection(
        session,
        rows,
        "sample_type_id",
        desired,
        lambda key, values: LabTestSampleType(
            lab_test_id=lab_test_id, sample_type_id=key, **values
        ),
    )
    await session.commit()
    return await list_sample_types(session, lab_test_id)


async def list_consent_documents(
    session: AsyncSession, lab_test_id: UUID, *, include_inactive: bool = False
) -> list[LabTestConsentDocument]:
    stmt = _only_active(
        select(LabTestConsentDocument).where(
            LabTestConsentDocument.lab_test_id == lab_test_id
        ),
        LabTestConsentDocument.is_active,
        include_inactive,
    )
    stmt = stmt.order_by(LabTestConsentDocument.id)
    return list((await session.execute(stmt)).scalars().all())


async def replace_consent_documents(
    session: AsyncSession, lab_test_id: UUID, desired: dict[UUID, dict]
) -> list[LabTestConsentDocument]:
    rows = await list_consent_documents(session, lab_test_id, include_inactive=True)
    await sync_collection(
        session,
        rows,
        "consent_document_version_id",
        desired,
        lambda key, values: LabTestConsentDocument(
            lab_test_id=lab_test_id, consent_document_version_id=key, **values
        ),
    )
    await session.commit()
    return await list_consent_documents(session, lab_test_id)


# --- usos de versiones por examenes activos (ver `core.versioning`) ---


async def _active_lab_test_codes(session: AsyncSession, stmt) -> list[str]:
    stmt = stmt.where(LabTest.is_active.is_(True)).distinct().order_by(LabTest.code)
    return list((await session.execute(stmt)).scalars().all())


async def codes_using_print_label_version(
    session: AsyncSession, version_id: UUID
) -> list[str]:
    return await _active_lab_test_codes(
        session,
        select(LabTest.code).where(LabTest.print_label_version_id == version_id),
    )


async def codes_using_result_template_version(
    session: AsyncSession, version_id: UUID
) -> list[str]:
    return await _active_lab_test_codes(
        session,
        select(LabTest.code).where(LabTest.result_template_version_id == version_id),
    )


async def codes_using_consent_document_version(
    session: AsyncSession, version_id: UUID
) -> list[str]:
    """Solo asignaciones activas (quitar el documento la desactiva)."""
    return await _active_lab_test_codes(
        session,
        select(LabTest.code)
        .join(LabTestConsentDocument, LabTestConsentDocument.lab_test_id == LabTest.id)
        .where(
            LabTestConsentDocument.consent_document_version_id == version_id,
            LabTestConsentDocument.is_active.is_(True),
        ),
    )
