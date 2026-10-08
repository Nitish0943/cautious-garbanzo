"""Initial schema: generation_jobs and certificates

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-07 23:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create generation_jobs table
    op.create_table(
        "generation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("course_name", sa.String(length=255), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=False),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_generation_jobs_id"), "generation_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_generation_jobs_status"), "generation_jobs", ["status"], unique=False)

    # 2. Create certificates table
    op.create_table(
        "certificates",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("file_path", sa.String(length=500), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f("ix_certificates_id"), "certificates", ["id"], unique=False)
    op.create_index(op.f("ix_certificates_job_id"), "certificates", ["job_id"], unique=False)
    op.create_index(op.f("ix_certificates_recipient_email"), "certificates", ["recipient_email"], unique=False)
    op.create_index(op.f("ix_certificates_status"), "certificates", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_certificates_status"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_recipient_email"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_job_id"), table_name="certificates")
    op.drop_index(op.f("ix_certificates_id"), table_name="certificates")
    op.drop_table("certificates")

    op.drop_index(op.f("ix_generation_jobs_status"), table_name="generation_jobs")
    op.drop_index(op.f("ix_generation_jobs_id"), table_name="generation_jobs")
    op.drop_table("generation_jobs")
