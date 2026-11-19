"""Initial tenant schema with RLS policies

Revision ID: 001_tenant_schema
Revises: 
Create Date: 2026-11-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_tenant_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=256), nullable=True),
        sa.Column("google_subject", sa.String(length=255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("session_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terms_version", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_org_id", "users", ["org_id"])

    # Email Tokens
    op.create_table(
        "email_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_email_tokens_user_id", "email_tokens", ["user_id"])
    op.create_index("ix_email_tokens_token_hash", "email_tokens", ["token_hash"], unique=True)

    # Failed Login Attempts
    op.create_table(
        "failed_login_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email_digest", sa.String(length=64), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_failed_login_attempts_email_digest", "failed_login_attempts", ["email_digest"])

    # Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="razorpay"),
        sa.Column("provider_subscription_id", sa.String(length=128), nullable=True),
        sa.Column("provider_plan_id", sa.String(length=128), nullable=True),
        sa.Column("plan_key", sa.String(length=32), nullable=False, server_default="free"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="inactive"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_subscriptions_tenant_id", "subscriptions", ["tenant_id"])

    # Jobs
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("input_name", sa.String(length=255), nullable=True),
        sa.Column("workspace_path", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_tenant_id", "jobs", ["tenant_id"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_status", "jobs", ["status"])

    # Audit Artifacts
    op.create_table(
        "audit_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("s3_key", sa.String(length=512), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("sha256_checksum", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_artifacts_tenant_id", "audit_artifacts", ["tenant_id"])
    op.create_index("ix_audit_artifacts_job_id", "audit_artifacts", ["job_id"])

    # Audit Ledger Entries (Tamper-evident Merkle provenance)
    op.create_table(
        "audit_ledger_entries",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("job_id", sa.String(length=36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("merkle_root_sha256", sa.String(length=64), nullable=False),
        sa.Column("stage_1_raw_input_sha256", sa.String(length=64), nullable=False),
        sa.Column("stage_2_coa_mapping_sha256", sa.String(length=64), nullable=False),
        sa.Column("stage_3_model_solve_sha256", sa.String(length=64), nullable=False),
        sa.Column("lineage_manifest_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_ledger_entries_job_id", "audit_ledger_entries", ["job_id"])
    op.create_index("ix_audit_ledger_entries_tenant_id", "audit_ledger_entries", ["tenant_id"])
    op.create_index("ix_audit_ledger_entries_merkle_root_sha256", "audit_ledger_entries", ["merkle_root_sha256"])

    # Webhook Events
    op.create_table(
        "webhook_events",
        sa.Column("event_id", sa.String(length=128), primary_key=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )

    # PostgreSQL Row Level Security (RLS) enforcement
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;")
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies WHERE tablename = 'jobs' AND policyname = 'tenant_isolation_jobs'
                ) THEN
                    CREATE POLICY tenant_isolation_jobs ON jobs
                        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), ''));
                END IF;
            END
            $$;
        """)
        op.execute("ALTER TABLE audit_artifacts ENABLE ROW LEVEL SECURITY;")
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies WHERE tablename = 'audit_artifacts' AND policyname = 'tenant_isolation_artifacts'
                ) THEN
                    CREATE POLICY tenant_isolation_artifacts ON audit_artifacts
                        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), ''));
                END IF;
            END
            $$;
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS tenant_isolation_artifacts ON audit_artifacts;")
        op.execute("DROP POLICY IF EXISTS tenant_isolation_jobs ON jobs;")
    op.drop_table("webhook_events")
    op.drop_table("audit_artifacts")
    op.drop_table("jobs")
    op.drop_table("subscriptions")
    op.drop_table("failed_login_attempts")
    op.drop_table("email_tokens")
    op.drop_table("users")
