"""add_missing_document_fields

Revision ID: 774b2013bad7
Revises: ab653bbb718e
Create Date: 2025-07-29 11:49:30.123456

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '774b2013bad7'
down_revision = 'ab653bbb718e'
branch_labels = None
depends_on = None


def upgrade():
    # Aggiungi tutti i campi mancanti alla tabella documents
    op.add_column('documents', sa.Column('is_signed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('documents', sa.Column('signed_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('signed_by', sa.String(150), nullable=True))
    op.add_column('documents', sa.Column('firma_commento', sa.Text(), nullable=True))
    op.add_column('documents', sa.Column('signed_by_ai', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('documents', sa.Column('stato_approvazione', sa.String(30), nullable=False, server_default='bozza'))
    op.add_column('documents', sa.Column('approvato_da', sa.String(150), nullable=True))
    op.add_column('documents', sa.Column('data_approvazione', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('commento_approvatore', sa.Text(), nullable=True))


def downgrade():
    # Rimuovi tutti i campi aggiunti
    op.drop_column('documents', 'commento_approvatore')
    op.drop_column('documents', 'data_approvazione')
    op.drop_column('documents', 'approvato_da')
    op.drop_column('documents', 'stato_approvazione')
    op.drop_column('documents', 'signed_by_ai')
    op.drop_column('documents', 'firma_commento')
    op.drop_column('documents', 'signed_by')
    op.drop_column('documents', 'signed_at')
    op.drop_column('documents', 'is_signed')
