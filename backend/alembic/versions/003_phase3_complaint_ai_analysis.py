"""Phase 3 database schema (complaint_ai_analyses)

Revision ID: 003_phase3_complaint_ai_analysis
Revises: 002_phase2_complaints
Create Date: 2026-10-07 19:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003_phase3_complaint_ai_analysis"
down_revision: Union[str, None] = "002_phase2_complaints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "complaint_ai_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("complaint_id", sa.Uuid(), nullable=False),
        sa.Column("predicted_category", sa.String(length=50), nullable=False),
        sa.Column("category_confidence", sa.Float(), nullable=False),
        sa.Column("recommended_department_name", sa.String(length=100), nullable=False),
        sa.Column("recommended_department_code", sa.String(length=50), nullable=False),
        sa.Column("recommended_department_id", sa.Integer(), nullable=True),
        sa.Column("predicted_priority", sa.String(length=20), nullable=False),
        sa.Column("urgency_score", sa.Float(), nullable=False),
        sa.Column("is_low_confidence", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("model_version", sa.String(length=50), nullable=False, server_default="tfidf-logreg-v1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["complaint_id"], ["complaints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommended_department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("complaint_id", name="uq_complaint_ai_analyses_complaint_id"),
    )
    op.create_index(op.f("ix_complaint_ai_analyses_complaint_id"), "complaint_ai_analyses", ["complaint_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_complaint_ai_analyses_complaint_id"), table_name="complaint_ai_analyses")
    op.drop_table("complaint_ai_analyses")
