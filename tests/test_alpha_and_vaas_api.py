"""
Verification Suite for C-Suite Decision & Alpha API and Metered VaaS Platform.
Tests:
1. Top-Quartile peer benchmarking math across DSO, DIO, DPO, EBITDA margin, and ROIC-vs-WACC spread.
2. POST /api/v1/diagnostics/what-if simulation preserving Max Err: 0.000000e+00 across all 6 invariants.
3. Scoped API Key lifecycle: creation, X-API-Key authentication, scope enforcement (403), rate limiting (429), revocation (401), and APIUsageEvent metering.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from io import BytesIO
from typing import Any, Dict

from fastapi.testclient import TestClient

from app import app
from financial_engine.engine import FinancialEngine
from financial_engine.reporting.pain_points import DEFAULT_QUARTILES, diagnose_pain_points
from src.mesh.regulatory_mesh import get_live_benchmark_multiples
from src.portal import database
from src.portal.database import (
    APIKey,
    APIUsageEvent,
    Job,
    User,
    create_api_key,
    get_tenant_api_usage_summary,
    init_database,
)


def test_top_quartile_peer_benchmarking_math():
    """
    Verify top-quartile peer benchmarking math across DSO, DIO, DPO, EBITDA margin,
    and ROIC-vs-WACC spread with quantified operational prescriptions.
    """
    engine = FinancialEngine.from_template("kaveri_foods")
    model = engine.solve(run_mc=False, run_scenarios=False)

    # Fetch live top-quartile distributions
    benchmark = get_live_benchmark_multiples(region="INDIA", sector="Consumer & Food Processing")
    assert "quartiles" in benchmark
    assert "dso" in benchmark["quartiles"]
    assert "ebitda_margin" in benchmark["quartiles"]

    pain_points = diagnose_pain_points(model, wacc=model.wacc, peer_benchmark=benchmark)
    assert len(pain_points) == 3

    # Check that items have priority ranks 1, 2, 3
    ranks = [p["priority_rank"] for p in pain_points]
    assert ranks == [1, 2, 3]

    for p in pain_points:
        assert "category" in p
        assert "summary" in p
        assert "client_value" in p
        assert "peer_median" in p
        assert "peer_top_quartile" in p
        assert "gap_to_top_quartile" in p
        assert "implied_ev_unlock" in p
        assert "valuation_alpha_pct" in p
        assert "owner_role" in p
        assert "action_playbook" in p
        assert len(p["action_playbook"]) > 10
        assert p["gap_to_top_quartile"] >= 0.0

    # Specifically verify Working Capital & CCC item
    ccc_item = next(p for p in pain_points if p["category"] == "Working Capital & CCC")
    assert "dso_breakdown" in ccc_item
    assert "dio_breakdown" in ccc_item
    assert "dpo_breakdown" in ccc_item
    assert ccc_item["dso_breakdown"]["client_value"] > 0
    assert ccc_item["dso_breakdown"]["peer_top_quartile"] > 0
    assert ccc_item["cash_trapped"] >= 0.0

    # Specifically verify Operating Margins item
    margin_item = next(p for p in pain_points if p["category"] == "Operating Margins")
    assert margin_item["client_value"] > 0.0
    assert margin_item["peer_top_quartile"] >= margin_item["peer_median"]
    assert margin_item["annual_ebitda_opportunity"] >= 0.0

    # Specifically verify Capital Allocation item
    roic_item = next(p for p in pain_points if p["category"] == "Capital Allocation")
    assert roic_item["client_value"] > 0.0
    assert roic_item["peer_top_quartile"] > 0.0


def test_diagnostics_what_if_and_invariants():
    """
    Verify POST /api/v1/diagnostics/what-if returns accurate valuation deltas
    and strictly preserves Max Err: 0.000000e+00 across all 6 accounting invariants.
    """
    init_database()
    client = TestClient(app)

    tenant_id = f"tenant-whatif-{uuid.uuid4()}"
    user_id = f"user-{uuid.uuid4()}"
    job_id = f"job-whatif-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        user = User(id=user_id, email=f"cfo_{uuid.uuid4()}@fund.com", org_id=tenant_id, email_verified=True)
        session.add(user)
        job = Job(
            id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="valuation",
            workspace_path="/tmp",
            status="succeeded",
            result_json=json.dumps({
                "company": {
                    "name": "Kaveri Alpha Corp",
                    "ticker": "KAVERI",
                    "industry": "Consumer & Food Processing",
                    "currency": "INR",
                }
            }),
        )
        session.add(job)

        # Create API key with diagnostics:read scope
        key_rec, raw_secret = create_api_key(
            session,
            tenant_id=tenant_id,
            name="WhatIf Test Key",
            scopes=["diagnostics:read", "model:write"],
            rate_limit_per_min=60,
        )

    headers = {"X-API-Key": raw_secret}

    # 1. Test GET /api/v1/diagnostics/{job_id}
    res_diag = client.get(f"/api/v1/diagnostics/{job_id}", headers=headers)
    assert res_diag.status_code == 200
    diag_data = res_diag.json()
    assert diag_data["job_id"] == job_id
    assert diag_data["overall_health_score"] > 0
    assert "peer_benchmark_context" in diag_data
    assert len(diag_data["pain_points"]) == 3
    assert diag_data["total_alpha_unlock_pct"] >= 0

    # 2. Test POST /api/v1/diagnostics/what-if
    sim_payload = {
        "job_id": job_id,
        "target_dso_days": 32.0,
        "target_dio_days": 25.0,
        "target_dpo_days": 65.0,
        "ebitda_margin_uplift_bps": 250.0,
        "debt_paydown_amount": 25.0,
    }
    res_sim = client.post("/api/v1/diagnostics/what-if", json=sim_payload, headers=headers)
    assert res_sim.status_code == 200
    sim_data = res_sim.json()

    assert sim_data["status"] == "success"
    assert sim_data["invariants_passed"] is True
    assert sim_data["max_discrepancy"] == 0.0, "Zero invariant discrepancy required (Max Err: 0.000000e+00)"

    # Valuation uplift assertions
    assert sim_data["simulated"]["enterprise_value"] > sim_data["baseline"]["enterprise_value"]
    assert sim_data["simulated"]["implied_share_price"] > sim_data["baseline"]["implied_share_price"]
    assert sim_data["deltas"]["delta_enterprise_value"] > 0
    assert sim_data["deltas"]["alpha_upside_pct"] > 0
    assert sim_data["deltas"]["delta_5yr_cumulative_fcff"] > 0
    assert "target_dso_days" in sim_data["levers_applied"]


def test_scoped_api_key_lifecycle_and_metering():
    """
    Verify scoped API key vault lifecycle:
    creation -> X-API-Key authentication -> scope check (403) -> rate limit (429) -> revocation (401) -> metering.
    """
    init_database()
    client = TestClient(app)

    tenant_id = f"tenant-vaas-{uuid.uuid4()}"
    user_id = f"user-{uuid.uuid4()}"
    job_id = f"job-vaas-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        user = User(id=user_id, email=f"dev_{uuid.uuid4()}@pefirm.com", org_id=tenant_id, email_verified=True)
        session.add(user)
        job = Job(
            id=job_id,
            tenant_id=tenant_id,
            user_id=user_id,
            kind="valuation",
            workspace_path="/tmp",
            status="succeeded",
            result_json=json.dumps({"company": {"name": "Test Co", "currency": "USD"}}),
        )
        session.add(job)
        session.commit()

        # 1. Create scoped key with rate limit 4 req/min, omitting audit:read
        key_rec, raw_secret = create_api_key(
            session,
            tenant_id=tenant_id,
            name="VaaS Metered Key",
            scopes=["model:write", "diagnostics:read"],
            rate_limit_per_min=4,
        )
        key_id = key_rec.id

    assert raw_secret.startswith("ml_live_")

    # Verify secret is never stored in plaintext
    with database.SessionLocal() as session:
        stored_key = session.query(APIKey).filter(APIKey.id == key_id).first()
        assert stored_key is not None
        assert stored_key.key_hash == hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
        assert raw_secret not in stored_key.key_hash

    headers = {"X-API-Key": raw_secret}

    # 2. Authenticate diagnostics:read
    res_diag = client.get(f"/api/v1/diagnostics/{job_id}", headers=headers)
    assert res_diag.status_code == 200

    # 3. Assert 403 when scope is missing (audit:read)
    res_audit = client.get(f"/api/v1/audit/verify/{job_id}", headers=headers)
    assert res_audit.status_code == 403, "Must return 403 when key lacks audit:read scope"

    # 4. Assert 429 when rate limit (4 req/min) is breached
    rate_limited = False
    for _ in range(5):
        resp = client.get(f"/api/v1/diagnostics/{job_id}", headers=headers)
        if resp.status_code == 429:
            rate_limited = True
            break
    assert rate_limited, "Must enforce sliding-window rate limit and return HTTP 429"

    # Reset in-memory rate limit window to test revocation
    from src.portal.dependencies import _RATE_LIMIT_WINDOWS
    _RATE_LIMIT_WINDOWS.pop(key_id, None)

    # 5. Revoke key via DELETE /api/v1/keys/{key_id}
    del_res = client.delete(f"/api/v1/keys/{key_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["revoked"] is True

    # 6. Assert 401 when using revoked key
    res_revoked = client.get(f"/api/v1/diagnostics/{job_id}", headers=headers)
    assert res_revoked.status_code == 401, "Revoked key must immediately return HTTP 401"

    # 7. Assert APIUsageEvent metering records
    with database.SessionLocal() as session:
        events = session.query(APIUsageEvent).filter(APIUsageEvent.tenant_id == tenant_id).all()
        assert len(events) >= 2, "Metered APIUsageEvent records must be persisted"
        summary = get_tenant_api_usage_summary(session, tenant_id)
        assert summary["total_billable_units"] >= 1
        assert len(summary["endpoint_breakdown"]) >= 1


def test_api_keys_management_and_usage_endpoints():
    """
    Verify GET /api/v1/keys, POST /api/v1/keys, and GET /api/v1/keys/usage endpoints.
    """
    init_database()
    client = TestClient(app)

    tenant_id = f"tenant-mgmt-{uuid.uuid4()}"
    user_id = f"user-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        user = User(id=user_id, email=f"admin_{uuid.uuid4()}@fintech.com", org_id=tenant_id, email_verified=True)
        session.add(user)
        key_rec, raw_secret = create_api_key(
            session,
            tenant_id=tenant_id,
            name="Admin Key",
            scopes=["model:write", "diagnostics:read", "audit:read"],
            rate_limit_per_min=100,
        )

    headers = {"Authorization": f"Bearer {raw_secret}"}

    # 1. List keys
    list_res = client.get("/api/v1/keys", headers=headers)
    assert list_res.status_code == 200
    data = list_res.json()
    assert "keys" in data
    assert len(data["keys"]) >= 1
    assert data["keys"][0]["key_prefix"].startswith("ml_live_")

    # 2. Create another key via POST /api/v1/keys
    create_payload = {
        "name": "Underwriting Ingestion Bot",
        "scopes": ["model:write"],
        "rate_limit_per_min": 120,
    }
    create_res = client.post("/api/v1/keys", json=create_payload, headers=headers)
    assert create_res.status_code == 201
    new_key = create_res.json()
    assert new_key["secret_key"].startswith("ml_live_")
    assert new_key["name"] == "Underwriting Ingestion Bot"

    # 3. Query usage summary
    usage_res = client.get("/api/v1/keys/usage", headers=headers)
    assert usage_res.status_code == 200
    usage_data = usage_res.json()
    assert usage_data["tenant_id"] == tenant_id
    assert "total_billable_units" in usage_data
    assert "remaining_quota" in usage_data
