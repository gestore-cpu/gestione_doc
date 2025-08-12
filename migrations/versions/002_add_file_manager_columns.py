"""Add file manager columns to documents table

Revision ID: 002_file_manager
Revises: 001_security
Create Date: 2025-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_file_manager'
down_revision = '001_security'
branch_labels = None
depends_on = None


def upgrade():
    # Add file manager columns to documents table
    op.add_column('documents', sa.Column('classification', sa.String(20), nullable=True, server_default='public'))
    op.add_column('documents', sa.Column('file_size', sa.BigInteger(), nullable=True))
    op.add_column('documents', sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('documents', sa.Column('owner_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraint for owner_id
    op.create_foreign_key('fk_documents_owner_id', 'documents', 'users', ['owner_id'], ['id'])
    
    # Create indexes for better performance
    op.create_index('ix_documents_classification', 'documents', ['classification'])
    op.create_index('ix_documents_file_size', 'documents', ['file_size'])
    op.create_index('ix_documents_updated_at', 'documents', ['updated_at'])
    op.create_index('ix_documents_owner_id', 'documents', ['owner_id'])
    
    # Create composite index for common queries
    op.create_index('ix_documents_company_dept_created', 'documents', ['company_id', 'department_id', 'created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_documents_company_dept_created', 'documents')
    op.drop_index('ix_documents_owner_id', 'documents')
    op.drop_index('ix_documents_updated_at', 'documents')
    op.drop_index('ix_documents_file_size', 'documents')
    op.drop_index('ix_documents_classification', 'documents')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_documents_owner_id', 'documents', type_='foreignkey')
    
    # Drop columns
    op.drop_column('documents', 'owner_id')
    op.drop_column('documents', 'updated_at')
    op.drop_column('documents', 'file_size')
    op.drop_column('documents', 'classification')
