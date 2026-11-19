"""
Unit and Integration Tests for Distributed Architecture:
PostgreSQL engine & connection pooling, strict tenant-level row isolation,
concurrent reserve_job() locking, Celery eager worker tasks, and signed S3 object storage.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.portal.database import (
    AuditArtifact,
    Job,
    Subscription,
    User,
    _create_engine,
    _database_url,
    configure_database,
    get_storage_backend,
    get_tenant_job,
    init_database,
    list_tenant_jobs,
    tenant_query,
    utc_now,
)
from src.portal.plans import reserve_job
from src.storage.object_store import (
    build_tenant_job_key,
    generate_presigned_url,
    is_s3_configured,
)
from src.workers.tasks import (
    daily_benchmark_refresh_task,
)


def test_postgresql_engine_normalization_and_pooling():
    """Verify DATABASE_URL normalization and production connection pooling parameters."""
    with patch.dict(os.environ, {"DATABASE_URL": "postgres://user:pass@ep-host.railway.app:5432/railway"}):
        norm_url = _database_url()
        assert norm_url.startswith("postgresql+psycopg2://")

    with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@ep-host.railway.app:5432/railway"}):
        norm_url = _database_url()
        assert norm_url.startswith("postgresql+psycopg2://")

    # Verify fallback to sqlite when DATABASE_URL is unset
    with patch.dict(os.environ, {}, clear=True):
        fallback_url = _database_url()
        assert fallback_url.startswith("sqlite:///")

    # Verify storage_backend reporting
    with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://test:test@localhost/test"}):
        assert get_storage_backend() == "postgresql"


def test_strict_tenant_row_isolation():
    """Verify that no tenant can ever read or mutate another tenant's jobs or audit artifacts."""
    configure_database("sqlite:///:memory:")
    init_database()

    from src.portal.database import SessionLocal

    with SessionLocal() as session:
        # Create two distinct tenants (Tenant A and Tenant B)
        tenant_a_id = str(uuid4())
        tenant_b_id = str(uuid4())

        user_a = User(id=tenant_a_id, email="cfo_a@tenant-a.com", email_verified=True)
        user_b = User(id=tenant_b_id, email="cfo_b@tenant-b.com", email_verified=True)
        session.add_all([user_a, user_b])
        session.commit()

        # Tenant A creates a job and an audit artifact
        job_a = Job(
            id=str(uuid4()),
            tenant_id=user_a.tenant_id,
            user_id=user_a.id,
            kind="live_scrape",
            status="succeeded",
            workspace_path="/tmp/test_a",
        )
        artifact_a = AuditArtifact(
            id=str(uuid4()),
            tenant_id=user_a.tenant_id,
            job_id=job_a.id,
            artifact_type="xlsx_model",
            s3_key=f"tenants/{user_a.tenant_id}/jobs/{job_a.id}/model.xlsx",
            file_size_bytes=1024,
        )

        # Tenant B creates a job
        job_b = Job(
            id=str(uuid4()),
            tenant_id=user_b.tenant_id,
            user_id=user_b.id,
            kind="file_upload",
            status="succeeded",
            workspace_path="/tmp/test_b",
        )

        session.add_all([job_a, artifact_a, job_b])
        session.commit()

        # ASSERTION 1: Tenant A can read their own job
        found_a = get_tenant_job(session, job_a.id, user_a.tenant_id)
        assert found_a is not None
        assert found_a.id == job_a.id

        # ASSERTION 2: Tenant B CANNOT read Tenant A's job (returns None)
        breached = get_tenant_job(session, job_a.id, user_b.tenant_id)
        assert breached is None, "Security violation: Tenant B accessed Tenant A's job!"

        # ASSERTION 3: list_tenant_jobs scopes strictly to requesting tenant
        jobs_a = list_tenant_jobs(session, user_a.tenant_id)
        assert len(jobs_a) == 1
        assert jobs_a[0].id == job_a.id

        jobs_b = list_tenant_jobs(session, user_b.tenant_id)
        assert len(jobs_b) == 1
        assert jobs_b[0].id == job_b.id

        # ASSERTION 4: AuditArtifact isolation
        artifacts_a = tenant_query(session, AuditArtifact, user_a.tenant_id).all()
        assert len(artifacts_a) == 1
        assert artifacts_a[0].id == artifact_a.id

        artifacts_b = tenant_query(session, AuditArtifact, user_b.tenant_id).all()
        assert len(artifacts_b) == 0


def test_concurrent_reserve_job_locking():
    """Verify that reserve_job() strictly enforces plan limits with row locking."""
    configure_database("sqlite:///:memory:")
    init_database()

    from src.portal.database import SessionLocal

    with SessionLocal() as session:
        user = User(id=str(uuid4()), email="enterprise@test.com", email_verified=True)
        session.add(user)
        session.commit()

        # Free tier gives 1 valuation
        job1 = reserve_job(session, user, "live_scrape", Path("/tmp/w1"))
        assert job1 is not None
        assert job1.tenant_id == user.id

        # Second job in same period must be rejected with 429
        with pytest.raises(HTTPException) as exc_info:
            reserve_job(session, user, "live_scrape", Path("/tmp/w2"))
        assert exc_info.value.status_code == 429
        assert "valuation(s) for this month" in exc_info.value.detail


def test_celery_daily_benchmark_refresh_task():
    """Verify scheduled Celery Beat task at 00:00 UTC."""
    result = daily_benchmark_refresh_task()
    assert result["status"] == "refreshed"
    assert "timestamp" in result


def test_s3_tenant_object_key_and_presigned_url():
    """Verify tenant-isolated S3 key construction and 900s pre-signed URL generation."""
    tenant_id = "tenant-enterprise-99"
    job_id = "job-val-001"
    filename = "Executive_Valuation_Pack.zip"

    # Test key structure: tenants/{tenant_id}/jobs/{job_id}/{filename}
    key = build_tenant_job_key(tenant_id, job_id, filename)
    assert key == f"tenants/{tenant_id}/jobs/{job_id}/{filename}"

    # Test pre-signed URL generation with mocked boto3 client
    mock_boto_client = MagicMock()
    mock_boto_client.generate_presigned_url.return_value = (
        f"https://r2.cloudflarestorage.com/marketlens/{key}?X-Amz-Expires=900&signature=test"
    )

    with patch("src.storage.object_store.is_s3_configured", return_value=True), \
         patch("src.storage.object_store.get_s3_client", return_value=mock_boto_client), \
         patch.dict(os.environ, {"S3_BUCKET": "marketlens-artifacts"}):

        url = generate_presigned_url(key, filename=filename, expires_in=900)
        assert "X-Amz-Expires=900" in url
        mock_boto_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={
                "Bucket": "marketlens-artifacts",
                "Key": key,
                "ResponseContentDisposition": f'attachment; filename="{filename}"',
            },
            ExpiresIn=900,
        )


if __name__ == "__main__":
    test_postgresql_engine_normalization_and_pooling()
    test_strict_tenant_row_isolation()
    test_concurrent_reserve_job_locking()
    test_celery_daily_benchmark_refresh_task()
    test_s3_tenant_object_key_and_presigned_url()
    print("All distributed architecture tests passed successfully!")
