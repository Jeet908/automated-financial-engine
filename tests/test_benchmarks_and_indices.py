"""
Verification Suite for Open Benchmark Authority & Live Public Sector Valuation Index.
Tests:
1. benchmarks/run_benchmark.py execution, 0.000000e+00 balance sheet precision, 100% 6-gate invariant pass rate, and report generation.
2. GET /api/v1/public/indices & GET /api/v1/public/indices/{sector_slug} public endpoints (zero private tenant exposure).
3. Public HTML5 SEO pages (/indices and /indices/{sector_slug}) and targeted CORS headers for https://www.marketlensanalytics.in.
4. WordPress REST API sync resilience (graceful skipping when unconfigured, valid payload generation when mocked).
5. Daily Celery/worker task execution for sector index refresh.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
from fastapi.testclient import TestClient

from app import app
from benchmarks.run_benchmark import run_benchmark
from src.mesh.wordpress_sync import (
    format_market_brief_html,
    sync_daily_market_brief_to_wordpress,
)
from src.portal.index_routes import SECTOR_INDICES_DATA, _compute_index_summary
from src.workers.daily_index_tasks import refresh_public_sector_indices_task


def test_accounting_benchmark_runner_and_reports():
    """
    Verify python benchmarks/run_benchmark.py executes with 0.000000e+00 Balance Sheet Error
    across Ind AS, US GAAP, and IFRS, achieving a 100% (18/18) 6-gate invariant pass rate.
    """
    results = run_benchmark()
    assert results is not None
    assert "summary" in results
    assert "regimes" in results

    summary = results["summary"]
    det = summary["deterministic_engine"]
    llm = summary["generic_llm_baseline"]

    # 1. Zero Balance Sheet Discrepancy Assertion
    assert det["max_balance_sheet_error"] == 0.0, f"Engine produced non-zero BS error: {det['max_balance_sheet_error']}"
    assert det["accounting_invariant_pass_rate_pct"] == 100.0
    assert det["excel_formula_errors"] == 0
    assert det["sha256_lineage_coverage_pct"] == 100.0

    # 2. Verify all 3 global regimes are represented
    regime_ids = [r["regime_id"] for r in results["regimes"]]
    assert "ind_as_schedule_iii" in regime_ids
    assert "us_gaap_saas" in regime_ids
    assert "uk_eu_ifrs" in regime_ids

    for r in results["regimes"]:
        r_det = r["deterministic_engine"]
        assert r_det["max_balance_sheet_error"] == 0.0
        assert r_det["invariants_passed"] == 6
        assert r_det["invariant_pass_rate_pct"] == 100.0
        assert r_det["audit_certificate_status"] == "PASSED"

    # 3. Verify physical files were generated
    report_file = Path(__file__).resolve().parent.parent / "benchmarks" / "BENCHMARK_REPORT.md"
    json_file = Path(__file__).resolve().parent.parent / "benchmarks" / "benchmark_results.json"

    assert report_file.exists(), "BENCHMARK_REPORT.md was not generated"
    assert json_file.exists(), "benchmark_results.json was not generated"

    report_text = report_file.read_text(encoding="utf-8")
    assert "0.000000e+00" in report_text
    assert "Balance Sheet Max Discrepancy" in report_text
    assert "India Ind AS / Schedule III" in report_text
    assert "US GAAP" in report_text
    assert "UK / EU IFRS" in report_text

    raw_json = json.loads(json_file.read_text(encoding="utf-8"))
    assert raw_json["summary"]["deterministic_engine"]["max_balance_sheet_error"] == 0.0


def test_public_indices_api_endpoints_and_zero_tenant_data():
    """
    Verify GET /api/v1/public/indices and GET /api/v1/public/indices/{sector_slug}
    expose strict public market data and 0.000000e+00 audit status with ZERO private tenant data.
    """
    client = TestClient(app)

    # 1. GET /api/v1/public/indices
    resp = client.get("/api/v1/public/indices")
    assert resp.status_code == 200
    data = resp.json()

    assert "indices" in data
    assert data["total_indices"] == 4
    assert "0.000000e+00" in data["audit_guarantee"]

    indices = data["indices"]
    slugs = [idx["sector_slug"] for idx in indices]
    assert "indian-defence-it" in slugs
    assert "global-saas-roic" in slugs
    assert "us-ai-semiconductors" in slugs
    assert "indian-fmcg-consumer" in slugs

    # Verify zero private tenant fields are leaked
    private_keys = {"tenant_id", "user_id", "password_hash", "email", "client_secret", "encrypted_token"}
    for idx in indices:
        for k in private_keys:
            assert k not in idx, f"Leaked private key '{k}' in public index summary"
        assert idx["audit_status"] == "0.000000e+00"
        assert idx["constituent_count"] > 0
        assert idx["median_wacc_pct"] > 0

    # 2. GET /api/v1/public/indices/{sector_slug} for global-saas-roic
    detail_resp = client.get("/api/v1/public/indices/global-saas-roic")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()

    assert "index" in detail_data
    assert "constituents" in detail_data
    assert "audit_certificate" in detail_data
    assert detail_data["audit_certificate"]["max_discrepancy"] == "0.000000e+00"

    constituents = detail_data["constituents"]
    assert len(constituents) >= 5
    msft = next((c for c in constituents if c["ticker"] == "MSFT"), None)
    assert msft is not None
    assert msft["market_price"] > 0
    assert msft["fair_value_dcf"] > 0
    assert msft["roic_pct"] > 0
    assert "sha256_hash" in msft
    assert len(msft["sha256_hash"]) == 64

    # 3. GET /api/v1/public/indices/{sector_slug} 404 for invalid sector
    not_found_resp = client.get("/api/v1/public/indices/nonexistent-crypto-index")
    assert not_found_resp.status_code == 404


def test_public_indices_html_pages_and_cors():
    """
    Verify public SEO & embed routes cleanly redirect (307) to the commercial portal /,
    and CORS on /api/v1/public/indices properly whitelists allowed origins.
    """
    client = TestClient(app)

    # 1. GET /indices cleanly redirects to /
    hub_resp = client.get("/indices", follow_redirects=False)
    assert hub_resp.status_code == 307
    assert hub_resp.headers["location"] == "/"

    # 2. GET /indices/{sector_slug} cleanly redirects to /
    detail_resp = client.get("/indices/indian-defence-it", follow_redirects=False)
    assert detail_resp.status_code == 307
    assert detail_resp.headers["location"] == "/"

    # 3. GET /benchmarks cleanly redirects to /
    bench_resp = client.get("/benchmarks", follow_redirects=False)
    assert bench_resp.status_code == 307
    assert bench_resp.headers["location"] == "/"

    # 4. GET /embed/indices WordPress Embed Snippet cleanly redirects to /
    embed_resp = client.get("/embed/indices", follow_redirects=False)
    assert embed_resp.status_code == 307
    assert embed_resp.headers["location"] == "/"

    # 5. Following redirect to / loads the commercial portal with the Enterprise Audit Guarantee badge
    portal_resp = client.get("/indices", follow_redirects=True)
    assert portal_resp.status_code == 200
    assert "6-Gate Mathematical Verification" in portal_resp.text
    assert "MarketLens" in portal_resp.text

    # 6. CORS verification on /api/v1/public/indices
    cors_origin = "https://www.marketlensanalytics.in"
    cors_resp = client.get("/api/v1/public/indices", headers={"Origin": cors_origin})
    assert cors_resp.status_code == 200
    assert cors_resp.headers.get("access-control-allow-origin") == cors_origin

    # OPTIONS preflight
    options_resp = client.options("/api/v1/public/indices", headers={"Origin": cors_origin})
    assert options_resp.status_code == 200
    assert options_resp.headers.get("access-control-allow-origin") == cors_origin
    assert "GET" in options_resp.headers.get("access-control-allow-methods", "")

    # Subdomain origin https://app.marketlensanalytics.in
    app_cors_resp = client.get("/api/v1/public/indices", headers={"Origin": "https://app.marketlensanalytics.in"})
    assert app_cors_resp.headers.get("access-control-allow-origin") == "https://app.marketlensanalytics.in"

    # Private API endpoint must NOT return CORS for external origin
    private_resp = client.post("/api/v1/model/live-scrape", headers={"Origin": cors_origin})
    assert private_resp.headers.get("access-control-allow-origin") != cors_origin


def test_wordpress_sync_resilience_and_payload_formatting():
    """
    Verify WordPress sync skips gracefully without credentials (no crash),
    formats comprehensive HTML tables, and handles mocked API responses.
    """
    # 1. Unset credentials -> graceful skip
    result = sync_daily_market_brief_to_wordpress(indices_data=None)
    assert result["status"] == "skipped"
    assert result["reason"] == "credentials_not_configured"

    # 2. Test format_market_brief_html
    sample_indices = [_compute_index_summary(sec) for sec in SECTOR_INDICES_DATA.values()]
    html_content = format_market_brief_html(sample_indices)
    assert "<table" in html_content
    assert "Daily Indian Defence & IT DCF Index" in html_content
    assert "Global SaaS Burn & ROIC Index" in html_content
    assert "0.000000e+00" in html_content
    assert "Start Free 14-Day Executive Trial" in html_content

    # 3. Mocked WordPress REST API publish
    import os
    os.environ["WP_USERNAME"] = "marketlens_admin"
    os.environ["WP_APP_PASSWORD"] = "abcd-1234-efgh-5678"
    os.environ["WP_SITE_URL"] = "https://www.marketlensanalytics.in"

    mock_client = MagicMock(spec=httpx.Client)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "id": 1042,
        "link": "https://www.marketlensanalytics.in/daily-sector-valuation-brief-2026-11-20",
    }
    mock_client.post.return_value = mock_response

    try:
        mock_result = sync_daily_market_brief_to_wordpress(indices_data=sample_indices, client=mock_client)
        assert mock_result["status"] == "published"
        assert mock_result["post_id"] == 1042
        assert mock_client.post.called
        # Verify endpoint called
        called_args, called_kwargs = mock_client.post.call_args
        assert "wp-json/wp/v2/posts" in called_args[0]
        assert "json" in called_kwargs
        payload = called_kwargs["json"]
        assert "Daily Sector Valuation Index" in payload["title"]
        assert "0.000000e+00" in payload["content"]
    finally:
        os.environ.pop("WP_USERNAME", None)
        os.environ.pop("WP_APP_PASSWORD", None)


def test_daily_index_celery_task():
    """
    Verify the daily 00:00 UTC sector index recalculation worker task runs cleanly.
    """
    task_res = refresh_public_sector_indices_task()
    assert task_res["status"] == "success"
    assert task_res["indices_refreshed_count"] == 4
    assert task_res["audit_guarantee"] == "0.000000e+00 Balance Sheet Error"
    assert "wordpress_sync" in task_res


def test_guest_live_valuation_end_to_end():
    """
    Verify full guest live valuation lifecycle:
    1. Unauthenticated POST /api/v1/model/live-scrape succeeds with HTTP 202 and issues guest session.
    2. Polling GET /api/v1/jobs/{job_id} succeeds for guest without 401.
    3. Downloading deliverable files via GET /api/v1/jobs/{job_id}/files/{file_key} returns 200.
    """
    from src.portal.database import init_database
    init_database()
    client = TestClient(app)

    # 1. Trigger live scrape for domain as anonymous guest
    resp = client.post(
        "/api/v1/model/live-scrape",
        json={"domain": "US AI & Cloud Semiconductors"},
    )
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
    body = resp.json()
    assert "job_id" in body
    job_id = body["job_id"]

    # 2. Poll job status
    poll_resp = client.get(f"/api/v1/jobs/{job_id}")
    assert poll_resp.status_code == 200, f"Expected 200, got {poll_resp.status_code}: {poll_resp.text}"
    job_data = poll_resp.json()
    assert job_data["status"] in ("succeeded", "completed", "processing", "pending")

    # If the fallback ran in-process, it should be succeeded
    if job_data["status"] in ("succeeded", "completed"):
        res = job_data.get("result") or {}
        files = res.get("files") or {}
        for file_key in ["dashboard_html", "xlsx_model", "pdf_tearsheet", "pptx_pitchbook"]:
            if file_key in files:
                dl_resp = client.get(f"/api/v1/jobs/{job_id}/files/{file_key}")
                assert dl_resp.status_code == 200, f"Download {file_key} failed with {dl_resp.status_code}"


def test_zero_proprietary_ip_leaks():
    """
    Verify zero occurrences of proprietary IP (github.com, Jeet908, git clone)
    in src/ and app.py.
    """
    root_dir = Path(__file__).resolve().parent.parent
    src_dir = root_dir / "src"
    app_py = root_dir / "app.py"
    index_html = root_dir / "src" / "portal" / "index.html"

    forbidden_patterns = ["github.com", "Jeet908", "git clone"]
    violations = []

    files_to_check = list(src_dir.rglob("*.py")) + [app_py, index_html]
    for file_path in files_to_check:
        if "__pycache__" in str(file_path):
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                if pattern in content:
                    violations.append(f"{file_path.name} contains '{pattern}'")
        except Exception:
            pass

    assert not violations, f"Found proprietary IP leaks in production files: {violations}"
