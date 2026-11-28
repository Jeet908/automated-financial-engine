"""
tests/test_sse_progress_stream.py — Verification Suite for Real-Time SSE Progress Streaming.
Tests:
1. Progress bus emission, in-memory history ring-buffer, and late-connecting client replay.
2. GET /api/v1/jobs/{job_id}/stream SSE headers (text/event-stream, X-Accel-Buffering: no, Cache-Control: no-cache).
3. Strict tenant isolation (404/403 for unauthorized tenants and cross-tenant job queries).
4. Full 6-gate milestone progression (15%, 32%, 50%, 70%, 88%, 96%, 100%) during valuation execution.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from fastapi.testclient import TestClient

from app import app
from discover_and_run import run_discovery_pipeline as discover_and_run
from src.portal import database
from src.portal.database import Job, User, create_api_key, init_database
from src.portal.progress_bus import (
    emit_job_progress,
    get_job_progress_history,
    subscribe_job_progress,
)


def test_progress_bus_in_memory_and_replay():
    """
    Verify progress bus emits milestones, stores them in history, and
    replays past milestones cleanly to late-connecting subscribers.
    """
    job_id = f"test-sse-bus-{uuid.uuid4()}"

    # 1. Emit 3 milestone events
    emit_job_progress(
        job_id=job_id,
        stage="trial_balance",
        progress_pct=15,
        message="Extracting XBRL balance sheet tags & trial balance...",
        elapsed_s=0.2,
    )
    emit_job_progress(
        job_id=job_id,
        stage="circularity",
        progress_pct=32,
        message="Solving 3-statement circularity & interest roll-forward...",
        elapsed_s=0.8,
    )
    emit_job_progress(
        job_id=job_id,
        stage="completed",
        progress_pct=100,
        message="Valuation completed successfully.",
        elapsed_s=3.2,
        data={"fair_value": 312.4},
        event_type="completed",
    )

    # 2. Check history retrieval
    history = get_job_progress_history(job_id)
    assert len(history) == 3
    assert history[0]["stage"] == "trial_balance"
    assert history[0]["progress_pct"] == 15
    assert history[1]["stage"] == "circularity"
    assert history[1]["progress_pct"] == 32
    assert history[2]["stage"] == "completed"
    assert history[2]["progress_pct"] == 100
    assert history[2]["event_type"] == "completed"

    # 3. Check async subscriber replay
    async def collect_frames():
        frames = []
        async for frame in subscribe_job_progress(job_id, timeout_s=5.0):
            frames.append(frame)
        return frames

    frames = asyncio.run(collect_frames())
    assert len(frames) == 3
    assert frames[0].startswith("event: progress\n")
    assert '"stage": "trial_balance"' in frames[0]
    assert frames[1].startswith("event: progress\n")
    assert '"stage": "circularity"' in frames[1]
    assert frames[2].startswith("event: completed\n")
    assert '"stage": "completed"' in frames[2]


def test_sse_stream_endpoint_and_headers():
    """
    Verify GET /api/v1/jobs/{job_id}/stream returns HTTP 200 with text/event-stream,
    X-Accel-Buffering: no, and Cache-Control: no-cache headers.
    """
    init_database()
    client = TestClient(app)

    tenant_id = f"tenant-sse-{uuid.uuid4()}"
    user_id = f"user-sse-{uuid.uuid4()}"
    job_id = f"job-sse-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        user = User(id=user_id, email=f"analyst_{uuid.uuid4()}@pefund.com", org_id=tenant_id, email_verified=True)
        session.add(user)
        session.flush()
        job = Job(
            id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="valuation",
            workspace_path="/tmp",
            status="running",
        )
        session.add(job)
        session.commit()

        key_rec, raw_secret = create_api_key(
            session,
            tenant_id=tenant_id,
            name="SSE Stream Key",
            scopes=["model:read", "model:write"],
        )

    # Emit a completed frame so the stream terminates cleanly
    emit_job_progress(
        job_id=job_id,
        stage="completed",
        progress_pct=100,
        message="Valuation done.",
        elapsed_s=1.0,
        data={"status": "ok"},
        event_type="completed",
    )

    headers = {"X-API-Key": raw_secret}
    res = client.get(f"/api/v1/jobs/{job_id}/stream", headers=headers)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers.get("content-type", "")
    assert res.headers.get("x-accel-buffering") == "no"
    assert "no-cache" in res.headers.get("cache-control", "")
    assert "event: completed" in res.text


def test_sse_stream_tenant_isolation_404():
    """
    Verify strict tenant isolation: an API key from tenant B querying
    a job belonging to tenant A receives an HTTP 404 response.
    """
    init_database()
    client = TestClient(app)

    tenant_a = f"tenant-a-{uuid.uuid4()}"
    tenant_b = f"tenant-b-{uuid.uuid4()}"
    job_id_a = f"job-a-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        user_a = User(id=f"user-a-{uuid.uuid4()}", email=f"user_a_{uuid.uuid4()}@co.com", org_id=tenant_a, email_verified=True)
        user_b = User(id=f"user-b-{uuid.uuid4()}", email=f"user_b_{uuid.uuid4()}@co.com", org_id=tenant_b, email_verified=True)
        session.add(user_a)
        session.add(user_b)
        session.flush()
        job_a = Job(
            id=job_id_a,
            tenant_id=tenant_a,
            user_id=user_a.id,
            kind="valuation",
            workspace_path="/tmp",
            status="running",
        )
        session.add(job_a)
        session.commit()

        # Key for Tenant B
        _, key_b = create_api_key(
            session,
            tenant_id=tenant_b,
            name="Tenant B Key",
            scopes=["model:read"],
        )

    headers_b = {"X-API-Key": key_b}
    res = client.get(f"/api/v1/jobs/{job_id_a}/stream", headers=headers_b)
    assert res.status_code == 404, "Tenant B must not access Tenant A's SSE stream"

    # Querying a non-existent job must also return 404
    res_none = client.get(f"/api/v1/jobs/non-existent-job-id/stream", headers=headers_b)
    assert res_none.status_code == 404


def test_milestone_instrumentation_live_scrape():
    """
    Verify discover_and_run emits all 6 computational milestones:
    15% (ingestion), 32% (statements), 50% (wacc_dcf), 70% (monte_carlo),
    88% (invariants), and 96% (compilation).
    """
    test_job_id = f"test-milestones-{uuid.uuid4()}"

    result = discover_and_run(domain="Consumer", job_id=test_job_id)
    assert result is not None
    assert "company" in result

    history = get_job_progress_history(test_job_id)
    stages = [h["stage"] for h in history]
    pcts = [h["progress_pct"] for h in history]

    # Verify order of progression
    assert "ingestion" in stages
    assert "statements" in stages
    assert "wacc_dcf" in stages
    assert "monte_carlo" in stages
    assert "invariants" in stages
    assert "compilation" in stages

    assert 15 in pcts
    assert 32 in pcts
    assert 50 in pcts
    assert 70 in pcts
    assert 88 in pcts
    assert 96 in pcts

    # Verify monotonicity of progress percentages
    for i in range(len(pcts) - 1):
        assert pcts[i] <= pcts[i + 1], f"Progress percentages must be non-decreasing: {pcts}"
