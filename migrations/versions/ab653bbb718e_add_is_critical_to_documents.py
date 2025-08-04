"""add_is_critical_to_documents

Revision ID: ab653bbb718e
Revises: fff1f376579c
Create Date: 2025-07-29 11:47:15.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ab653bbb718e'
down_revision = 'fff1f376579c'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi il campo is_critical alla tabella documents
    op.add_column('documents', sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Rimuovi il campo is_critical dalla tabella documents
    op.drop_column('documents', 'is_critical')
