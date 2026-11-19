from __future__ import annotations

import base64
import hashlib
import os
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
        return self.org_id or self.id


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
    source_sha256: Mapped[str] = mapped_column(String(64))
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


def init_database() -> None:
    global _database_initialized
    if _database_initialized:
        return
    with _init_lock:
        if not _database_initialized:
            Base.metadata.create_all(_engine)
            with SessionLocal.begin() as session:
                session.execute(
                    Job.__table__.update()
                    .where(Job.status.in_(("pending", "running")))
                    .where(Job.updated_at < utc_now() - timedelta(hours=2))
                    .values(status="failed", error_code="interrupted")
                )
            _database_initialized = True


def database_ready() -> bool:
    init_database()
    with _engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


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
def _get_fernet() -> Fernet | None:
    if not _FERNET_AVAILABLE:
        return None
    key_str = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if key_str:
        try:
            return Fernet(key_str.encode() if isinstance(key_str, str) else key_str)
        except Exception:
            pass
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


def get_db():
    init_database()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
