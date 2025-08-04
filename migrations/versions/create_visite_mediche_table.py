"""Create visite_mediche table

Revision ID: create_visite_mediche_table
Revises: a43c00560750
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'create_visite_mediche_table'
down_revision = 'a43c00560750'
branch_labels = None
depends_on = None


def upgrade():
    """Create visite_mediche table."""
    op.create_table('visite_mediche',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ruolo', sa.String(length=100), nullable=False),
        sa.Column('tipo_visita', sa.String(length=150), nullable=False),
        sa.Column('data_visita', sa.Date(), nullable=False),
        sa.Column('scadenza', sa.Date(), nullable=False),
        sa.Column('esito', sa.String(length=50), nullable=False),
        sa.Column('certificato_filename', sa.String(length=255), nullable=True),
        sa.Column('certificato_path', sa.String(length=255), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    """Drop visite_mediche table."""
    op.drop_table('visite_mediche') 