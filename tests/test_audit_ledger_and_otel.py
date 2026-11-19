"""
Comprehensive Verification Suite for Cryptographic Audit Ledger & OpenTelemetry Observability.
Tests Big-4 verifiability, SHA-256 Merkle root determinism, tamper-detection,
deliverable embedding, SLA monitoring, and upstream schema drift detection.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory

import openpyxl
from fastapi.testclient import TestClient

from app import app
from financial_engine.audit.provenance import (
    LineageNode,
    ProvenanceChain,
    SourceFact,
    build_provenance_ledger,
    canonical_json_hash,
    compute_merkle_root,
    sha256_bytes,
)
from src.exporters.tabs.tab_09_audit_ledger import build_audit_ledger
from src.ingestion.live_web_scraper import detect_schema_drift
from src.observability.telemetry import (
    record_invariant_discrepancy,
    record_pipeline_duration,
    record_schema_drift,
    record_scraper_latency,
    sla_tracker,
    trace_span,
)
from src.portal import database
from src.portal.database import (
    AuditLedgerEntry,
    Job,
    User,
    find_audit_entry_by_hash,
    get_audit_ledger_entry,
    init_database,
)


def test_canonical_source_fact_determinism():
    """Verify that SourceFact SHA-256 is deterministic and invariant to dictionary key ordering."""
    f1 = SourceFact(
        fact_id="FACT-001",
        source_system="SEC_EDGAR_XBRL",
        gl_code_or_xbrl_tag="us-gaap:Revenues",
        account_name="Total Operating Revenue",
        period="FY24A",
        raw_value=24500.0,
        currency="USD",
        unit_scale="USD_MILLION",
        source_file_sha256="a" * 64,
    )
    f2 = SourceFact(
        fact_id="FACT-001",
        source_system="SEC_EDGAR_XBRL",
        gl_code_or_xbrl_tag="us-gaap:Revenues",
        account_name="Total Operating Revenue",
        period="FY24A",
        raw_value=24500.0,
        currency="usd",  # normalized to uppercase
        unit_scale="usd_million",  # normalized to uppercase
        source_file_sha256="a" * 64,
    )

    assert f1.fact_sha256 == f2.fact_sha256
    assert len(f1.fact_sha256) == 64
    assert f1.compute_hash() == f1.fact_sha256


def test_merkle_tree_root_determinism_and_tamper_detection():
    """Verify deterministic Merkle root generation and sensitivity to any single-digit tamper."""
    nodes = [
        LineageNode(
            output_metric="Revenue_FY24",
            target_cell_ref="'03_Income_Statement'!C5",
            source_gl_or_xbrl="us-gaap:Revenues",
            formula="=SUM(Vouchers)",
            value=1000.0,
        ),
        LineageNode(
            output_metric="EBITDA_FY24",
            target_cell_ref="'03_Income_Statement'!C10",
            source_gl_or_xbrl="CALCULATED",
            formula="=Rev-COGS-OpEx",
            value=250.0,
        ),
        LineageNode(
            output_metric="Fair_Value_Per_Share",
            target_cell_ref="'07_DCF'!C20",
            source_gl_or_xbrl="DCF_MODEL",
            formula="=EqVal/Shares",
            value=185.50,
        ),
    ]

    root_original = compute_merkle_root([n.node_sha256 for n in nodes])
    assert len(root_original) == 64

    # Reordering nodes should yield the EXACT same Merkle root due to canonical sorting
    reversed_nodes = list(reversed(nodes))
    root_reversed = compute_merkle_root([n.node_sha256 for n in reversed_nodes])
    assert root_original == root_reversed, "Merkle root must be canonically deterministic regardless of input order"

    # Tampering a single value MUST change the Merkle root
    tampered_nodes = [
        LineageNode(
            output_metric="Revenue_FY24",
            target_cell_ref="'03_Income_Statement'!C5",
            source_gl_or_xbrl="us-gaap:Revenues",
            formula="=SUM(Vouchers)",
            value=1000.01,  # 1-cent discrepancy
        ),
        nodes[1],
        nodes[2],
    ]
    root_tampered = compute_merkle_root([n.node_sha256 for n in tampered_nodes])
    assert root_tampered != root_original, "Any modification must immediately alter the Merkle root"


def test_four_stage_provenance_chain_integrity():
    """Verify end-to-end 4-stage provenance chain creation and integrity validation."""
    raw_payload = b"Sample_Raw_Trial_Balance_Vouchers_FY24"
    coa_map = {"revenue": "GL-4010", "cogs": "GL-5010", "cash": "GL-1010"}
    model_data = {"enterprise_value": 7500.0, "equity_value": 6800.0, "value_per_share": 245.0}
    inv_status = {"all_passed": True, "overall_status": "PASSED", "max_discrepancy": 0.0}

    chain = build_provenance_ledger(
        job_id="JOB-AUDIT-TEST-001",
        raw_input=raw_payload,
        coa_mapping=coa_map,
        model_data=model_data,
        invariant_status=inv_status,
    )

    report = chain.verify_integrity(raw_input_bytes=raw_payload)
    assert report["verified"] is True
    assert report["stage_1_valid"] is True
    assert report["nodes_valid"] is True
    assert report["merkle_root_valid"] is True
    assert report["invariants_valid"] is True

    # Tampered raw bytes should fail stage 1 verification
    tampered_report = chain.verify_integrity(raw_input_bytes=b"Modified_Raw_Bytes")
    assert tampered_report["verified"] is False
    assert tampered_report["stage_1_valid"] is False


def test_audit_ledger_database_persistence_and_query_isolation():
    """Verify database storage, retrieval, and tenant isolation of AuditLedgerEntry."""
    init_database()
    tenant_a = f"tenant-audit-{uuid.uuid4()}"
    tenant_b = f"tenant-audit-{uuid.uuid4()}"
    job_id = f"job-audit-{uuid.uuid4()}"
    user_id = f"user-{uuid.uuid4()}"

    with database.SessionLocal() as session:
        # Create user and job
        user = User(id=user_id, email=f"audit_{uuid.uuid4()}@enterprise.com", org_id=tenant_a)
        session.add(user)
        job = Job(id=job_id, tenant_id=tenant_a, user_id=user_id, kind="live_scrape", workspace_path="/tmp")
        session.add(job)

        # Create audit entry
        entry = AuditLedgerEntry(
            job_id=job_id,
            tenant_id=tenant_a,
            merkle_root_sha256="c" * 64,
            stage_1_raw_input_sha256="1" * 64,
            stage_2_coa_mapping_sha256="2" * 64,
            stage_3_model_solve_sha256="3" * 64,
            lineage_manifest_json=json.dumps({"lineage_nodes": [], "invariant_status": {"all_passed": True}}),
        )
        session.add(entry)
        session.commit()

        # Query by tenant_a succeeds
        retrieved_a = get_audit_ledger_entry(session, job_id, tenant_id=tenant_a)
        assert retrieved_a is not None
        assert retrieved_a.merkle_root_sha256 == "c" * 64

        # Query by tenant_b returns None (Strict row isolation)
        retrieved_b = get_audit_ledger_entry(session, job_id, tenant_id=tenant_b)
        assert retrieved_b is None

        # Global lookup by hash succeeds
        match_entry = find_audit_entry_by_hash(session, "c" * 64)
        assert match_entry is not None
        assert match_entry.job_id == job_id


def test_public_audit_verification_endpoints():
    """Verify GET /api/v1/audit/verify/{job_id} and POST /api/v1/audit/verify-hash."""
    init_database()
    client = TestClient(app)

    job_id = f"job-verify-{uuid.uuid4()}"
    tenant_id = f"tenant-verify-{uuid.uuid4()}"
    user_id = f"user-{uuid.uuid4()}"
    test_merkle_root = hashlib.sha256(b"unique_merkle_root_12345").hexdigest()
    test_stage_1 = hashlib.sha256(b"unique_stage_1_raw_bytes").hexdigest()

    with database.SessionLocal() as session:
        user = User(id=user_id, email=f"verify_{uuid.uuid4()}@firm.com", org_id=tenant_id)
        session.add(user)
        job = Job(id=job_id, tenant_id=tenant_id, user_id=user_id, kind="valuation", workspace_path="/tmp")
        session.add(job)

        entry = AuditLedgerEntry(
            job_id=job_id,
            tenant_id=tenant_id,
            merkle_root_sha256=test_merkle_root,
            stage_1_raw_input_sha256=test_stage_1,
            stage_2_coa_mapping_sha256="e" * 64,
            stage_3_model_solve_sha256="f" * 64,
            lineage_manifest_json=json.dumps({
                "lineage_nodes": [{"metric": "Revenue", "value": 1000.0}],
                "invariant_status": {"all_passed": True, "overall_status": "PASSED", "max_discrepancy": 0.0},
            }),
        )
        session.add(entry)
        session.commit()

    # 1. Verify by job_id
    res_job = client.get(f"/api/v1/audit/verify/{job_id}")
    assert res_job.status_code == 200
    data_job = res_job.json()
    assert data_job["verified"] is True
    assert data_job["merkle_root_sha256"] == test_merkle_root
    assert data_job["provenance_stages"]["stage_1_raw_input_sha256"] == test_stage_1

    # 2. Verify by hash (Merkle root match)
    res_hash = client.post("/api/v1/audit/verify-hash", json={"hash": test_merkle_root})
    assert res_hash.status_code == 200
    data_hash = res_hash.json()
    assert data_hash["verified"] is True
    assert data_hash["job_id"] == job_id
    assert data_hash["match_type"] == "merkle_root"

    # 3. Verify by hash (Raw input stage 1 match)
    res_stage1 = client.post("/api/v1/audit/verify-hash", json={"hash": test_stage_1})
    assert res_stage1.status_code == 200
    data_stage1 = res_stage1.json()
    assert data_stage1["verified"] is True
    assert data_stage1["match_type"] == "raw_input"

    # 4. Unknown hash returns verified: False
    res_unknown = client.post("/api/v1/audit/verify-hash", json={"hash": "0" * 64})
    assert res_unknown.status_code == 200
    assert res_unknown.json()["verified"] is False


def test_excel_deliverable_provenance_tab_embedding():
    """Verify that workbook compilation creates the 09_Audit_&_Lineage_Ledger tab with keywords."""
    wb = openpyxl.Workbook()
    engine_output = {
        "Base": {
            "dcf": {"enterprise_value": 4500.0, "equity_value": 4000.0, "fair_value_per_share": 120.0},
        }
    }
    meta = {"name": "Audit Corp", "standard": "US_GAAP", "ticker": "ACRP"}

    merkle_root = build_audit_ledger(wb, engine_output, metadata=meta)
    assert len(merkle_root) == 64
    assert "09_Audit_&_Lineage_Ledger" in wb.sheetnames

    ws = wb["09_Audit_&_Lineage_Ledger"]
    assert "CRYPTOGRAPHIC SHA-256 AUDIT & LINEAGE LEDGER" in ws["A1"].value
    assert ws["B5"].value == merkle_root
    assert "MerkleRoot:" in wb.properties.keywords


def test_opentelemetry_observability_and_schema_drift():
    """Verify OTel telemetry hooks, SLA monitoring, and upstream schema drift detector."""
    # 1. Tracing span and metric recording should execute cleanly with zero errors
    with trace_span("test.execution", {"test_key": "val"}):
        record_scraper_latency(145.2, {"source": "sec_edgar"})
        record_pipeline_duration(320.5, success=True)
        record_schema_drift("SEC_EDGAR_XBRL", "us-gaap:Depreciation", "Tag deprecated by regulator")
        record_invariant_discrepancy("JOB-TEST", 0.0, "Balance Sheet Equilibrium")

    # 2. SLA Tracker summary
    summary = sla_tracker.get_summary()
    assert summary["sla_target_availability"] == "99.9%"
    assert summary["total_pipeline_runs"] >= 1
    assert summary["avg_scraper_latency_ms"] > 0
    assert summary["total_schema_drifts_detected"] >= 1

    # 3. Upstream Schema Drift Detection
    # When all required tags are present, missing list is empty
    available_tags_full = [
        "Total Revenue", "Operating Income", "Total Assets",
        "Total Liabilities", "Stockholders Equity", "Operating Cash Flow"
    ]
    missing_none = detect_schema_drift(available_tags_full, source_system="SEC_EDGAR")
    assert len(missing_none) == 0

    # When mandatory tags are missing, drift counter increments and missing list returned
    available_tags_partial = ["Total Revenue", "Total Assets"]
    missing_items = detect_schema_drift(available_tags_partial, source_system="Screener.in")
    assert len(missing_items) > 0
    assert "operating_income" in missing_items
    assert "total_liabilities" in missing_items

    # 4. GET /api/v1/health/sla endpoint check
    client = TestClient(app)
    res_sla = client.get("/api/v1/health/sla")
    assert res_sla.status_code == 200
    sla_data = res_sla.json()
    assert "current_availability_pct" in sla_data
    assert "total_schema_drifts_detected" in sla_data
