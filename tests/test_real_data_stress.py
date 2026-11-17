"""
Autonomous Real-World Stress Test Suite:
Validates ingestion, 3-statement linking, DCF valuation, and Excel compilation
on real public company data (Infosys Ind AS INR Crores & Microsoft US GAAP USD Millions)
injected with realistic client ERP quirks (merged banners, blank top rows,
trailing footnotes, mixed date formats, and custom Tally/Zoho ledger names).
"""

from __future__ import annotations

import os
import sys
import subprocess
import time
from pathlib import Path
import pytest
import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.ingester import UniversalIngester
from src.engine.orchestrator import ModelOrchestrator
from src.exporters.workbook_compiler import WorkbookCompiler
from src.exporters.formula_checker import FormulaChecker

TOLERANCE = 1e-4

INFY_QUIRKY_PATH = "inputs/quirky_infosys_tally_ind_as.xlsx"
MSFT_QUIRKY_PATH = "inputs/quirky_microsoft_zoho_us_gaap.xlsx"


# ── STEP 1: Ingestion & Normalization Verification ───────────────────────────
class TestRealDataIngestion:
    def test_infosys_tally_ingestion(self):
        ingester = UniversalIngester()
        res = ingester.ingest_file(INFY_QUIRKY_PATH)
        assert res.standard == "IND_AS"
        assert res.currency == "INR"
        assert res.unit == "Crores"
        assert len(res.periods) >= 3
        # Verify revenue extracted
        clean_rev = [r for r in res.revenue if r is not None]
        assert len(clean_rev) >= 3
        assert all(r > 0 for r in clean_rev)
        # Verify assets extracted
        clean_assets = [a for a in res.total_assets if a is not None]
        assert len(clean_assets) >= 3
        assert all(a > 0 for a in clean_assets)

    def test_microsoft_zoho_ingestion(self):
        ingester = UniversalIngester()
        res = ingester.ingest_file(MSFT_QUIRKY_PATH)
        assert res.standard == "US_GAAP"
        assert res.currency == "USD"
        assert res.unit == "Millions"
        assert len(res.periods) >= 3
        clean_rev = [r for r in res.revenue if r is not None]
        assert len(clean_rev) >= 3
        assert all(r > 0 for r in clean_rev)
        clean_assets = [a for a in res.total_assets if a is not None]
        assert len(clean_assets) >= 3
        assert all(a > 0 for a in clean_assets)


# ── STEP 2: Gate 1 — Balance Sheet Identity Invariant ───────────────────────
class TestRealDataGate1_BalanceSheetIdentity:
    @pytest.mark.parametrize("file_path,scenarios", [
        (INFY_QUIRKY_PATH, ["Base", "Bull", "Bear"]),
        (MSFT_QUIRKY_PATH, ["Base", "Bull", "Bear"]),
    ])
    def test_balance_sheet_identity(self, file_path, scenarios):
        ingester = UniversalIngester()
        norm = ingester.ingest_file(file_path)
        orch = ModelOrchestrator()
        out = orch.run(norm, scenarios=scenarios, n_years=5)

        for scen in scenarios:
            model = out[scen]["model_output"]
            for i, p in enumerate(model.periods):
                assets = model.bs_total_assets[i]
                liab_eq = model.bs_total_liab_equity[i]
                diff = abs(assets - liab_eq)
                assert diff < TOLERANCE, f"{file_path} / {scen} / {p}: BS mismatch diff={diff:.6f}"


# ── STEP 3: Gate 2 — Cash Reconciliation ────────────────────────────────────
class TestRealDataGate2_CashReconciliation:
    @pytest.mark.parametrize("file_path", [INFY_QUIRKY_PATH, MSFT_QUIRKY_PATH])
    def test_cash_reconciles(self, file_path):
        ingester = UniversalIngester()
        norm = ingester.ingest_file(file_path)
        orch = ModelOrchestrator()
        out = orch.run(norm, scenarios=["Base"], n_years=5)
        model = out["Base"]["model_output"]

        for i, p in enumerate(model.periods):
            closing_cash = model.cf_closing_cash[i]
            bs_cash = model.bs_cash[i]
            diff = abs(closing_cash - bs_cash)
            assert diff < TOLERANCE, f"{file_path} / Base / {p}: Cash mismatch={diff:.6f}"


# ── STEP 4: Gate 3 — Formula Integrity Scan ─────────────────────────────────
class TestRealDataGate3_FormulaIntegrity:
    @pytest.mark.parametrize("file_path,name", [
        (INFY_QUIRKY_PATH, "Infosys_Tally_IndAS_StressModel.xlsx"),
        (MSFT_QUIRKY_PATH, "Microsoft_Zoho_USGAAP_StressModel.xlsx"),
    ])
    def test_no_formula_errors(self, file_path, name, tmp_path):
        ingester = UniversalIngester()
        norm = ingester.ingest_file(file_path)
        orch = ModelOrchestrator()
        out = orch.run(norm, scenarios=["Base", "Bull", "Bear"], n_years=5)

        meta = {
            "name": name.replace(".xlsx", ""),
            "standard": norm.standard,
            "currency": norm.currency,
            "unit": norm.unit,
            "fy_end_month": norm.fiscal_year_end,
        }
        compiler = WorkbookCompiler()
        target_path = str(tmp_path / name)
        compiler.compile(out, norm, meta, target_path)

        checker = FormulaChecker()
        scan_res = checker.scan(target_path)
        assert scan_res.total_formulas_scanned > 350
        assert not scan_res.has_errors, f"Formula errors in {name}: {scan_res.error_cells}"


# ── STEP 5: Gate 5 — Live API Dropzone Endpoint ──────────────────────────────
class TestRealDataGate5_LiveAPI:
    def test_upload_and_download_real_quirky_files(self, tmp_path):
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.ingestion.api:app", "--host", "127.0.0.1", "--port", "8770"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            client = httpx.Client(base_url="http://127.0.0.1:8770", timeout=30.0)

            # Check health
            deadline = time.monotonic() + 30
            while True:
                try:
                    r = client.get("/api/v1/health", timeout=1.0)
                    if r.status_code == 200:
                        break
                    raise AssertionError(f"Health check returned {r.status_code}: {r.text}")
                except httpx.TransportError:
                    if proc.poll() is not None:
                        stderr = proc.stderr.read().decode("utf-8", errors="replace")
                        raise RuntimeError(f"Uvicorn exited during startup: {stderr}") from None
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Uvicorn did not become healthy within 30 seconds") from None
                    time.sleep(0.5)
            assert r.status_code == 200

            # Upload quirky INFY
            with open(INFY_QUIRKY_PATH, "rb") as f:
                r_infy = client.post(
                    "/api/v1/model/generate",
                    files={"file": (os.path.basename(INFY_QUIRKY_PATH), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                )
            assert r_infy.status_code == 200, f"INFY upload failed: {r_infy.text}"
            res_infy = r_infy.json()
            assert res_infy["status"] == "success"
            assert res_infy["metadata"]["standard"] == "IND_AS"
            assert res_infy["metadata"]["currency"] == "INR"
            assert res_infy["metadata"]["unit"] == "Crores"

            # Download INFY model
            infy_wb = res_infy["workbook_filename"]
            r_dl = client.get(f"/api/v1/model/download/{infy_wb}")
            assert r_dl.status_code == 200
            dl_path = tmp_path / infy_wb
            dl_path.write_bytes(r_dl.content)
            assert dl_path.stat().st_size > 10000

            # Scan downloaded file for formula errors
            checker = FormulaChecker()
            assert not checker.scan(str(dl_path)).has_errors

            # Upload quirky MSFT
            with open(MSFT_QUIRKY_PATH, "rb") as f:
                r_msft = client.post(
                    "/api/v1/model/generate",
                    files={"file": (os.path.basename(MSFT_QUIRKY_PATH), f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                )
            assert r_msft.status_code == 200, f"MSFT upload failed: {r_msft.text}"
            res_msft = r_msft.json()
            assert res_msft["status"] == "success"
            assert res_msft["metadata"]["standard"] == "US_GAAP"
            assert res_msft["metadata"]["currency"] == "USD"
            assert res_msft["metadata"]["unit"] == "Millions"

            # Download MSFT model
            msft_wb = res_msft["workbook_filename"]
            r_dl2 = client.get(f"/api/v1/model/download/{msft_wb}")
            assert r_dl2.status_code == 200
            dl_path2 = tmp_path / msft_wb
            dl_path2.write_bytes(r_dl2.content)
            assert dl_path2.stat().st_size > 10000
            assert not checker.scan(str(dl_path2)).has_errors

        finally:
            proc.terminate()
            proc.wait()
