"""Rutas HTTP de los catalogos de categoria: `/api/v1/catalogs/<slug>`.

Delgadas: traducen HTTP <-> controller. Las 3 rutas de cada catalogo (listar,
crear, editar/desactivar) salen del mismo patron, parametrizado por su
`CatalogSpec`; nada se borra.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from leo_sdk import LeoUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import include_inactive_param
from app.core.leo import audit_patch, auth, authorize_patch, record_audit, snapshot
from app.core.schemas import error_responses
from app.modules.catalogs import controller
from app.modules.catalogs.permissions import (
    CHANGE_STATUS,
    CHANGE_STATUS_CHECK,
    CREATE,
    EDIT,
    EDIT_CHECK,
    CanCreate,
    CanView,
)
from app.modules.catalogs.registry import CATALOGS, CatalogSpec

router = APIRouter(tags=["catalogs"])


def _add_catalog_routes(spec: CatalogSpec) -> None:
    read, create, update = spec.read, spec.create, spec.update
    path = f"/{spec.slug}"
    item_path = f"{path}/{{item_id}}"

    @router.get(
        path,
        name=f"list_{spec.entity}",
        response_model=list[read],
        summary=f"Listar {spec.entity}",
        description="Ordenado por `sort_order`. Por defecto solo activos; "
        "`include_inactive=true` incluye los desactivados.",
    )
    async def list_items(
        _user: CanView,
        session: Annotated[AsyncSession, Depends(get_session)],
        include_inactive: Annotated[bool, Depends(include_inactive_param)],
    ) -> list[read]:
        return await controller.list_items(
            session, spec, include_inactive=include_inactive
        )

    @router.post(
        path,
        name=f"create_{spec.entity}",
        response_model=read,
        status_code=status.HTTP_201_CREATED,
        summary=f"Crear en {spec.entity}",
        responses=error_responses(409, 422),
    )
    async def create_item(
        data: create,
        user: CanCreate,
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> read:
        created = await controller.create_item(session, spec, data)
        await record_audit(
            CREATE,
            user,
            entity_type=spec.entity,
            entity_id=created.id,
            after=snapshot(created),
        )
        return created

    @router.patch(
        item_path,
        name=f"update_{spec.entity}",
        response_model=read,
        summary=f"Editar o (des)activar en {spec.entity}",
        description="Exige `edit` si cambia datos y `change-status` si trae "
        "`is_active` (con `activity_reason` opcional). El `code` no se edita.",
        responses=error_responses(404, 409, 422),
    )
    async def update_item(
        item_id: UUID,
        data: update,
        request: Request,
        user: Annotated[LeoUser, Depends(auth.current_user)],
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> read:
        await authorize_patch(
            request, user, data, edit_check=EDIT_CHECK, status_check=CHANGE_STATUS_CHECK
        )
        before = snapshot(await controller.get_item(session, spec, item_id))
        updated = await controller.update_item(session, spec, item_id, data)
        await audit_patch(
            user,
            edit_tag=EDIT,
            status_tag=CHANGE_STATUS,
            entity_type=spec.entity,
            entity_id=item_id,
            before=before,
            after=snapshot(updated),
            reason=data.activity_reason,
        )
        return updated


for catalog_spec in CATALOGS:
    _add_catalog_routes(catalog_spec)
