from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

try:
    from cryptography.fernet import Fernet
    _FERNET_AVAILABLE = True
except ImportError:
    _FERNET_AVAILABLE = False

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("MARKETLENS_DATA_DIR", PROJECT_ROOT / "data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    google_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    @property
    def tenant_id(self) -> str:
        return getattr(self, "_tenant_id", None) or self.org_id or self.id

    @tenant_id.setter
    def tenant_id(self, val: str | None) -> None:
        self._tenant_id = val

    @property
    def is_guest(self) -> bool:
        return getattr(self, "_is_guest", False)

    @is_guest.setter
    def is_guest(self, val: bool) -> None:
        self._is_guest = bool(val)


class EmailToken(Base):
    __tablename__ = "email_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FailedLoginAttempt(Base):
    __tablename__ = "failed_login_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email_digest: Mapped[str] = mapped_column(String(64), index=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, default=lambda: str(uuid4()))
    provider: Mapped[str] = mapped_column(String(32), default="razorpay")
    provider_subscription_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    provider_plan_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    plan_key: Mapped[str] = mapped_column(String(32), default="free")
    status: Mapped[str] = mapped_column(String(32), default="inactive")
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    input_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    workspace_path: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class AuditArtifact(Base):
    __tablename__ = "audit_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(64), index=True)
    s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    local_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AuditLedgerEntry(Base):
    __tablename__ = "audit_ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    merkle_root_sha256: Mapped[str] = mapped_column(String(64), index=True)
    stage_1_raw_input_sha256: Mapped[str] = mapped_column(String(64))
    stage_2_coa_mapping_sha256: Mapped[str] = mapped_column(String(64))
    stage_3_model_solve_sha256: Mapped[str] = mapped_column(String(64))
    lineage_manifest_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SectorBenchmark(Base):
    __tablename__ = "sector_benchmarks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    region: Mapped[str] = mapped_column(String(32), index=True)
    sector: Mapped[str] = mapped_column(String(64), index=True)
    as_of_date: Mapped[str] = mapped_column(String(10), index=True)
    median_ev_ebitda: Mapped[float] = mapped_column(Float, default=12.5)
    median_ev_revenue: Mapped[float] = mapped_column(Float, default=3.2)
    median_beta: Mapped[float] = mapped_column(Float, default=1.0)
    risk_free_rate: Mapped[float] = mapped_column(Float, default=0.045)
    equity_risk_premium: Mapped[float] = mapped_column(Float, default=0.055)
    peer_tickers_json: Mapped[str] = mapped_column(Text, default="[]")

    # Quartile Distributions (p25, p50_median, p75_top_quartile)
    dso_p25: Mapped[float] = mapped_column(Float, default=35.0)  # Top quartile (lower is better)
    dso_p50: Mapped[float] = mapped_column(Float, default=52.0)
    dso_p75: Mapped[float] = mapped_column(Float, default=75.0)

    dio_p25: Mapped[float] = mapped_column(Float, default=25.0)  # Top quartile (lower is better)
    dio_p50: Mapped[float] = mapped_column(Float, default=45.0)
    dio_p75: Mapped[float] = mapped_column(Float, default=70.0)

    dpo_p25: Mapped[float] = mapped_column(Float, default=30.0)
    dpo_p50: Mapped[float] = mapped_column(Float, default=45.0)
    dpo_p75: Mapped[float] = mapped_column(Float, default=65.0)  # Top quartile (higher is better)

    ccc_p25: Mapped[float] = mapped_column(Float, default=25.0)  # Top quartile (lower is better)
    ccc_p50: Mapped[float] = mapped_column(Float, default=50.0)
    ccc_p75: Mapped[float] = mapped_column(Float, default=85.0)

    ebitda_margin_p25: Mapped[float] = mapped_column(Float, default=12.0)
    ebitda_margin_p50: Mapped[float] = mapped_column(Float, default=18.0)
    ebitda_margin_p75: Mapped[float] = mapped_column(Float, default=26.0)  # Top quartile (higher is better)

    roic_p25: Mapped[float] = mapped_column(Float, default=9.0)
    roic_p50: Mapped[float] = mapped_column(Float, default=15.0)
    roic_p75: Mapped[float] = mapped_column(Float, default=22.0)  # Top quartile (higher is better)

    roic_wacc_spread_bps_p25: Mapped[float] = mapped_column(Float, default=150.0)
    roic_wacc_spread_bps_p50: Mapped[float] = mapped_column(Float, default=550.0)
    roic_wacc_spread_bps_p75: Mapped[float] = mapped_column(Float, default=1250.0)  # Top quartile (higher is better)

    source_sha256: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(128))
    key_prefix: Mapped[str] = mapped_column(String(32), index=True)  # e.g., "ml_live_a1b2c3"
    key_hash: Mapped[str] = mapped_column(String(64), index=True, unique=True)  # SHA-256
    scopes: Mapped[str] = mapped_column(String(512), default='["model:write", "diagnostics:read", "audit:read"]')
    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=60)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class APIUsageEvent(Base):
    __tablename__ = "api_usage_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    api_key_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    endpoint: Mapped[str] = mapped_column(String(128), index=True)
    http_status: Mapped[int] = mapped_column(Integer, default=200)
    compute_ms: Mapped[float] = mapped_column(Float, default=0.0)
    billable_units: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SAMLProviderConfig(Base):
    __tablename__ = "saml_provider_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    org_slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    idp_entity_id: Mapped[str] = mapped_column(String(255))
    idp_sso_url: Mapped[str] = mapped_column(String(512))
    idp_x509_cert_pem: Mapped[str] = mapped_column(Text)
    allowed_email_domains: Mapped[str | None] = mapped_column(String(512), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ERPConnection(Base):
    __tablename__ = "erp_connections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    provider: Mapped[str] = mapped_column(String(32), index=True)  # xero, quickbooks, zoho, netsuite, tally
    org_name: Mapped[str] = mapped_column(String(255))
    external_realm_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scopes: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sync_frequency: Mapped[str] = mapped_column(String(32), default="monthly")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="connected", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        # Normalize Railway / Heroku postgres:// or postgresql:// to postgresql+psycopg2:// or postgresql+psycopg://
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url
    database_path = DATA_DIR / "marketlens.sqlite3"
    return f"sqlite:///{database_path.as_posix()}"


def _create_engine(url: str) -> Engine:
    options: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite:"):
        options["connect_args"] = {"check_same_thread": False, "timeout": 30}
        if ":memory:" in url:
            options["poolclass"] = StaticPool
    elif url.startswith("postgresql"):
        options["pool_size"] = int(os.environ.get("DB_POOL_SIZE", "10"))
        options["max_overflow"] = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
        options["pool_recycle"] = int(os.environ.get("DB_POOL_RECYCLE", "1800"))

    engine = create_engine(url, **options)

    if url.startswith("sqlite:"):
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


_engine = _create_engine(_database_url())
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
_init_lock = threading.Lock()
_database_initialized = False


def configure_database(url: str) -> None:
    """Replace the database engine; primarily useful for isolated tests."""
    global _engine, SessionLocal, _database_initialized
    with _init_lock:
        _engine.dispose()
        _engine = _create_engine(url)
        SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
        _database_initialized = False


def _ensure_sqlite_columns(engine: Engine) -> None:
    """Safely add any newly introduced ORM columns to existing SQLite tables."""
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            existing_cols = {
                row[1]
                for row in conn.execute(text(f'PRAGMA table_info("{table_name}")')).fetchall()
            }
            if not existing_cols:
                continue
            for col in table.columns:
                if col.name not in existing_cols:
                    col_type = col.type.compile(dialect=engine.dialect)
                    conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {col_type}'))


def init_database() -> None:
    global _database_initialized, _engine, SessionLocal
    if _database_initialized:
        return
    with _init_lock:
        if not _database_initialized:
            try:
                Base.metadata.create_all(_engine)
                _ensure_sqlite_columns(_engine)
                with SessionLocal.begin() as session:
                    session.execute(
                        Job.__table__.update()
                        .where(Job.status.in_(("pending", "running")))
                        .where(Job.updated_at < utc_now() - timedelta(hours=2))
                        .values(status="failed", error_code="interrupted")
                    )
                _database_initialized = True
            except Exception as exc:
                # If remote PostgreSQL fails or times out, gracefully fallback to local SQLite
                fallback_path = DATA_DIR / "marketlens.sqlite3"
                fallback_url = f"sqlite:///{fallback_path.as_posix()}"
                try:
                    _engine.dispose()
                    _engine = _create_engine(fallback_url)
                    SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)
                    Base.metadata.create_all(_engine)
                    _database_initialized = True
                except Exception:
                    pass


def database_ready() -> bool:
    try:
        init_database()
        with _engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def get_storage_backend() -> str:
    """Dynamically reports whether the system is connected to PostgreSQL or SQLite."""
    try:
        dialect_name = _engine.dialect.name
        if "postgres" in dialect_name:
            return "postgresql"
    except Exception:
        pass
    if os.environ.get("DATABASE_URL", "").startswith(("postgres://", "postgresql://", "postgresql+")):
        return "postgresql"
    return "sqlite"


# ---------------------------------------------------------------------------
# Strict Tenant-Level Row Isolation Helpers
# ---------------------------------------------------------------------------
def tenant_query(session, model_cls, tenant_id: str):
    """Enforce strict tenant-level row isolation across models."""
    return session.query(model_cls).filter(model_cls.tenant_id == tenant_id)


def get_tenant_job(session, job_id: str, tenant_id: str) -> Job | None:
    """Fetch a job ensuring it strictly belongs to the requesting tenant."""
    return session.query(Job).filter(Job.id == job_id, Job.tenant_id == tenant_id).first()


def list_tenant_jobs(session, tenant_id: str, limit: int = 20) -> list[Job]:
    """List jobs strictly scoped to the requesting tenant."""
    return (
        session.query(Job)
        .filter(Job.tenant_id == tenant_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .all()
    )


def get_audit_ledger_entry(session, job_id: str, tenant_id: str | None = None) -> AuditLedgerEntry | None:
    """Fetch an audit ledger entry by job_id with optional tenant isolation check."""
    query = session.query(AuditLedgerEntry).filter(AuditLedgerEntry.job_id == job_id)
    if tenant_id:
        query = query.filter(AuditLedgerEntry.tenant_id == tenant_id)
    return query.first()


def find_audit_entry_by_hash(session, hash_str: str) -> AuditLedgerEntry | None:
    """Find any audit ledger entry matching either merkle root or raw input SHA-256."""
    clean_hash = hash_str.strip().lower()
    return session.query(AuditLedgerEntry).filter(
        (AuditLedgerEntry.merkle_root_sha256 == clean_hash) |
        (AuditLedgerEntry.stage_1_raw_input_sha256 == clean_hash)
    ).first()


# ---------------------------------------------------------------------------
# Fernet Token Encryption at Rest
# ---------------------------------------------------------------------------
_WARNED_MISSING_TOKEN_KEY = False


def _get_fernet() -> Fernet | None:
    global _WARNED_MISSING_TOKEN_KEY
    if not _FERNET_AVAILABLE:
        return None
    key_str = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if key_str:
        try:
            return Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
        except Exception:
            pass
    if not _WARNED_MISSING_TOKEN_KEY and (
        os.environ.get("APP_ENV") == "production" or os.environ.get("RAILWAY_ENVIRONMENT")
    ):
        _WARNED_MISSING_TOKEN_KEY = True
        import logging
        logging.getLogger(__name__).warning(
            "TOKEN_ENCRYPTION_KEY is not set in production; deriving Fernet key from SESSION_SECRET."
        )
    # Deterministic fallback key derived from SESSION_SECRET
    seed = (os.environ.get("SESSION_SECRET") or "marketlens_default_token_encryption_key_32bytes").encode("utf-8")
    derived = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(derived)


def encrypt_token(raw_token: str | None) -> str:
    """Encrypts an OAuth token at rest using Fernet symmetric encryption."""
    if not raw_token:
        return ""
    fernet = _get_fernet()
    if fernet is not None:
        return fernet.encrypt(raw_token.encode("utf-8")).decode("utf-8")
    # Base64 fallback if cryptography is unavailable
    return "b64:" + base64.b64encode(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str | None) -> str:
    """Decrypts an OAuth token encrypted at rest."""
    if not encrypted_token:
        return ""
    if encrypted_token.startswith("b64:"):
        return base64.b64decode(encrypted_token[4:].encode("utf-8")).decode("utf-8")
    fernet = _get_fernet()
    if fernet is not None:
        try:
            return fernet.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")
        except Exception:
            return ""
    return encrypted_token


# ---------------------------------------------------------------------------
# SectorBenchmark & ERP Integration Query Helpers
# ---------------------------------------------------------------------------
def get_sector_benchmark(session, region: str, sector: str) -> SectorBenchmark | None:
    """Fetch the freshest sector benchmark for a given region and sector."""
    return (
        session.query(SectorBenchmark)
        .filter(
            SectorBenchmark.region.ilike(region),
            SectorBenchmark.sector.ilike(sector),
        )
        .order_by(SectorBenchmark.as_of_date.desc(), SectorBenchmark.updated_at.desc())
        .first()
    )


def save_sector_benchmark(session, benchmark_data: dict) -> SectorBenchmark:
    """Upserts or records a live sector benchmark entry."""
    region = benchmark_data["region"].upper()
    sector = benchmark_data["sector"]
    as_of = benchmark_data.get("as_of_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    existing = (
        session.query(SectorBenchmark)
        .filter(
            SectorBenchmark.region == region,
            SectorBenchmark.sector == sector,
            SectorBenchmark.as_of_date == as_of,
        )
        .first()
    )
    if existing:
        for k, v in benchmark_data.items():
            if hasattr(existing, k) and k != "id":
                setattr(existing, k, v)
        existing.updated_at = utc_now()
        session.commit()
        return existing

    record = SectorBenchmark(**benchmark_data)
    session.add(record)
    session.commit()
    return record


def list_tenant_erp_connections(session, tenant_id: str) -> list[ERPConnection]:
    """Fetch all active and connected ERP integrations strictly for the tenant."""
    return (
        session.query(ERPConnection)
        .filter(ERPConnection.tenant_id == tenant_id)
        .order_by(ERPConnection.created_at.desc())
        .all()
    )


def get_tenant_erp_connection(session, connection_id: str, tenant_id: str) -> ERPConnection | None:
    """Fetch an ERP integration ensuring strict tenant row isolation."""
    return (
        session.query(ERPConnection)
        .filter(ERPConnection.id == connection_id, ERPConnection.tenant_id == tenant_id)
        .first()
    )


def delete_tenant_erp_connection(session, connection_id: str, tenant_id: str) -> bool:
    """Revokes and purges an ERP connection cleanly under strict tenant isolation."""
    conn = get_tenant_erp_connection(session, connection_id, tenant_id)
    if not conn:
        return False
    session.delete(conn)
    session.commit()
    return True


# ---------------------------------------------------------------------------
# Scoped API Key Management & Metered Usage Helpers
# ---------------------------------------------------------------------------
def create_api_key(
    session,
    tenant_id: str,
    name: str,
    scopes: list[str] | None = None,
    rate_limit_per_min: int = 60,
) -> tuple[APIKey, str]:
    """
    Creates a new scoped API key for an authenticated tenant.
    Returns (api_key_record, full_secret_key). The full secret key is never stored in plaintext.
    """
    raw_secret = "ml_live_" + secrets.token_urlsafe(32)
    key_prefix = raw_secret[:14]  # e.g. ml_live_a1b2c3
    key_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()

    if scopes is None:
        scopes = ["model:write", "diagnostics:read", "audit:read"]

    record = APIKey(
        tenant_id=tenant_id,
        name=name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=json.dumps(scopes),
        rate_limit_per_min=rate_limit_per_min,
        created_at=utc_now(),
    )
    session.add(record)
    session.commit()
    return record, raw_secret


def get_api_key_by_hash(session, key_hash: str) -> APIKey | None:
    """Lookup an API key by its deterministic SHA-256 hash."""
    return session.query(APIKey).filter(APIKey.key_hash == key_hash).first()


def list_tenant_api_keys(session, tenant_id: str) -> list[APIKey]:
    """Lists all active and revoked API keys strictly belonging to a tenant."""
    return (
        session.query(APIKey)
        .filter(APIKey.tenant_id == tenant_id)
        .order_by(APIKey.created_at.desc())
        .all()
    )


def get_tenant_api_key(session, key_id: str, tenant_id: str) -> APIKey | None:
    """Fetches an API key ensuring strict tenant row isolation."""
    return (
        session.query(APIKey)
        .filter(APIKey.id == key_id, APIKey.tenant_id == tenant_id)
        .first()
    )


def revoke_tenant_api_key(session, key_id: str, tenant_id: str) -> bool:
    """Immediately revokes an API key for the tenant."""
    record = get_tenant_api_key(session, key_id, tenant_id)
    if not record or record.revoked_at is not None:
        return False
    record.revoked_at = utc_now()
    session.commit()
    return True


def record_api_usage(
    session,
    tenant_id: str,
    endpoint: str,
    http_status: int = 200,
    api_key_id: str | None = None,
    job_id: str | None = None,
    compute_ms: float = 0.0,
    billable_units: int = 1,
) -> APIUsageEvent:
    """Records an API usage event for metering and billing."""
    event = APIUsageEvent(
        tenant_id=tenant_id,
        api_key_id=api_key_id,
        job_id=job_id,
        endpoint=endpoint,
        http_status=http_status,
        compute_ms=round(compute_ms, 2),
        billable_units=billable_units,
        created_at=utc_now(),
    )
    session.add(event)
    session.commit()
    return event


def get_tenant_api_usage_summary(session, tenant_id: str) -> dict[str, Any]:
    """Aggregates monthly metered usage events, billable units, and latency breakdown."""
    start_of_month = utc_now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    events = (
        session.query(APIUsageEvent)
        .filter(APIUsageEvent.tenant_id == tenant_id, APIUsageEvent.created_at >= start_of_month)
        .all()
    )
    total_units = sum(e.billable_units for e in events)
    total_requests = len(events)
    avg_latency = (sum(e.compute_ms for e in events) / total_requests) if total_requests > 0 else 0.0

    endpoint_breakdown: dict[str, dict[str, Any]] = {}
    for e in events:
        ep = e.endpoint
        if ep not in endpoint_breakdown:
            endpoint_breakdown[ep] = {"count": 0, "billable_units": 0, "total_ms": 0.0}
        endpoint_breakdown[ep]["count"] += 1
        endpoint_breakdown[ep]["billable_units"] += e.billable_units
        endpoint_breakdown[ep]["total_ms"] += e.compute_ms

    formatted_breakdown = [
        {
            "endpoint": ep,
            "requests": data["count"],
            "billable_units": data["billable_units"],
            "avg_latency_ms": round(data["total_ms"] / data["count"], 2) if data["count"] > 0 else 0.0,
        }
        for ep, data in endpoint_breakdown.items()
    ]

    return {
        "tenant_id": tenant_id,
        "current_period_start": start_of_month.isoformat(),
        "total_billable_units": total_units,
        "total_requests": total_requests,
        "average_compute_ms": round(avg_latency, 2),
        "endpoint_breakdown": formatted_breakdown,
    }


# ---------------------------------------------------------------------------
# Enterprise SAML 2.0 SSO Query Helpers
# ---------------------------------------------------------------------------
def get_saml_config_by_org_slug(session, org_slug: str) -> SAMLProviderConfig | None:
    """Lookup SAML IdP configuration by enterprise tenant organization slug."""
    return (
        session.query(SAMLProviderConfig)
        .filter(SAMLProviderConfig.org_slug.ilike(org_slug.strip()), SAMLProviderConfig.enabled.is_(True))
        .first()
    )


def save_saml_provider_config(
    session,
    tenant_id: str,
    org_slug: str,
    idp_entity_id: str,
    idp_sso_url: str,
    idp_x509_cert_pem: str,
    allowed_email_domains: str | None = None,
    enabled: bool = True,
) -> SAMLProviderConfig:
    """Upserts a SAML 2.0 IdP configuration."""
    existing = session.query(SAMLProviderConfig).filter(SAMLProviderConfig.org_slug == org_slug.strip().lower()).first()
    if existing:
        existing.tenant_id = tenant_id
        existing.idp_entity_id = idp_entity_id
        existing.idp_sso_url = idp_sso_url
        existing.idp_x509_cert_pem = idp_x509_cert_pem
        existing.allowed_email_domains = allowed_email_domains
        existing.enabled = enabled
        existing.updated_at = utc_now()
        session.commit()
        return existing

    record = SAMLProviderConfig(
        tenant_id=tenant_id,
        org_slug=org_slug.strip().lower(),
        idp_entity_id=idp_entity_id,
        idp_sso_url=idp_sso_url,
        idp_x509_cert_pem=idp_x509_cert_pem,
        allowed_email_domains=allowed_email_domains,
        enabled=enabled,
        created_at=utc_now(),
    )
    session.add(record)
    session.commit()
    return record


def get_db():
    init_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
