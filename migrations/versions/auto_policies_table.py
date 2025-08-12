"""Auto policies table

Revision ID: auto_policies_001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'auto_policies_001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Crea tabella auto_policies per regole AI automatiche."""
    
    # Crea tabella auto_policies
    op.create_table('auto_policies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('condition', sa.Text(), nullable=False),
        sa.Column('condition_type', sa.String(length=50), nullable=False, default='json'),
        sa.Column('action', sa.String(length=10), nullable=False),  # approve / deny
        sa.Column('priority', sa.Integer(), nullable=False, default=1),
        sa.Column('active', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Aggiungi indici per performance
    op.create_index('idx_auto_policies_active', 'auto_policies', ['active'])
    op.create_index('idx_auto_policies_priority', 'auto_policies', ['priority'])
    op.create_index('idx_auto_policies_created_by', 'auto_policies', ['created_by'])
    
    # Aggiungi foreign key per created_by
    op.create_foreign_key(
        'fk_auto_policies_created_by',
        'auto_policies', 'users',
        ['created_by'], ['id']
    )
    
    # Aggiungi foreign key per approved_by
    op.create_foreign_key(
        'fk_auto_policies_approved_by',
        'auto_policies', 'users',
        ['approved_by'], ['id']
    )

def downgrade():
    """Elimina tabella auto_policies."""
    
    # Rimuovi foreign keys
    op.drop_constraint('fk_auto_policies_approved_by', 'auto_policies', type_='foreignkey')
    op.drop_constraint('fk_auto_policies_created_by', 'auto_policies', type_='foreignkey')
    
    # Rimuovi indici
    op.drop_index('idx_auto_policies_created_by', table_name='auto_policies')
    op.drop_index('idx_auto_policies_priority', table_name='auto_policies')
    op.drop_index('idx_auto_policies_active', table_name='auto_policies')
    
    # Rimuovi tabella
    op.drop_table('auto_policies') 