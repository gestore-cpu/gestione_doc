"""Add security and audit tables

Revision ID: 001_security
Revises: 
Create Date: 2025-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_security'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create security_audit_log table
    op.create_table('security_audit_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('ip', sa.String(length=45), nullable=False),
    sa.Column('action', sa.String(length=100), nullable=False),
    sa.Column('object_type', sa.String(length=50), nullable=True),
    sa.Column('object_id', sa.Integer(), nullable=True),
    sa.Column('meta', sa.JSON(), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_audit_log_ts', 'security_audit_log', ['ts'], unique=False)
    op.create_index('ix_security_audit_log_user_id', 'security_audit_log', ['user_id'], unique=False)
    
    # Create security_alert table
    op.create_table('security_alert',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('rule_id', sa.String(length=50), nullable=False),
    sa.Column('severity', sa.Enum('low', 'medium', 'high', name='severitylevel'), nullable=False),
    sa.Column('details', sa.Text(), nullable=False),
    sa.Column('status', sa.Enum('open', 'closed', name='alertstatus'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_security_alert_ts', 'security_alert', ['ts'], unique=False)
    op.create_index('ix_security_alert_user_id', 'security_alert', ['user_id'], unique=False)
    op.create_index('ix_security_alert_severity', 'security_alert', ['severity'], unique=False)
    op.create_index('ix_security_alert_status', 'security_alert', ['status'], unique=False)
    
    # Create file_hash table
    op.create_table('file_hash',
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('algo', sa.String(length=10), nullable=False),
    sa.Column('value', sa.String(length=256), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('file_id')
    )
    
    # Create antivirus_scan table
    op.create_table('antivirus_scan',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('file_id', sa.Integer(), nullable=False),
    sa.Column('engine', sa.String(length=50), nullable=False),
    sa.Column('signature', sa.String(length=100), nullable=False),
    sa.Column('verdict', sa.Enum('clean', 'infected', name='antivirusverdict'), nullable=False),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['file_id'], ['documents.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_antivirus_scan_file_id', 'antivirus_scan', ['file_id'], unique=False)
    op.create_index('ix_antivirus_scan_ts', 'antivirus_scan', ['ts'], unique=False)


def downgrade():
    op.drop_index('ix_antivirus_scan_ts', table_name='antivirus_scan')
    op.drop_index('ix_antivirus_scan_file_id', table_name='antivirus_scan')
    op.drop_table('antivirus_scan')
    op.drop_table('file_hash')
    op.drop_index('ix_security_alert_status', table_name='security_alert')
    op.drop_index('ix_security_alert_severity', table_name='security_alert')
    op.drop_index('ix_security_alert_user_id', table_name='security_alert')
    op.drop_index('ix_security_alert_ts', table_name='security_alert')
    op.drop_table('security_alert')
    op.drop_index('ix_security_audit_log_user_id', table_name='security_audit_log')
    op.drop_index('ix_security_audit_log_ts', table_name='security_audit_log')
    op.drop_table('security_audit_log')
