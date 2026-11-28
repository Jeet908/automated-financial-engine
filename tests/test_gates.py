import sys, json, math, os
sys.path.insert(0, "C:/Users/HP/Downloads/Finance")

import pytest

TOLERANCE = 1e-4

def load_fixture(name):
    path = f"C:/Users/HP/Downloads/Finance/tests/fixtures/{name}"
    with open(path) as f:
        return json.load(f)

# ── GATE 1: Balance Sheet Identity ──────────────────────────────────────────
class TestGate1_BalanceSheetIdentity:
    def _run_model(self, fixture_name, scenario):
        from src.engine.orchestrator import ModelOrchestrator
        from src.engine.model3s import ModelOutput
        data = load_fixture(fixture_name)
        orch = ModelOrchestrator()
        result = orch.run(data, scenarios=[scenario], n_years=5)
        return result[scenario]

    @pytest.mark.parametrize("fixture,scenario", [
        ("ind_as_fixture.json", "Base"),
        ("ind_as_fixture.json", "Bull"),
        ("ind_as_fixture.json", "Bear"),
        ("startup_fixture.json", "Base"),
        ("startup_fixture.json", "Bull"),
        ("startup_fixture.json", "Bear"),
        ("gaap_fixture.json", "Base"),
        ("gaap_fixture.json", "Bull"),
        ("gaap_fixture.json", "Bear"),
    ])
    def test_balance_sheet_balances(self, fixture, scenario):
        out = self._run_model(fixture, scenario)
        model = out["model_output"]
        for i, period in enumerate(model.periods):
            diff = abs(model.bs_total_assets[i] - model.bs_total_liab_equity[i])
            assert diff < TOLERANCE, f"{fixture}/{scenario}/{period}: BS imbalance={diff:.6f}"

# ── GATE 2: Cash & NI Reconciliation ────────────────────────────────────────
class TestGate2_CashReconciliation:
    @pytest.mark.parametrize("fixture,scenario", [
        ("ind_as_fixture.json", "Base"),
        ("startup_fixture.json", "Base"),
        ("gaap_fixture.json", "Base"),
    ])
    def test_cash_reconciles(self, fixture, scenario):
        from src.engine.orchestrator import ModelOrchestrator
        data = load_fixture(fixture)
        orch = ModelOrchestrator()
        result = orch.run(data, scenarios=[scenario], n_years=5)
        model = result[scenario]["model_output"]
        for i, period in enumerate(model.periods):
            cash_check = abs(model.cf_closing_cash[i] - model.bs_cash[i])
            assert cash_check < TOLERANCE, f"{fixture}/{scenario}/{period}: Cash mismatch={cash_check:.6f}"

# ── GATE 3: Zero Formula Errors in .xlsx ────────────────────────────────────
class TestGate3_FormulaErrors:
    def test_no_formula_errors(self, tmp_path):
        from src.engine.orchestrator import ModelOrchestrator
        from src.exporters.workbook_compiler import WorkbookCompiler
        from src.exporters.formula_checker import FormulaChecker
        import sys; sys.path.insert(0, "C:/Users/HP/Downloads/Finance")
        data = load_fixture("ind_as_fixture.json")
        orch = ModelOrchestrator()
        result = orch.run(data, scenarios=["Base","Bull","Bear"], n_years=5)
        output_path = str(tmp_path / "test_model.xlsx")
        compiler = WorkbookCompiler()
        compiler.compile(result, data, data.get("metadata",{}), output_path)
        checker = FormulaChecker()
        fc_result = checker.scan(output_path)
        assert not fc_result.has_errors, f"Formula errors found: {fc_result.error_cells}"

# ── GATE 4: Synthetic Stress Suite ──────────────────────────────────────────
class TestGate4_SyntheticStress:
    @pytest.mark.parametrize("fixture", [
        "ind_as_fixture.json",
        "startup_fixture.json",
        "gaap_fixture.json",
    ])
    def test_full_pipeline(self, fixture, tmp_path):
        from src.engine.orchestrator import ModelOrchestrator
        from src.exporters.workbook_compiler import WorkbookCompiler
        data = load_fixture(fixture)
        orch = ModelOrchestrator()
        result = orch.run(data, scenarios=["Base","Bull","Bear"], n_years=5)
        output_path = str(tmp_path / f"{fixture.replace('.json','')}_model.xlsx")
        compiler = WorkbookCompiler()
        saved = compiler.compile(result, data, data.get("metadata",{}), output_path)
        assert os.path.exists(saved), f"Output file not created: {saved}"
        assert os.path.getsize(saved) > 5000, f"Output file too small: {os.path.getsize(saved)} bytes"

# ── GATE 5: Live API ─────────────────────────────────────────────────────────
class TestGate5_LiveAPI:
    def test_api_full_e2e(self, tmp_path):
        import httpx, subprocess, time
        from src.exporters.formula_checker import FormulaChecker

        # Start FastAPI server on port 8765
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "src.ingestion.api:app", "--host", "127.0.0.1", "--port", "8765"],
            cwd="C:/Users/HP/Downloads/Finance",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        try:
            client = httpx.Client(base_url="http://127.0.0.1:8765", timeout=30.0)

            # 1. Health check
            deadline = time.monotonic() + 30
            while True:
                try:
                    r_health = client.get("/api/v1/health", timeout=1.0)
                    if r_health.status_code == 200:
                        break
                    raise AssertionError(f"Health check returned {r_health.status_code}: {r_health.text}")
                except httpx.TransportError:
                    if proc.poll() is not None:
                        stderr = proc.stderr.read().decode("utf-8", errors="replace")
                        raise RuntimeError(f"Uvicorn exited during startup: {stderr}") from None
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Uvicorn did not become healthy within 30 seconds") from None
                    time.sleep(0.5)
            assert r_health.status_code == 200
            assert r_health.json()["status"] == "ok"

            # 2. Web Dropzone UI check
            r_ui = client.get("/")
            assert r_ui.status_code == 200
            assert "Make the numbers easier to act on." in r_ui.text

            # 3. Upload all 3 fixtures via POST /api/v1/model/generate
            fixtures = ["ind_as_fixture.json", "startup_fixture.json", "gaap_fixture.json"]
            for fix in fixtures:
                fix_path = f"C:/Users/HP/Downloads/Finance/tests/fixtures/{fix}"
                with open(fix_path, "rb") as f:
                    r_upload = client.post(
                        "/api/v1/model/generate",
                        files={"file": (fix, f, "application/json")}
                    )
                assert r_upload.status_code == 200, f"Upload failed for {fix}: {r_upload.text}"
                res_json = r_upload.json()
                assert res_json["status"] == "success"
                assert res_json["formulas_scanned"] > 0
                assert len(res_json["formula_errors"]) == 0

                wb_filename = res_json["workbook_filename"]
                # 4. Download generated workbook via GET /api/v1/model/download/{filename}
                r_dl = client.get(f"/api/v1/model/download/{wb_filename}")
                assert r_dl.status_code == 200
                dl_target = tmp_path / wb_filename
                dl_target.write_bytes(r_dl.content)
                assert dl_target.stat().st_size > 5000, f"Downloaded workbook too small: {wb_filename}"

                # Formula integrity scan on downloaded file
                checker = FormulaChecker()
                scan_res = checker.scan(str(dl_target))
                assert not scan_res.has_errors, f"Formula errors in downloaded {wb_filename}: {scan_res.error_cells}"

        finally:
            proc.terminate()
            proc.wait()
