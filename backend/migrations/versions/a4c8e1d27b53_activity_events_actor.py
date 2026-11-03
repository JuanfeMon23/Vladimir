"""activity_events: quien hace cada (des)activacion

`activity_events` gana `actor_user_id` (uuid del usuario en Leo, sin FK) y
`actor_username` (copia del nombre al momento del cambio); ambas nullable
(filas historicas y semillas no tienen actor). `fn_log_activity` se redefine
para llenarlas desde `vladimir.activity_actor_id` y
`vladimir.activity_actor_username` (`current_setting(..., true)`; vacio o
ausente -> NULL). No toca los triggers de las tablas.

El downgrade restaura la funcion anterior y elimina las columnas (se pierde
el actor registrado).

Revision ID: a4c8e1d27b53
Revises: f7d3a9c25e18
Create Date: 2026-11-03 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a4c8e1d27b53"
down_revision: Union[str, Sequence[str], None] = "f7d3a9c25e18"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FN_LOG_ACTIVITY_WITH_ACTOR = """
CREATE OR REPLACE FUNCTION fn_log_activity() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.is_active IS NOT DISTINCT FROM OLD.is_active THEN
        RETURN NULL;
    END IF;
    INSERT INTO activity_events
        (entity_type, entity_id, action, reason, actor_user_id, actor_username)
    VALUES (
        TG_TABLE_NAME,
        NEW.id,
        CASE WHEN NEW.is_active THEN 'activated' ELSE 'deactivated' END,
        NULLIF(current_setting('vladimir.activity_reason', true), ''),
        NULLIF(current_setting('vladimir.activity_actor_id', true), '')::uuid,
        NULLIF(current_setting('vladimir.activity_actor_username', true), '')
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

# Definicion de la revision 6be0a4509512 (sin actor).
FN_LOG_ACTIVITY_WITHOUT_ACTOR = """
CREATE OR REPLACE FUNCTION fn_log_activity() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.is_active IS NOT DISTINCT FROM OLD.is_active THEN
        RETURN NULL;
    END IF;
    INSERT INTO activity_events (entity_type, entity_id, action, reason)
    VALUES (
        TG_TABLE_NAME,
        NEW.id,
        CASE WHEN NEW.is_active THEN 'activated' ELSE 'deactivated' END,
        NULLIF(current_setting('vladimir.activity_reason', true), '')
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("activity_events", sa.Column("actor_user_id", sa.UUID(), nullable=True))
    op.add_column("activity_events", sa.Column("actor_username", sa.Text(), nullable=True))
    op.execute(FN_LOG_ACTIVITY_WITH_ACTOR)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(FN_LOG_ACTIVITY_WITHOUT_ACTOR)
    op.drop_column("activity_events", "actor_username")
    op.drop_column("activity_events", "actor_user_id")
