"""Rutas HTTP del modulo `result_templates`. Delgadas: solo traducen HTTP
<-> controller.

Cinco routers: `units_router` (`/units`), `analytes_router` (`/analytes`), `result_option_sets_router`
(`/result-option-sets`, con el sub-recurso `options`), `result_options_router`
(`/result-options/{id}`, PATCH directo, mismo patron que
`samples.sample_types_router`) y `result_templates_router`
(`/result-templates`, con versiones y, dentro de cada version, secciones,
analitos y rangos de referencia).

Nada se elimina: no hay `DELETE`; secciones, analitos de plantilla y rangos
se desactivan con `is_active` en su PATCH (solo en borrador).
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from leo_sdk import LeoUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import (
    ActiveOnlyFilter,
    PaginationParams,
    SearchFilter,
    active_only_filter,
    include_inactive_param,
    pagination_params,
    search_filter,
    version_status_param,
)
from app.core.leo import audit_patch, auth, authorize_patch, record_audit, snapshot
from app.core.schemas import Page, error_responses
from app.core.versioning import RETIRE_VERSION_RESPONSES, VersionStatus
from app.modules.result_templates import controller
from app.modules.result_templates.permissions import (
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    CREATE_VERSION,
    EDIT,
    EDIT_CHECK,
    EDIT_CONTENT,
    EDIT_VERSION,
    MANAGE_ANALYTES,
    MANAGE_OPTION_SETS,
    MANAGE_UNITS,
    PUBLISH_VERSION,
    RETIRE_VERSION,
    CanCreate,
    CanCreateVersion,
    CanEditContent,
    CanEditVersion,
    CanManageAnalytes,
    CanManageOptionSets,
    CanManageUnits,
    CanPublishVersion,
    CanRetireVersion,
    CanView,
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
    ResultTemplateVersionCreate,
    ResultTemplateVersionRead,
    ResultTemplateVersionUpdate,
    ResultTemplateVersionWithOwnerRead,
    UnitCreate,
    UnitRead,
    UnitUpdate,
)

units_router = APIRouter(tags=["result_templates"])
analytes_router = APIRouter(tags=["result_templates"])
result_option_sets_router = APIRouter(tags=["result_templates"])
result_options_router = APIRouter(tags=["result_templates"])
result_templates_router = APIRouter(tags=["result_templates"])
result_template_versions_router = APIRouter(tags=["result_templates"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]
PaginationDep = Annotated[PaginationParams, Depends(pagination_params)]
ActiveFilterDep = Annotated[ActiveOnlyFilter, Depends(active_only_filter)]
SearchDep = Annotated[SearchFilter, Depends(search_filter)]
IncludeInactiveDep = Annotated[bool, Depends(include_inactive_param)]

# --------------------------------------------------------------------------
# Units (catalogo UCUM; sin DELETE: se desactiva)
# --------------------------------------------------------------------------


@units_router.get("", response_model=Page[UnitRead])
async def list_units(
    _user: CanView,
    session: SessionDep,
    pagination: PaginationDep,
    active_filter: ActiveFilterDep,
    search: SearchDep,
) -> Page[UnitRead]:
    """Ordenadas por `code` (UCUM)."""
    return await controller.list_units(session, pagination, active_filter, search)


@units_router.post(
    "",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_unit(
    user: CanManageUnits, data: UnitCreate, session: SessionDep
) -> UnitRead:
    created = await controller.create_unit(session, data)
    await record_audit(
        MANAGE_UNITS,
        user,
        entity_type="unit",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@units_router.get("/{unit_id}", response_model=UnitRead, responses=error_responses(404))
async def get_unit(_user: CanView, unit_id: UUID, session: SessionDep) -> UnitRead:
    return await controller.get_unit(session, unit_id)


@units_router.patch(
    "/{unit_id}", response_model=UnitRead, responses=error_responses(404, 409, 422)
)
async def update_unit(
    user: CanManageUnits, unit_id: UUID, data: UnitUpdate, session: SessionDep
) -> UnitRead:
    """`is_active` + `activity_reason` (des)activa con motivo."""
    before = snapshot(await controller.get_unit(session, unit_id))
    updated = await controller.update_unit(session, unit_id, data)
    await record_audit(
        MANAGE_UNITS,
        user,
        entity_type="unit",
        entity_id=unit_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


# --------------------------------------------------------------------------
# Analytes
# --------------------------------------------------------------------------


@analytes_router.get("", response_model=Page[AnalyteRead])
async def list_analytes(
    _user: CanView,
    session: SessionDep,
    pagination: PaginationDep,
    active_filter: ActiveFilterDep,
    search: SearchDep,
) -> Page[AnalyteRead]:
    return await controller.list_analytes(session, pagination, active_filter, search)


@analytes_router.post(
    "",
    response_model=AnalyteRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_analyte(
    user: CanManageAnalytes, data: AnalyteCreate, session: SessionDep
) -> AnalyteRead:
    created = await controller.create_analyte(session, data)
    await record_audit(
        MANAGE_ANALYTES,
        user,
        entity_type="analyte",
        entity_id=created.id,
        after=snapshot(created, "default_unit", "default_unit_detail"),
    )
    return created


@analytes_router.get(
    "/{analyte_id}", response_model=AnalyteRead, responses=error_responses(404)
)
async def get_analyte(
    _user: CanView, analyte_id: UUID, session: SessionDep
) -> AnalyteRead:
    return await controller.get_analyte(session, analyte_id)


@analytes_router.patch(
    "/{analyte_id}",
    response_model=AnalyteRead,
    responses=error_responses(404, 409, 422),
)
async def update_analyte(
    user: CanManageAnalytes, analyte_id: UUID, data: AnalyteUpdate, session: SessionDep
) -> AnalyteRead:
    before = snapshot(
        await controller.get_analyte(session, analyte_id),
        "default_unit",
        "default_unit_detail",
    )
    updated = await controller.update_analyte(session, analyte_id, data)
    await record_audit(
        MANAGE_ANALYTES,
        user,
        entity_type="analyte",
        entity_id=analyte_id,
        before=before,
        after=snapshot(updated, "default_unit", "default_unit_detail"),
        reason=data.activity_reason,
    )
    return updated


# --------------------------------------------------------------------------
# Result option sets + options
# --------------------------------------------------------------------------


@result_option_sets_router.get("", response_model=Page[ResultOptionSetRead])
async def list_result_option_sets(
    _user: CanView,
    session: SessionDep,
    pagination: PaginationDep,
    active_filter: ActiveFilterDep,
    search: SearchDep,
) -> Page[ResultOptionSetRead]:
    return await controller.list_option_sets(session, pagination, active_filter, search)


@result_option_sets_router.post(
    "",
    response_model=ResultOptionSetRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_result_option_set(
    user: CanManageOptionSets, data: ResultOptionSetCreate, session: SessionDep
) -> ResultOptionSetRead:
    created = await controller.create_option_set(session, data)
    await record_audit(
        MANAGE_OPTION_SETS,
        user,
        entity_type="result_option_set",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_option_sets_router.get(
    "/{option_set_id}",
    response_model=ResultOptionSetRead,
    responses=error_responses(404),
)
async def get_result_option_set(
    _user: CanView, option_set_id: UUID, session: SessionDep
) -> ResultOptionSetRead:
    return await controller.get_option_set(session, option_set_id)


@result_option_sets_router.patch(
    "/{option_set_id}",
    response_model=ResultOptionSetRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_option_set(
    user: CanManageOptionSets,
    option_set_id: UUID,
    data: ResultOptionSetUpdate,
    session: SessionDep,
) -> ResultOptionSetRead:
    before = snapshot(await controller.get_option_set(session, option_set_id))
    updated = await controller.update_option_set(session, option_set_id, data)
    await record_audit(
        MANAGE_OPTION_SETS,
        user,
        entity_type="result_option_set",
        entity_id=option_set_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@result_option_sets_router.get(
    "/{option_set_id}/options",
    response_model=Page[ResultOptionRead],
    responses=error_responses(404),
)
async def list_result_options(
    _user: CanView,
    option_set_id: UUID,
    session: SessionDep,
    pagination: PaginationDep,
    active_filter: ActiveFilterDep,
    search: SearchDep,
) -> Page[ResultOptionRead]:
    return await controller.list_options(
        session, option_set_id, pagination, active_filter, search
    )


@result_option_sets_router.post(
    "/{option_set_id}/options",
    response_model=ResultOptionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_result_option(
    user: CanManageOptionSets,
    option_set_id: UUID,
    data: ResultOptionCreate,
    session: SessionDep,
) -> ResultOptionRead:
    created = await controller.create_option(session, option_set_id, data)
    await record_audit(
        MANAGE_OPTION_SETS,
        user,
        entity_type="result_option",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_options_router.patch(
    "/{option_id}",
    response_model=ResultOptionRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_option(
    user: CanManageOptionSets,
    option_id: UUID,
    data: ResultOptionUpdate,
    session: SessionDep,
) -> ResultOptionRead:
    before = snapshot(await controller.get_option(session, option_id))
    updated = await controller.update_option(session, option_id, data)
    await record_audit(
        MANAGE_OPTION_SETS,
        user,
        entity_type="result_option",
        entity_id=option_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


# --------------------------------------------------------------------------
# Result templates + versions
# --------------------------------------------------------------------------


@result_templates_router.get("", response_model=Page[ResultTemplateRead])
async def list_result_templates(
    _user: CanView,
    session: SessionDep,
    pagination: PaginationDep,
    active_filter: ActiveFilterDep,
    search: SearchDep,
) -> Page[ResultTemplateRead]:
    return await controller.list_templates(session, pagination, active_filter, search)


@result_templates_router.post(
    "",
    response_model=ResultTemplateRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(409, 422),
)
async def create_result_template(
    user: CanCreate, data: ResultTemplateCreate, session: SessionDep
) -> ResultTemplateRead:
    created = await controller.create_template(session, data)
    await record_audit(
        CREATE,
        user,
        entity_type="result_template",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_templates_router.get(
    "/{template_id}", response_model=ResultTemplateRead, responses=error_responses(404)
)
async def get_result_template(
    _user: CanView, template_id: UUID, session: SessionDep
) -> ResultTemplateRead:
    return await controller.get_template(session, template_id)


@result_templates_router.patch(
    "/{template_id}",
    response_model=ResultTemplateRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_template(
    template_id: UUID,
    data: ResultTemplateUpdate,
    request: Request,
    user: Annotated[LeoUser, Depends(auth.current_user)],
    session: SessionDep,
) -> ResultTemplateRead:
    """Exige `edit` si cambia datos y `change-status` si trae `is_active`."""
    await authorize_patch(
        request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
    )
    before = snapshot(await controller.get_template(session, template_id))
    updated = await controller.update_template(session, template_id, data)
    await audit_patch(
        user,
        edit_tag=EDIT,
        status_tag=CHANGE_STATUS,
        entity_type="result_template",
        entity_id=template_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


@result_templates_router.get(
    "/{template_id}/versions",
    response_model=Page[ResultTemplateVersionRead],
    responses=error_responses(404),
)
async def list_result_template_versions(
    _user: CanView,
    template_id: UUID,
    session: SessionDep,
    pagination: PaginationDep,
    version_status: Annotated[VersionStatus | None, Depends(version_status_param)],
) -> Page[ResultTemplateVersionRead]:
    """`?status=` filtra por estado (p. ej. solo `published`)."""
    return await controller.list_versions(
        session, template_id, pagination, version_status
    )


@result_template_versions_router.get(
    "/{version_id}",
    response_model=ResultTemplateVersionWithOwnerRead,
    responses=error_responses(404),
)
async def get_result_template_version(
    _user: CanView, version_id: UUID, session: SessionDep
) -> ResultTemplateVersionWithOwnerRead:
    """Una version por su id, con su plantilla duena en `owner`."""
    return await controller.get_version_with_owner(session, version_id)


@result_templates_router.post(
    "/{template_id}/versions",
    response_model=ResultTemplateVersionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_result_template_version(
    user: CanCreateVersion,
    template_id: UUID,
    data: ResultTemplateVersionCreate,
    session: SessionDep,
) -> ResultTemplateVersionRead:
    """Nuevo draft: clona la ultima version (secciones, analitos y rangos
    incluidos), o crea la version 1 si la plantilla todavia no tiene
    ninguna."""
    created = await controller.create_version(session, template_id, data)
    await record_audit(
        CREATE_VERSION,
        user,
        entity_type="result_template_version",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_templates_router.patch(
    "/{template_id}/versions/{version_id}",
    response_model=ResultTemplateVersionRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_template_version(
    user: CanEditVersion,
    template_id: UUID,
    version_id: UUID,
    data: ResultTemplateVersionUpdate,
    session: SessionDep,
) -> ResultTemplateVersionRead:
    """Solo aplica si la version esta en `draft`."""
    before = snapshot(await controller.get_version(session, template_id, version_id))
    updated = await controller.update_version(session, template_id, version_id, data)
    await record_audit(
        EDIT_VERSION,
        user,
        entity_type="result_template_version",
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


@result_templates_router.post(
    "/{template_id}/versions/{version_id}/publish",
    response_model=ResultTemplateVersionRead,
    responses=error_responses(404, 422),
)
async def publish_result_template_version(
    user: CanPublishVersion, template_id: UUID, version_id: UUID, session: SessionDep
) -> ResultTemplateVersionRead:
    """Valida que la plantilla este completa; `422` con el detalle de lo que
    falta si no lo esta."""
    before = snapshot(await controller.get_version(session, template_id, version_id))
    updated = await controller.publish_version(session, template_id, version_id)
    await record_audit(
        PUBLISH_VERSION,
        user,
        entity_type="result_template_version",
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


@result_templates_router.post(
    "/{template_id}/versions/{version_id}/retire",
    response_model=ResultTemplateVersionRead,
    responses=RETIRE_VERSION_RESPONSES,
)
async def retire_result_template_version(
    user: CanRetireVersion, template_id: UUID, version_id: UUID, session: SessionDep
) -> ResultTemplateVersionRead:
    before = snapshot(await controller.get_version(session, template_id, version_id))
    updated = await controller.retire_version(session, template_id, version_id)
    await record_audit(
        RETIRE_VERSION,
        user,
        entity_type="result_template_version",
        entity_id=version_id,
        before=before,
        after=snapshot(updated),
    )
    return updated


# --------------------------------------------------------------------------
# Sections (editable solo en draft)
# --------------------------------------------------------------------------


@result_templates_router.get(
    "/{template_id}/versions/{version_id}/sections",
    response_model=list[ResultTemplateSectionRead],
    responses=error_responses(404),
)
async def list_result_template_sections(
    _user: CanView,
    template_id: UUID,
    version_id: UUID,
    session: SessionDep,
    include_inactive: IncludeInactiveDep,
) -> list[ResultTemplateSectionRead]:
    """Solo las activas, salvo `?include_inactive=true`."""
    return await controller.list_sections(
        session, template_id, version_id, include_inactive=include_inactive
    )


@result_templates_router.post(
    "/{template_id}/versions/{version_id}/sections",
    response_model=ResultTemplateSectionRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_result_template_section(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    data: ResultTemplateSectionCreate,
    session: SessionDep,
) -> ResultTemplateSectionRead:
    created = await controller.create_section(session, template_id, version_id, data)
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="result_template_section",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_templates_router.patch(
    "/{template_id}/versions/{version_id}/sections/{section_id}",
    response_model=ResultTemplateSectionRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_template_section(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    section_id: UUID,
    data: ResultTemplateSectionUpdate,
    session: SessionDep,
) -> ResultTemplateSectionRead:
    before = snapshot(await controller.get_section(session, version_id, section_id))
    updated = await controller.update_section(
        session, template_id, version_id, section_id, data
    )
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="result_template_section",
        entity_id=section_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated


# --------------------------------------------------------------------------
# Template analytes (editable solo en draft)
# --------------------------------------------------------------------------


@result_templates_router.get(
    "/{template_id}/versions/{version_id}/analytes",
    response_model=list[ResultTemplateAnalyteRead],
    responses=error_responses(404),
)
async def list_result_template_analytes(
    _user: CanView,
    template_id: UUID,
    version_id: UUID,
    session: SessionDep,
    include_inactive: IncludeInactiveDep,
) -> list[ResultTemplateAnalyteRead]:
    """Solo los activos, salvo `?include_inactive=true`."""
    return await controller.list_template_analytes(
        session, template_id, version_id, include_inactive=include_inactive
    )


@result_templates_router.post(
    "/{template_id}/versions/{version_id}/analytes",
    response_model=ResultTemplateAnalyteRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_result_template_analyte(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    data: ResultTemplateAnalyteCreate,
    session: SessionDep,
) -> ResultTemplateAnalyteRead:
    created = await controller.create_template_analyte(
        session, template_id, version_id, data
    )
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="result_template_analyte",
        entity_id=created.id,
        after=snapshot(created, "unit", "unit_detail"),
    )
    return created


@result_templates_router.patch(
    "/{template_id}/versions/{version_id}/analytes/{template_analyte_id}",
    response_model=ResultTemplateAnalyteRead,
    responses=error_responses(404, 409, 422),
)
async def update_result_template_analyte(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    data: ResultTemplateAnalyteUpdate,
    session: SessionDep,
) -> ResultTemplateAnalyteRead:
    before = snapshot(
        await controller.get_template_analyte(session, version_id, template_analyte_id),
        "unit",
        "unit_detail",
    )
    updated = await controller.update_template_analyte(
        session, template_id, version_id, template_analyte_id, data
    )
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="result_template_analyte",
        entity_id=template_analyte_id,
        before=before,
        after=snapshot(updated, "unit", "unit_detail"),
        reason=data.activity_reason,
    )
    return updated


# --------------------------------------------------------------------------
# Reference ranges (editable solo en draft)
# --------------------------------------------------------------------------


@result_templates_router.get(
    "/{template_id}/versions/{version_id}/analytes/{template_analyte_id}/reference-ranges",
    response_model=list[ReferenceRangeRead],
    responses=error_responses(404),
)
async def list_reference_ranges(
    _user: CanView,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    session: SessionDep,
    include_inactive: IncludeInactiveDep,
) -> list[ReferenceRangeRead]:
    """Solo los activos, salvo `?include_inactive=true`."""
    return await controller.list_reference_ranges(
        session,
        template_id,
        version_id,
        template_analyte_id,
        include_inactive=include_inactive,
    )


@result_templates_router.post(
    "/{template_id}/versions/{version_id}/analytes/{template_analyte_id}/reference-ranges",
    response_model=ReferenceRangeRead,
    status_code=status.HTTP_201_CREATED,
    responses=error_responses(404, 409, 422),
)
async def create_reference_range(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    data: ReferenceRangeCreate,
    session: SessionDep,
) -> ReferenceRangeRead:
    created = await controller.create_reference_range(
        session, template_id, version_id, template_analyte_id, data
    )
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="reference_range",
        entity_id=created.id,
        after=snapshot(created),
    )
    return created


@result_templates_router.patch(
    "/{template_id}/versions/{version_id}/analytes/{template_analyte_id}"
    "/reference-ranges/{reference_range_id}",
    response_model=ReferenceRangeRead,
    responses=error_responses(404, 409, 422),
)
async def update_reference_range(
    user: CanEditContent,
    template_id: UUID,
    version_id: UUID,
    template_analyte_id: UUID,
    reference_range_id: UUID,
    data: ReferenceRangeUpdate,
    session: SessionDep,
) -> ReferenceRangeRead:
    before = snapshot(
        await controller.get_reference_range(
            session, template_analyte_id, reference_range_id
        )
    )
    updated = await controller.update_reference_range(
        session, template_id, version_id, template_analyte_id, reference_range_id, data
    )
    await record_audit(
        EDIT_CONTENT,
        user,
        entity_type="reference_range",
        entity_id=reference_range_id,
        before=before,
        after=snapshot(updated),
        reason=data.activity_reason,
    )
    return updated
