"""add_auto_approval_to_approval_steps

Revision ID: fff1f376579c
Revises: 076426a7df4b
Create Date: 2025-07-29 11:36:56.291544

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fff1f376579c'
down_revision = '076426a7df4b'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi il campo auto_approval alla tabella approval_steps
    op.add_column('approval_steps', sa.Column('auto_approval', sa.Boolean(), nullable=False, server_default='false'))


def downgrade():
    # Rimuovi il campo auto_approval dalla tabella approval_steps
    op.drop_column('approval_steps', 'auto_approval')
