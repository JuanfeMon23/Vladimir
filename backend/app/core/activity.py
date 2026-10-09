"""`GET /api/v1/activity`: historial de activaciones/desactivaciones de
cualquier fila con `is_active` (tabla `activity_events`, escrita solo por el
trigger de BD; la API solo la lee).

Transversal (no pertenece a ningun modulo de negocio), por eso vive en el
nucleo: schema, consulta y router en un solo archivo pequeno.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.db.activity import ACTIVITY_ACTION_VALUES, ActivityEvent
from app.core.dependencies import PaginationParams, pagination_params
from app.core.repository import paginate
from app.core.schemas import Page

# Tablas con `is_active` (= trigger de actividad). Escrita a mano para que
# el OpenAPI la publique como enum sin que el nucleo importe los modulos;
# `core/tests/test_activity.py` verifica que coincide con `Base.metadata`.
ACTIVATABLE_TABLES = (
    "analytes",
    "consent_documents",
    "lab_areas",
    "lab_test_consent_documents",
    "lab_test_preconditions",
    "lab_test_sample_types",
    "lab_tests",
    "preconditions",
    "print_labels",
    "reference_ranges",
    "result_option_sets",
    "result_options",
    "result_template_analytes",
    "result_template_sections",
    "result_templates",
    "sample_types",
    "samples",
    "staff",
    "units",
)

ActivityEntityType = Literal[ACTIVATABLE_TABLES]
ActivityAction = Literal[ACTIVITY_ACTION_VALUES]


class ActivityEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: ActivityEntityType
    entity_id: UUID
    action: ActivityAction
    reason: str | None
    occurred_at: datetime


async def list_activity(
    session: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    pagination: PaginationParams,
) -> Page[ActivityEventRead]:
    stmt = select(ActivityEvent).where(
        ActivityEvent.entity_type == entity_type,
        ActivityEvent.entity_id == entity_id,
    )
    items, total = await paginate(
        session,
        stmt,
        pagination,
        ActivityEvent.occurred_at.desc(),
        ActivityEvent.id.desc(),
    )
    return Page[ActivityEventRead](
        items=[ActivityEventRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


activity_router = APIRouter(tags=["activity"])


@activity_router.get(
    "",
    response_model=Page[ActivityEventRead],
    responses={422: {"description": "`entity_type` no es una tabla con is_active"}},
)
async def get_activity(
    session: Annotated[AsyncSession, Depends(get_session)],
    pagination: Annotated[PaginationParams, Depends(pagination_params)],
    entity_type: Annotated[ActivityEntityType, Query()],
    entity_id: Annotated[UUID, Query()],
) -> Page[ActivityEventRead]:
    """Historial de (des)activaciones de una fila, mas reciente primero.
    `entity_type` es el nombre de la tabla (p. ej. `analytes`)."""
    return await list_activity(session, entity_type, entity_id, pagination)


__all__ = [
    "ACTIVATABLE_TABLES",
    "ActivityEntityType",
    "ActivityEventRead",
    "activity_router",
]
