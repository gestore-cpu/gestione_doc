"""Manus user mapping + coverage report"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250811_manus_mapping_coverage"
down_revision = None  # <-- metti l'ultima tua revision come down_revision
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "manus_user_mapping",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("manus_user_id", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("syn_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_mum_manus_user_id", "manus_user_mapping", ["manus_user_id"], unique=True)
    op.create_index("ix_mum_email", "manus_user_mapping", ["email"], unique=False)

    op.create_table(
        "training_coverage_report",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("azienda_id", sa.Integer, sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("requisito_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False, server_default=sa.text("'manus'")),
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
        sa.Column("updated_at", sa.DateTime, nullable=True),
        sa.UniqueConstraint("user_id", "requisito_id", name="uq_cov_user_req"),
    )

def downgrade():
    op.drop_table("training_coverage_report")
    op.drop_index("ix_mum_email", table_name="manus_user_mapping")
    op.drop_index("ix_mum_manus_user_id", table_name="manus_user_mapping")
    op.drop_table("manus_user_mapping")
