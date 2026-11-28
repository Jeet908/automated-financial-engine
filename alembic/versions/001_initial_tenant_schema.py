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

    # Sector Benchmarks
    op.create_table(
        "sector_benchmarks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("region", sa.String(length=32), nullable=False),
        sa.Column("sector", sa.String(length=64), nullable=False),
        sa.Column("as_of_date", sa.String(length=10), nullable=False),
        sa.Column("median_ev_ebitda", sa.Float(), nullable=False, server_default="12.5"),
        sa.Column("median_ev_revenue", sa.Float(), nullable=False, server_default="3.2"),
        sa.Column("median_beta", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("risk_free_rate", sa.Float(), nullable=False, server_default="0.045"),
        sa.Column("equity_risk_premium", sa.Float(), nullable=False, server_default="0.055"),
        sa.Column("peer_tickers_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_sha256", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sector_benchmarks_region", "sector_benchmarks", ["region"])
    op.create_index("ix_sector_benchmarks_sector", "sector_benchmarks", ["sector"])
    op.create_index("ix_sector_benchmarks_as_of_date", "sector_benchmarks", ["as_of_date"])

    # ERP Connections
    op.create_table(
        "erp_connections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("org_name", sa.String(length=255), nullable=False),
        sa.Column("external_realm_id", sa.String(length=128), nullable=True),
        sa.Column("encrypted_access_token", sa.Text(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scopes", sa.String(length=512), nullable=True),
        sa.Column("sync_frequency", sa.String(length=32), nullable=False, server_default="monthly"),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="connected"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_erp_connections_tenant_id", "erp_connections", ["tenant_id"])
    op.create_index("ix_erp_connections_provider", "erp_connections", ["provider"])
    op.create_index("ix_erp_connections_status", "erp_connections", ["status"])

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("key_prefix", sa.String(length=32), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.String(length=512), nullable=False),
        sa.Column("rate_limit_per_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])

    # API Usage Events
    op.create_table(
        "api_usage_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("api_key_id", sa.String(length=36), sa.ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("endpoint", sa.String(length=128), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("compute_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("billable_units", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_api_usage_events_tenant_id", "api_usage_events", ["tenant_id"])
    op.create_index("ix_api_usage_events_api_key_id", "api_usage_events", ["api_key_id"])
    op.create_index("ix_api_usage_events_endpoint", "api_usage_events", ["endpoint"])

    # SAML Provider Configs
    op.create_table(
        "saml_provider_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("org_slug", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("idp_entity_id", sa.String(length=255), nullable=False),
        sa.Column("idp_sso_url", sa.String(length=512), nullable=False),
        sa.Column("idp_x509_cert_pem", sa.Text(), nullable=False),
        sa.Column("allowed_email_domains", sa.String(length=512), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saml_provider_configs_org_slug", "saml_provider_configs", ["org_slug"], unique=True)
    op.create_index("ix_saml_provider_configs_tenant_id", "saml_provider_configs", ["tenant_id"])

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
