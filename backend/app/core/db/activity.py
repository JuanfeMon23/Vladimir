"""`activity_events`: historial de (des)activaciones de toda fila con
`is_active`.

La escribe solo la BD (trigger `fn_log_activity`, ver `triggers.py`); la app
solo la lee. Es inmutable (UPDATE y DELETE bloqueados por trigger), por eso
no lleva `created_at`/`updated_at`: `occurred_at` es su unica marca de tiempo.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db.base import Base
from app.core.db.mixins import UUIDv7PK

ACTIVITY_ACTION_VALUES = ("activated", "deactivated")


class ActivityEvent(UUIDv7PK, Base):
    """Una activacion o desactivacion de una fila de cualquier tabla."""

    __tablename__ = "activity_events"
    __table_args__ = (
        CheckConstraint(f"action IN {ACTIVITY_ACTION_VALUES}", name="action"),
        Index(
            "ix_activity_events_entity_type_entity_id_occurred_at",
            "entity_type",
            "entity_id",
            "occurred_at",
        ),
    )

    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
