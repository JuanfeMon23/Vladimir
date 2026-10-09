"""Esquemas Pydantic de entrada/salida del modulo `lab_areas`."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput, CodeStr


class LabAreaBase(BaseModel):
    code: CodeStr
    name: str = Field(max_length=100)
    description: str | None = None


class LabAreaCreate(LabAreaBase):
    is_active: bool = True


class LabAreaUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    code: CodeStr | None = None
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    is_active: bool | None = None


class ManagerAssignmentRead(BaseModel):
    """Una fila del historial de encargados, con el nombre del staff resuelto
    (evita que el frontend tenga que resolverlo con una 2a llamada)."""

    id: UUID
    area_id: UUID
    staff_id: UUID
    staff_name: str
    start_at: datetime
    end_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ManagerAssignmentCreate(BaseModel):
    """Body de `PUT /lab-areas/{id}/manager`: asigna o cambia el encargado."""

    staff_id: UUID
    start_at: datetime | None = None
    notes: str | None = None


class LabAreaRead(LabAreaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    current_manager: ManagerAssignmentRead | None = None
