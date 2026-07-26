"""initial schema: tenants, jobs

Revision ID: 0001
Revises:
Create Date: 2026-07-26

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False),
        sa.Column("tenant_secret_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("tenant_secret_previous_encrypted", sa.LargeBinary, nullable=True),
        sa.Column("tenant_secret_previous_expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "allowed_callback_domains",
            postgresql.ARRAY(sa.Text),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("rate_limit_per_minute", sa.Integer, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tenants_api_key_hash", "tenants", ["api_key_hash"], unique=True)

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("doc_type", sa.String(40), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("callback_url", sa.Text, nullable=False),
        sa.Column("pages_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("confidence_overall", sa.Float, nullable=True),
        sa.Column("extracted_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("validation_flags", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("review_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("webhook_delivery_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("webhook_delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_jobs_tenant_created", "jobs", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_tenant_created", table_name="jobs")
    op.drop_table("jobs")
    op.drop_index("ix_tenants_api_key_hash", table_name="tenants")
    op.drop_table("tenants")
