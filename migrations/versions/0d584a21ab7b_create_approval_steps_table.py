"""create_approval_steps_table

Revision ID: 0d584a21ab7b
Revises: 774b2013bad7
Create Date: 2025-07-29 11:52:30.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d584a21ab7b'
down_revision = '774b2013bad7'
branch_labels = None
depends_on = None


def upgrade():
    # Crea la tabella approval_steps
    op.create_table('approval_steps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('step_name', sa.String(length=100), nullable=False),
        sa.Column('approver_id', sa.Integer(), nullable=True),
        sa.Column('approver_role', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('auto_approval', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['approver_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Rimuovi la tabella approval_steps
    op.drop_table('approval_steps')
