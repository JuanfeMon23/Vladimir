"""Esquemas Pydantic de entrada/salida del modulo `staff`."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ActivityReasonInput


class StaffBase(BaseModel):
    document_type: str = Field(max_length=32)
    document_number: str = Field(max_length=32)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    job_title: str | None = Field(default=None, max_length=100)
    professional_license: str | None = Field(default=None, max_length=64)


class StaffCreate(StaffBase):
    is_active: bool = True


class StaffUpdate(ActivityReasonInput):
    """Todos los campos opcionales: PATCH parcial."""

    document_type: str | None = Field(default=None, max_length=32)
    document_number: str | None = Field(default=None, max_length=32)
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    job_title: str | None = Field(default=None, max_length=100)
    professional_license: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class StaffRead(StaffBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
