"""merge heads for DownloadAlert

Revision ID: f4a6e23dd580
Revises: 002_file_manager, add_log_reminder_visita, auto_policies_001, create_visite_mediche_table
Create Date: 2025-08-11 07:50:36.239288

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a6e23dd580'
down_revision = ('002_file_manager', 'add_log_reminder_visita', 'auto_policies_001', 'create_visite_mediche_table')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
