"""Casos de uso / logica de negocio del modulo `result_templates`.

No conoce HTTP: no usa `Request` ni lanza `HTTPException`. Las reglas de
ciclo de vida de la version (`draft` -> `published` -> `retired`) las aplica
`VersioningService` (ver `app.core.versioning`), instanciado una sola vez
para este modulo. Secciones, analitos de plantilla y rangos de referencia
solo se pueden crear/editar/desactivar mientras la version este en `draft`
(`versioning.ensure_draft`).

Reglas "nada se elimina, solo se desactiva" (2026-10-02):
- El contenido de una version no se borra: se desactiva por PATCH
  (`is_active`). Listados, publicacion y clonado solo ven lo activo.
- Una referencia NUEVA (analito, unidad, conjunto, opcion, seccion) debe
  existir (`invalid_reference`) y estar activa (`inactive_reference`). Las
  existentes se conservan aunque se desactiven despues; publicar las
  reporta en `details.inactive`.
"""

import math
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.activation import ensure_active, ensure_active_reference
from app.core.dependencies import (
    NO_SEARCH,
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
)
from app.core.exceptions import CodeConflictError, InvalidReferenceError, not_found
from app.core.repository import create_entity, get_by_ids, get_or_404, update_entity
from app.core.schemas import Page
from app.core.versioning import VersioningService
from app.modules.result_templates import repository
from app.modules.result_templates.exceptions import (
    ReferenceRangeBoundsError,
    ReferenceRangeFieldsNotAllowedError,
    ReferenceRangeOverlapError,
    ResultTemplateAnalyteDuplicateError,
    ResultTemplateAnalyteFormulaError,
    ResultTemplateVersionIncompleteError,
)
from app.modules.result_templates.formula import (
    FormulaNode,
    formula_problems,
)
from app.modules.result_templates.models import (
    Analyte,
    ReferenceRange,
    ResultOption,
    ResultOptionSet,
    ResultTemplate,
    ResultTemplateAnalyte,
    ResultTemplateSection,
    ResultTemplateVersion,
    Unit,
)
from app.modules.result_templates.schemas import (
    AnalyteCreate,
    AnalyteRead,
    AnalyteUpdate,
    ReferenceRangeCreate,
    ReferenceRangeRead,
    ReferenceRangeUpdate,
    ResultOptionCreate,
    ResultOptionRead,
    ResultOptionSetCreate,
    ResultOptionSetRead,
    ResultOptionSetUpdate,
    ResultOptionUpdate,
    ResultTemplateAnalyteCreate,
    ResultTemplateAnalyteRead,
    ResultTemplateAnalyteUpdate,
    ResultTemplateCreate,
    ResultTemplateRead,
    ResultTemplateSectionCreate,
    ResultTemplateSectionRead,
    ResultTemplateSectionUpdate,
    ResultTemplateUpdate,
    ResultTemplateVersionRead,
    ResultTemplateVersionWithOwnerRead,
    UnitCreate,
    UnitRead,
    UnitSummary,
    UnitUpdate,
    reference_range_bound_errors,
)


def _option_code_conflict(option_set_id: UUID, code: str) -> CodeConflictError:
    return CodeConflictError(
        "una opción",
        code,
        scope=" en este conjunto",
        extra_details={"option_set_id": str(option_set_id)},
    )


def _is_new_reference(
    changes: Mapping[str, Any], field: str, current: object | None
) -> bool:
    """`field` trae una referencia NUEVA: enviada, no nula y distinta de la
    que ya tiene `current` (reenviar la misma conserva la relacion aunque el
    elemento se haya desactivado despues)."""
    value = changes.get(field)
    if value is None:
        return False
    return current is None or value != getattr(current, field)


def _page[T](items: list[T], total: int, pagination: PaginationParams) -> Page[T]:
    return Page[T](
        items=items, total=total, page=pagination.page, page_size=pagination.page_size
    )


# --------------------------------------------------------------------------
# Units
# --------------------------------------------------------------------------


async def list_units(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[UnitRead]:
    items, total = await repository.list_units(
        session, pagination, active_filter, search
    )
    return _page([UnitRead.model_validate(item) for item in items], total, pagination)


async def create_unit(session: AsyncSession, data: UnitCreate) -> UnitRead:
    if await repository.get_unit_by_code(session, data.code) is not None:
        raise CodeConflictError("una unidad", data.code)
    unit = await create_entity(session, Unit, data)
    return UnitRead.model_validate(unit)


async def get_unit(session: AsyncSession, unit_id: UUID) -> UnitRead:
    return UnitRead.model_validate(
        await get_or_404(session, Unit, unit_id, "una unidad")
    )


async def update_unit(
    session: AsyncSession, unit_id: UUID, data: UnitUpdate
) -> UnitRead:
    unit = await get_or_404(session, Unit, unit_id, "una unidad")
    new_code = data.code
    if (
        new_code is not None
        and new_code != unit.code
        and await repository.get_unit_by_code(session, new_code) is not None
    ):
        raise CodeConflictError("una unidad", new_code)
    unit = await update_entity(session, unit, data)
    return UnitRead.model_validate(unit)


async def _validate_new_unit(session: AsyncSession, unit_id: UUID, field: str) -> None:
    unit = await session.get(Unit, unit_id)
    ensure_active_reference(
        unit, subject="la unidad", field=field, value=unit_id, feminine=True
    )


def _unit_fields(unit: Unit | None, text_field: str, detail_field: str) -> dict:
    """Lectura de la unidad: simbolo (texto, contrato previo) + objeto."""
    if unit is None:
        return {text_field: None, detail_field: None}
    return {text_field: unit.symbol, detail_field: UnitSummary.model_validate(unit)}


# --------------------------------------------------------------------------
# Analytes
# --------------------------------------------------------------------------


async def _analyte_reads(
    session: AsyncSession, analytes: list[Analyte]
) -> list[AnalyteRead]:
    units = await get_by_ids(
        session, Unit, [analyte.default_unit_id for analyte in analytes]
    )
    return [
        AnalyteRead.model_validate(analyte).model_copy(
            update=_unit_fields(
                units.get(analyte.default_unit_id),  # type: ignore[arg-type]
                "default_unit",
                "default_unit_detail",
            )
        )
        for analyte in analytes
    ]


async def _analyte_read(session: AsyncSession, analyte: Analyte) -> AnalyteRead:
    return (await _analyte_reads(session, [analyte]))[0]


async def list_analytes(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[AnalyteRead]:
    items, total = await repository.list_analytes(
        session, pagination, active_filter, search
    )
    return _page(await _analyte_reads(session, items), total, pagination)


async def create_analyte(session: AsyncSession, data: AnalyteCreate) -> AnalyteRead:
    existing = await repository.get_analyte_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un analito", data.code)
    if data.default_unit_id is not None:
        await _validate_new_unit(session, data.default_unit_id, "default_unit_id")
    analyte = await create_entity(session, Analyte, data)
    return await _analyte_read(session, analyte)


async def get_analyte(session: AsyncSession, analyte_id: UUID) -> AnalyteRead:
    analyte = await get_or_404(session, Analyte, analyte_id, "un analito")
    return await _analyte_read(session, analyte)


async def update_analyte(
    session: AsyncSession, analyte_id: UUID, data: AnalyteUpdate
) -> AnalyteRead:
    analyte = await get_or_404(session, Analyte, analyte_id, "un analito")
    changes = data.model_dump(exclude_unset=True)

    new_code = data.code
    if new_code is not None and new_code != analyte.code:
        existing = await repository.get_analyte_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un analito", new_code)
    if _is_new_reference(changes, "default_unit_id", analyte):
        await _validate_new_unit(session, changes["default_unit_id"], "default_unit_id")

    analyte = await update_entity(session, analyte, data)
    return await _analyte_read(session, analyte)


# --------------------------------------------------------------------------
# Result option sets
# --------------------------------------------------------------------------


async def list_option_sets(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[ResultOptionSetRead]:
    items, total = await repository.list_option_sets(
        session, pagination, active_filter, search
    )
    return _page(
        [ResultOptionSetRead.model_validate(item) for item in items], total, pagination
    )


async def create_option_set(
    session: AsyncSession, data: ResultOptionSetCreate
) -> ResultOptionSetRead:
    existing = await repository.get_option_set_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("un conjunto de opciones", data.code)
    option_set = await create_entity(session, ResultOptionSet, data)
    return ResultOptionSetRead.model_validate(option_set)


async def get_option_set(
    session: AsyncSession, option_set_id: UUID
) -> ResultOptionSetRead:
    option_set = await get_or_404(
        session, ResultOptionSet, option_set_id, "un conjunto de opciones"
    )
    return ResultOptionSetRead.model_validate(option_set)


async def update_option_set(
    session: AsyncSession, option_set_id: UUID, data: ResultOptionSetUpdate
) -> ResultOptionSetRead:
    option_set = await get_or_404(
        session, ResultOptionSet, option_set_id, "un conjunto de opciones"
    )

    new_code = data.code
    if new_code is not None and new_code != option_set.code:
        existing = await repository.get_option_set_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("un conjunto de opciones", new_code)

    option_set = await update_entity(session, option_set, data)
    return ResultOptionSetRead.model_validate(option_set)


# --------------------------------------------------------------------------
# Result options (sub-recurso de un option set)
# --------------------------------------------------------------------------


async def list_options(
    session: AsyncSession,
    option_set_id: UUID,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[ResultOptionRead]:
    await get_or_404(session, ResultOptionSet, option_set_id, "un conjunto de opciones")

    items, total = await repository.list_options_by_set(
        session, option_set_id, pagination, active_filter, search
    )
    return _page(
        [ResultOptionRead.model_validate(item) for item in items], total, pagination
    )


async def create_option(
    session: AsyncSession, option_set_id: UUID, data: ResultOptionCreate
) -> ResultOptionRead:
    option_set = await get_or_404(
        session, ResultOptionSet, option_set_id, "un conjunto de opciones"
    )
    ensure_active(option_set, subject="el conjunto de opciones", field="option_set_id")

    existing = await repository.get_option_by_set_and_code(
        session, option_set_id, data.code
    )
    if existing is not None:
        raise _option_code_conflict(option_set_id, data.code)

    option = await create_entity(
        session, ResultOption, data, option_set_id=option_set_id
    )
    return ResultOptionRead.model_validate(option)


async def update_option(
    session: AsyncSession, option_id: UUID, data: ResultOptionUpdate
) -> ResultOptionRead:
    option = await get_or_404(session, ResultOption, option_id, "una opcion")

    new_code = data.code
    if new_code is not None and new_code != option.code:
        existing = await repository.get_option_by_set_and_code(
            session, option.option_set_id, new_code
        )
        if existing is not None:
            raise _option_code_conflict(option.option_set_id, new_code)

    option = await update_entity(session, option, data)
    return ResultOptionRead.model_validate(option)


# --------------------------------------------------------------------------
# Result templates
# --------------------------------------------------------------------------


async def list_templates(
    session: AsyncSession,
    pagination: PaginationParams,
    active_filter: ActiveOnlyFilter,
    search: SearchFilter = NO_SEARCH,
) -> Page[ResultTemplateRead]:
    items, total = await repository.list_templates(
        session, pagination, active_filter, search
    )
    return _page(
        [ResultTemplateRead.model_validate(item) for item in items], total, pagination
    )


async def create_template(
    session: AsyncSession, data: ResultTemplateCreate
) -> ResultTemplateRead:
    existing = await repository.get_template_by_code(session, data.code)
    if existing is not None:
        raise CodeConflictError("una plantilla", data.code)
    template = await create_entity(session, ResultTemplate, data)
    return ResultTemplateRead.model_validate(template)


async def get_template(session: AsyncSession, template_id: UUID) -> ResultTemplateRead:
    template = await get_or_404(session, ResultTemplate, template_id, "una plantilla")
    return ResultTemplateRead.model_validate(template)


async def update_template(
    session: AsyncSession, template_id: UUID, data: ResultTemplateUpdate
) -> ResultTemplateRead:
    template = await get_or_404(session, ResultTemplate, template_id, "una plantilla")

    new_code = data.code
    if new_code is not None and new_code != template.code:
        existing = await repository.get_template_by_code(session, new_code)
        if existing is not None:
            raise CodeConflictError("una plantilla", new_code)

    template = await update_entity(session, template, data)
    return ResultTemplateRead.model_validate(template)


# --------------------------------------------------------------------------
# Result template versions
# --------------------------------------------------------------------------


async def _clone_content(
    session: AsyncSession, source_version_id: UUID, draft_id: UUID
) -> None:
    """Copia al borrador solo el contenido ACTIVO de la version origen
    (secciones, analitos y sus rangos). Las referencias a catalogos
    desactivados si se copian: la publicacion del borrador las bloquea."""
    section_id_map: dict[UUID, UUID] = {}
    for section in await repository.list_sections_by_version(
        session, source_version_id
    ):
        new_section = ResultTemplateSection(
            version_id=draft_id, name=section.name, sort_order=section.sort_order
        )
        session.add(new_section)
        await session.flush()
        section_id_map[section.id] = new_section.id

    analytes = await repository.list_analytes_by_version(session, source_version_id)
    ranges = await repository.list_reference_ranges_by_template_analytes(
        session, [template_analyte.id for template_analyte in analytes]
    )
    for template_analyte in analytes:
        new_template_analyte = ResultTemplateAnalyte(
            version_id=draft_id,
            section_id=section_id_map.get(template_analyte.section_id)  # type: ignore[arg-type]
            if template_analyte.section_id is not None
            else None,
            analyte_id=template_analyte.analyte_id,
            sort_order=template_analyte.sort_order,
            result_type=template_analyte.result_type,
            unit_id=template_analyte.unit_id,
            decimals=template_analyte.decimals,
            option_set_id=template_analyte.option_set_id,
            formula=template_analyte.formula,
            is_required=template_analyte.is_required,
            is_reportable=template_analyte.is_reportable,
            default_value=template_analyte.default_value,
        )
        session.add(new_template_analyte)
        await session.flush()

        for reference_range in ranges[template_analyte.id]:
            session.add(
                ReferenceRange(
                    template_analyte_id=new_template_analyte.id,
                    **{field: getattr(reference_range, field) for field in _RANGE_COPY},
                )
            )


_RANGE_COPY = (
    "sex",
    "age_min",
    "age_max",
    "age_unit",
    "condition",
    "low",
    "high",
    "critical_low",
    "critical_high",
    "expected_option_id",
    "expected_boolean",
    "display_text",
    "interpretation",
)


# --- reglas de reporte por result_type ---

_NUMERIC_RANGE_FIELDS = frozenset({"low", "high", "critical_low", "critical_high"})
_TYPED_RANGE_FIELDS = _NUMERIC_RANGE_FIELDS | {"expected_option_id", "expected_boolean"}

# Campos "tipados" de un rango que admite cada `result_type`; los demas
# (`display_text`, `interpretation`, sexo/edad/condicion) siempre se admiten.
# `titer` se modela como `semi_quantitative` (decision de diseno 2026-10-03,
# sujeta a validacion del laboratorio): conjunto ordenado de diluciones
# (`option_set_id`) y valor esperado = una opcion del conjunto.
_ALLOWED_RANGE_FIELDS: dict[str, frozenset[str]] = {
    "numeric": _NUMERIC_RANGE_FIELDS,
    "calculated": _NUMERIC_RANGE_FIELDS,
    "qualitative": frozenset({"expected_option_id"}),
    "semi_quantitative": frozenset({"expected_option_id"}),
    "boolean": frozenset({"expected_boolean"}),
    "text": frozenset(),
    "titer": frozenset({"expected_option_id"}),
}

# `result_type` cuyo valor se elige de un conjunto de opciones.
_OPTION_SET_RESULT_TYPES = ("qualitative", "semi_quantitative", "titer")


def _not_allowed_range_fields(result_type: str, values: Mapping[str, Any]) -> list[str]:
    allowed = _ALLOWED_RANGE_FIELDS[result_type]
    return sorted(
        field
        for field in _TYPED_RANGE_FIELDS - allowed
        if values.get(field) is not None
    )


def _missing_fields_for_result_type(
    template_analyte: ResultTemplateAnalyte, active_range_count: int
) -> list[str]:
    """Campos obligatorios para publicar, segun `result_type`:
    - `qualitative`/`semi_quantitative`/`titer`: `option_set_id`.
    - `numeric`: `unit_id` + `decimals`; si es reportable, >= 1 rango activo
      (`reference_ranges`).
    - `calculated`: `formula` + `unit_id` + `decimals`.
    """
    result_type = template_analyte.result_type
    missing: list[str] = []
    if (
        result_type in _OPTION_SET_RESULT_TYPES
        and template_analyte.option_set_id is None
    ):
        missing.append("option_set_id")
    if result_type == "calculated" and template_analyte.formula is None:
        missing.append("formula")
    if result_type in ("numeric", "calculated"):
        if template_analyte.unit_id is None:
            missing.append("unit_id")
        if template_analyte.decimals is None:
            missing.append("decimals")
    if (
        result_type == "numeric"
        and template_analyte.is_reportable
        and active_range_count == 0
    ):
        missing.append("reference_ranges")
    return missing


def _is_inactive(entity: Any) -> bool:
    return entity is not None and not entity.is_active


async def _validate_publish(
    session: AsyncSession, version: ResultTemplateVersion
) -> None:
    """Solo el contenido activo cuenta. 422 si algun analito activo esta
    incompleto para su `result_type` (`details.missing`), si la version
    referencia algo desactivado (`details.inactive`) o si alguna formula es
    invalida (`details.invalid_formula`)."""
    version_id = version.id

    analytes = await repository.list_analytes_by_version(session, version_id)
    ranges = await repository.list_reference_ranges_by_template_analytes(
        session, [template_analyte.id for template_analyte in analytes]
    )
    catalogs: dict[str, Mapping[UUID, Any]] = {
        "analyte_id": await get_by_ids(
            session, Analyte, [a.analyte_id for a in analytes]
        ),
        "unit_id": await get_by_ids(session, Unit, [a.unit_id for a in analytes]),
        "option_set_id": await get_by_ids(
            session, ResultOptionSet, [a.option_set_id for a in analytes]
        ),
    }
    sections = {
        section.id: section
        for section in await repository.list_sections_by_version(
            session, version_id, include_inactive=True
        )
    }
    options = await get_by_ids(
        session,
        ResultOption,
        [r.expected_option_id for rows in ranges.values() for r in rows],
    )

    formula_nodes = await _version_formula_nodes(session, version_id)
    all_formula_nodes = list(formula_nodes.values())

    missing_report: list[dict] = []
    inactive_report: list[dict] = []
    formula_report: list[dict] = []
    for template_analyte in analytes:
        if template_analyte.formula is not None:
            formula_report.extend(
                {"template_analyte_id": str(template_analyte.id), **p.as_dict()}
                for p in formula_problems(
                    formula_nodes[template_analyte.id], all_formula_nodes
                )
            )

        active_ranges = ranges[template_analyte.id]
        missing = _missing_fields_for_result_type(template_analyte, len(active_ranges))
        incompatible = [
            str(r.id)
            for r in active_ranges
            if _not_allowed_range_fields(template_analyte.result_type, r.__dict__)
        ]
        if missing or incompatible:
            entry: dict[str, Any] = {
                "template_analyte_id": str(template_analyte.id),
                "result_type": template_analyte.result_type,
                "missing_fields": missing,
            }
            if incompatible:
                entry["incompatible_reference_range_ids"] = incompatible
            missing_report.append(entry)

        refs = [
            (field, getattr(template_analyte, field), catalog)
            for field, catalog in catalogs.items()
        ]
        refs.append(("section_id", template_analyte.section_id, sections))
        refs.extend(
            ("expected_option_id", r.expected_option_id, options) for r in active_ranges
        )
        inactive_report.extend(
            {
                "template_analyte_id": str(template_analyte.id),
                "field": field,
                "id": str(ref_id),
            }
            for field, ref_id, catalog in refs
            if ref_id is not None and _is_inactive(catalog.get(ref_id))
        )

    if missing_report or inactive_report or formula_report:
        raise ResultTemplateVersionIncompleteError(
            missing_report, inactive_report, formula_report
        )


versioning = VersioningService(
    ResultTemplateVersion,
    "result_template_id",
    parent_model=ResultTemplate,
    parent_noun="plantilla",
    feminine=True,
    read_schema=ResultTemplateVersionRead,
    owner_read_schema=ResultTemplateVersionWithOwnerRead,
    required_fields=("report_settings",),
    validate_publish=_validate_publish,
    clone_content=_clone_content,
)

# Ciclo de versiones (rutas `/result-templates/{id}/versions...`): lo resuelve
# el servicio generico; este modulo solo declara lo especifico (completitud al
# publicar y clonado profundo del contenido).
list_versions = versioning.list_versions
get_version_with_owner = versioning.read_with_owner
create_version = versioning.create_version
update_version = versioning.update_version
publish_version = versioning.publish_version
retire_version = versioning.retire_version


# --------------------------------------------------------------------------
# Sections (editable solo en draft)
# --------------------------------------------------------------------------


async def get_section_or_404(
    session: AsyncSession, version_id: UUID, section_id: UUID
) -> ResultTemplateSection:
    section = await session.get(ResultTemplateSection, section_id)
    if section is None or section.version_id != version_id:
        raise not_found("una seccion", section_id)
    return section


async def list_sections(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[ResultTemplateSectionRead]:
    await versioning.get_or_404(session, template_id, version_id)
    sections = await repository.list_sections_by_version(
        session, version_id, include_inactive=include_inactive
    )
    return [ResultTemplateSectionRead.model_validate(s) for s in sections]


async def create_section(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    data: ResultTemplateSectionCreate,
) -> ResultTemplateSectionRead:
    await versioning.get_draft(session, template_id, version_id)
    section = await create_entity(
        session, ResultTemplateSection, data, version_id=version_id
    )
    return ResultTemplateSectionRead.model_validate(section)


async def update_section(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    section_id: UUID,
    data: ResultTemplateSectionUpdate,
) -> ResultTemplateSectionRead:
    """Tambien desactiva/reactiva (`is_active`): las secciones no se borran.
    Un analito activo que quede en una seccion inactiva bloquea la
    publicacion (`details.inactive`)."""
    await versioning.get_draft(session, template_id, version_id)
    section = await get_section_or_404(session, version_id, section_id)
    section = await update_entity(session, section, data)
    return ResultTemplateSectionRead.model_validate(section)


# --------------------------------------------------------------------------
# Template analytes (editable solo en draft)
# --------------------------------------------------------------------------


async def get_template_analyte_or_404(
    session: AsyncSession, version_id: UUID, template_analyte_id: UUID
) -> ResultTemplateAnalyte:
    template_analyte = await session.get(ResultTemplateAnalyte, template_analyte_id)
    if template_analyte is None or template_analyte.version_id != version_id:
        raise not_found("un analito de plantilla", template_analyte_id)
    return template_analyte


async def _template_analyte_reads(
    session: AsyncSession, template_analytes: list[ResultTemplateAnalyte]
) -> list[ResultTemplateAnalyteRead]:
    units = await get_by_ids(
        session,
        Unit,
        [template_analyte.unit_id for template_analyte in template_analytes],
    )
    return [
        ResultTemplateAnalyteRead.model_validate(template_analyte).model_copy(
            update=_unit_fields(
                units.get(template_analyte.unit_id),  # type: ignore[arg-type]
                "unit",
                "unit_detail",
            )
        )
        for template_analyte in template_analytes
    ]


async def _validate_template_analyte_references(
    session: AsyncSession,
    version_id: UUID,
    changes: Mapping[str, Any],
    current: ResultTemplateAnalyte | None,
) -> None:
    """Toda referencia NUEVA del body debe existir y estar activa; la
    seccion, ademas, debe ser de la misma version."""
    if _is_new_reference(changes, "analyte_id", current):
        analyte_id = changes["analyte_id"]
        ensure_active_reference(
            await session.get(Analyte, analyte_id),
            subject="el analito",
            field="analyte_id",
            value=analyte_id,
        )
    if _is_new_reference(changes, "option_set_id", current):
        option_set_id = changes["option_set_id"]
        ensure_active_reference(
            await session.get(ResultOptionSet, option_set_id),
            subject="el conjunto de opciones",
            field="option_set_id",
            value=option_set_id,
        )
    if _is_new_reference(changes, "unit_id", current):
        await _validate_new_unit(session, changes["unit_id"], "unit_id")
    if _is_new_reference(changes, "section_id", current):
        section_id = changes["section_id"]
        section = await session.get(ResultTemplateSection, section_id)
        if section is None or section.version_id != version_id:
            raise InvalidReferenceError(
                "la sección", "section_id", section_id, "no existe en esta versión"
            )
        ensure_active(section, subject="la sección", field="section_id", feminine=True)


async def _ensure_analyte_not_duplicated(
    session: AsyncSession,
    version_id: UUID,
    analyte_id: UUID,
    current_id: UUID | None = None,
) -> None:
    """Un analito esta activo a lo sumo una vez por version (indice unico
    parcial en BD): 409 limpio en vez de `IntegrityError`."""
    existing = await repository.get_active_template_analyte_for_analyte(
        session, version_id, analyte_id
    )
    if existing is not None and existing.id != current_id:
        raise ResultTemplateAnalyteDuplicateError(str(analyte_id))


async def _version_formula_nodes(
    session: AsyncSession, version_id: UUID
) -> dict[UUID, FormulaNode]:
    """Todos los analitos de la version (activos e inactivos) como nodos de
    formula, por id de fila. Activo = fila activa y analito de catalogo activo."""
    rows = await repository.list_analytes_by_version(
        session, version_id, include_inactive=True
    )
    catalog = await get_by_ids(session, Analyte, [row.analyte_id for row in rows])
    return {
        row.id: FormulaNode(
            code=catalog[row.analyte_id].code,
            formula=row.formula,
            is_active=row.is_active and catalog[row.analyte_id].is_active,
        )
        for row in rows
    }


async def _validate_formula(
    session: AsyncSession,
    version_id: UUID,
    analyte_id: UUID,
    formula: str,
    current_id: UUID | None = None,
) -> None:
    """422 si la formula (de este analito, ya con su valor nuevo) no es
    valida dentro de la version: ver `formula.formula_problems`."""
    analyte = await get_or_404(session, Analyte, analyte_id, "un analito")
    node = FormulaNode(code=analyte.code, formula=formula, is_active=True)
    others = [
        other
        for row_id, other in (await _version_formula_nodes(session, version_id)).items()
        if row_id != current_id
    ]
    problems = formula_problems(node, [*others, node])
    if problems:
        raise ResultTemplateAnalyteFormulaError([p.as_dict() for p in problems])


async def list_template_analytes(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[ResultTemplateAnalyteRead]:
    await versioning.get_or_404(session, template_id, version_id)
    analytes = await repository.list_analytes_by_version(
        session, version_id, include_inactive=include_inactive
    )
    return await _template_analyte_reads(session, analytes)


async def create_template_analyte(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    data: ResultTemplateAnalyteCreate,
) -> ResultTemplateAnalyteRead:
    """No valida los campos requeridos por `result_type` aqui: una plantilla
    en `draft` puede construirse incrementalmente (p. ej. agregar el
    analito antes de decidir su `option_set_id`). La completitud solo se
    exige al publicar (ver `publish_version`). Las referencias si se
    validan (existen, activas, seccion de la misma version)."""
    await versioning.get_draft(session, template_id, version_id)
    await _validate_template_analyte_references(
        session, version_id, data.model_dump(), None
    )
    await _ensure_analyte_not_duplicated(session, version_id, data.analyte_id)
    if data.formula is not None:
        await _validate_formula(session, version_id, data.analyte_id, data.formula)

    template_analyte = await create_entity(
        session, ResultTemplateAnalyte, data, version_id=version_id
    )
    return (await _template_analyte_reads(session, [template_analyte]))[0]


async def update_template_analyte(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    data: ResultTemplateAnalyteUpdate,
) -> ResultTemplateAnalyteRead:
    """Tambien desactiva/reactiva (`is_active`): no se borran."""
    await versioning.get_draft(session, template_id, version_id)
    template_analyte = await get_template_analyte_or_404(
        session, version_id, template_analyte_id
    )
    changes = data.model_dump(exclude_unset=True)
    await _validate_template_analyte_references(
        session, version_id, changes, template_analyte
    )

    will_be_active = changes.get("is_active", template_analyte.is_active)
    target_analyte_id = changes.get("analyte_id") or template_analyte.analyte_id
    if will_be_active is not False:
        await _ensure_analyte_not_duplicated(
            session, version_id, target_analyte_id, template_analyte.id
        )
        formula = changes.get("formula", template_analyte.formula)
        if formula is not None and ("formula" in changes or "analyte_id" in changes):
            await _validate_formula(
                session, version_id, target_analyte_id, formula, template_analyte.id
            )

    template_analyte = await update_entity(session, template_analyte, data)
    return (await _template_analyte_reads(session, [template_analyte]))[0]


# --------------------------------------------------------------------------
# Reference ranges (editable solo en draft)
# --------------------------------------------------------------------------

# Edades normalizadas a dias para comparar rangos con distinta `age_unit`.
# Sin `age_unit` (y con edades) se interpreta como anos.
_AGE_UNIT_DAYS = {"dias": 1.0, "meses": 30.4375, "anos": 365.25}


def _age_interval(values: Mapping[str, Any]) -> tuple[float, float]:
    """`[age_min, age_max)` en dias; un extremo NULL es abierto (+-inf)."""
    factor = _AGE_UNIT_DAYS[values.get("age_unit") or "anos"]
    age_min, age_max = values.get("age_min"), values.get("age_max")
    low = -math.inf if age_min is None else float(age_min) * factor
    high = math.inf if age_max is None else float(age_max) * factor
    return low, high


def _normalized_condition(condition: str | None) -> str:
    return " ".join((condition or "").split()).casefold()


def _ranges_overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    """Misma combinacion (sexo compatible -- `any` solapa con todos --,
    condicion normalizada igual) y edades `[min, max)` que se cruzan."""
    if a["sex"] != b["sex"] and "any" not in (a["sex"], b["sex"]):
        return False
    if _normalized_condition(a.get("condition")) != _normalized_condition(
        b.get("condition")
    ):
        return False
    a_low, a_high = _age_interval(a)
    b_low, b_high = _age_interval(b)
    return a_low < b_high and b_low < a_high


async def get_reference_range_or_404(
    session: AsyncSession, template_analyte_id: UUID, reference_range_id: UUID
) -> ReferenceRange:
    reference_range = await session.get(ReferenceRange, reference_range_id)
    if (
        reference_range is None
        or reference_range.template_analyte_id != template_analyte_id
    ):
        raise not_found("un rango de referencia", reference_range_id)
    return reference_range


async def _validate_reference_range(
    session: AsyncSession,
    template_analyte: ResultTemplateAnalyte,
    values: Mapping[str, Any],
    current: ReferenceRange | None,
) -> None:
    """`values`: el rango completo resultante (en un PATCH, lo guardado
    combinado con el body)."""
    bound_errors = reference_range_bound_errors(values)
    if bound_errors:
        raise ReferenceRangeBoundsError(bound_errors)

    not_allowed = _not_allowed_range_fields(template_analyte.result_type, values)
    if not_allowed:
        raise ReferenceRangeFieldsNotAllowedError(
            template_analyte.result_type, not_allowed
        )

    if _is_new_reference(values, "expected_option_id", current):
        option_id = values["expected_option_id"]
        option = ensure_active_reference(
            await session.get(ResultOption, option_id),
            subject="la opción",
            field="expected_option_id",
            value=option_id,
            feminine=True,
        )
        if option.option_set_id != template_analyte.option_set_id:
            raise InvalidReferenceError(
                "la opción",
                "expected_option_id",
                option_id,
                "no pertenece al conjunto de opciones del analito",
            )

    if values.get("is_active", True):
        siblings = await repository.list_reference_ranges_by_template_analyte(
            session, template_analyte.id
        )
        for sibling in siblings:
            if current is not None and sibling.id == current.id:
                continue
            if _ranges_overlap(values, _range_values(sibling)):
                raise ReferenceRangeOverlapError(str(sibling.id))


def _range_values(reference_range: ReferenceRange) -> dict[str, Any]:
    return {
        field: getattr(reference_range, field) for field in (*_RANGE_COPY, "is_active")
    }


async def list_reference_ranges(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    *,
    include_inactive: bool = False,
) -> list[ReferenceRangeRead]:
    await versioning.get_or_404(session, template_id, version_id)
    await get_template_analyte_or_404(session, version_id, template_analyte_id)
    ranges = await repository.list_reference_ranges_by_template_analyte(
        session, template_analyte_id, include_inactive=include_inactive
    )
    return [ReferenceRangeRead.model_validate(r) for r in ranges]


async def create_reference_range(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    data: ReferenceRangeCreate,
) -> ReferenceRangeRead:
    await versioning.get_draft(session, template_id, version_id)
    template_analyte = await get_template_analyte_or_404(
        session, version_id, template_analyte_id
    )
    await _validate_reference_range(session, template_analyte, data.model_dump(), None)

    reference_range = await create_entity(
        session, ReferenceRange, data, template_analyte_id=template_analyte_id
    )
    return ReferenceRangeRead.model_validate(reference_range)


async def update_reference_range(
    session: AsyncSession,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    reference_range_id: UUID,
    data: ReferenceRangeUpdate,
) -> ReferenceRangeRead:
    """Tambien desactiva/reactiva (`is_active`): no se borran."""
    await versioning.get_draft(session, template_id, version_id)
    template_analyte = await get_template_analyte_or_404(
        session, version_id, template_analyte_id
    )
    reference_range = await get_reference_range_or_404(
        session, template_analyte_id, reference_range_id
    )
    changes = data.model_dump(exclude_unset=True, exclude={"activity_reason"})
    merged = {**_range_values(reference_range), **changes}
    await _validate_reference_range(session, template_analyte, merged, reference_range)

    reference_range = await update_entity(session, reference_range, data)
    return ReferenceRangeRead.model_validate(reference_range)
