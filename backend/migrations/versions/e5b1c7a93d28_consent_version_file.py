"""consent document versions: pdf file (base64) + single active data-treatment doc

Revision ID: e5b1c7a93d28
Revises: d4a9e2b86c15
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5b1c7a93d28'
down_revision: Union[str, Sequence[str], None] = 'd4a9e2b86c15'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

T = 'consent_document_versions'


def upgrade() -> None:
    op.add_column(T, sa.Column('file_base64', sa.Text(), nullable=True))
    op.add_column(T, sa.Column('file_content_type', sa.String(length=64), nullable=True))
    op.add_column(T, sa.Column('file_sha256', postgresql.CHAR(length=64), nullable=True))
    op.add_column(T, sa.Column('file_size_bytes', sa.Integer(), nullable=True))
    op.create_check_constraint(
        'file_content_type', T, "file_content_type IN ('application/pdf')"
    )
    op.create_check_constraint('file_sha256', T, "file_sha256 ~ '^[0-9a-f]{64}$'")
    op.create_check_constraint('file_size_bytes', T, 'file_size_bytes > 0')
    op.create_check_constraint(
        'file_all_or_none',
        T,
        '(file_base64 IS NULL AND file_content_type IS NULL '
        'AND file_sha256 IS NULL AND file_size_bytes IS NULL) OR '
        '(file_base64 IS NOT NULL AND file_content_type IS NOT NULL '
        'AND file_sha256 IS NOT NULL AND file_size_bytes IS NOT NULL)',
    )
    op.create_index(
        'uq_consent_documents_one_active_data_treatment',
        'consent_documents',
        ['document_type'],
        unique=True,
        postgresql_where=sa.text("document_type = 'tratamiento_datos' AND is_active"),
    )


def downgrade() -> None:
    op.drop_index(
        'uq_consent_documents_one_active_data_treatment',
        table_name='consent_documents',
        postgresql_where=sa.text("document_type = 'tratamiento_datos' AND is_active"),
    )
    for name in ('file_all_or_none', 'file_size_bytes', 'file_sha256', 'file_content_type'):
        op.drop_constraint(name, T, type_='check')
    for col in ('file_size_bytes', 'file_sha256', 'file_content_type', 'file_base64'):
        op.drop_column(T, col)
