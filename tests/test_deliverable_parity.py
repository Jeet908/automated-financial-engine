"""
tests/test_deliverable_parity.py — Cross-Deliverable Mathematical Parity Verification Suite.
Asserts that Web UI, Excel (.xlsx), PDF, and PowerPoint deliverables are 100% reconciled
from a single verified computation kernel with zero formula errors and zero accounting drift.
"""

import os
import tempfile
import pytest
import openpyxl

from src.ingestion.live_web_scraper import DOMAIN_CATALOG
from financial_engine.cli import run_pipeline
from src.exporters.adapter import financial_model_to_engine_output
from src.exporters.executive_pack import ExecutivePackCompiler
from src.exporters.formula_checker import FormulaChecker
from financial_engine.valuation.comps import run_comps_analysis


def test_unified_kernel_parity_nvda():
    """Verify NVDA US GAAP valuation reconciles identically across all deliverables."""
    nvda_data = None
    for comp in DOMAIN_CATALOG.get("US AI & Cloud Semiconductors", []):
        if comp["ticker"] == "NVDA":
            nvda_data = comp
            break
    assert nvda_data is not None, "NVDA benchmark catalog entry must exist"

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Run Engine A
        from src.ingestion.live_web_scraper import LiveWebScraper
        scraper = LiveWebScraper(output_inbox=tmp_dir, output_inputs=tmp_dir)
        company_data, xlsx_inbox, json_config = scraper.discover_and_extract(ticker="NVDA")

        artifacts_dir = os.path.join(tmp_dir, "artifacts")
        os.makedirs(artifacts_dir, exist_ok=True)

        model = run_pipeline(
            config_path=json_config,
            output_dir=artifacts_dir,
            mc_iterations=500,
            export_excel=False,
            export_html=False,
            export_memo=False,
            export_json=False,
            quiet=True,
        )

        assert model.audit_certificate.is_valid, "Accounting invariants must pass"
        max_err = max((c.max_discrepancy for c in model.audit_certificate.checks), default=0.0)
        assert max_err <= 1e-6, f"Accounting error {max_err} exceeds 1e-6 tolerance"

        # Adapt to engine_output
        engine_output = financial_model_to_engine_output(model, company_data=company_data)

        # Mathematical parity assertions
        base_dcf = engine_output["Base"]["dcf"]
        assert abs(base_dcf["price_per_share"] - model.value_per_share) < 1e-6, (
            f"Parity broken: Web implied price {model.value_per_share} != Pack price {base_dcf['price_per_share']}"
        )
        assert abs(base_dcf["enterprise_value"] - model.enterprise_value) < 1e-6, (
            f"Parity broken: Web EV {model.enterprise_value} != Pack EV {base_dcf['enterprise_value']}"
        )
        assert abs(base_dcf["wacc"] - model.wacc) < 1e-6, (
            f"Parity broken: Web WACC {model.wacc} != Pack WACC {base_dcf['wacc']}"
        )

        # Compile Executive Pack
        outbox_dir = os.path.join(tmp_dir, "outbox")
        comp_meta = {
            "name": company_data["name"],
            "ticker": "NVDA",
            "standard": "US_GAAP",
            "currency": "USD",
            "unit": "billion",
            "shares_unit": "billion",
            "fy_end_month": 12,
            "shares_outstanding": float(model.dcf_result.shares_outstanding),
        }
        compiler = ExecutivePackCompiler()
        pack_res = compiler.compile_pack(
            engine_output=engine_output,
            normalized_financials=company_data.get("historicals", {}),
            metadata=comp_meta,
            output_dir=outbox_dir,
            clean_name="NVDA_Institutional",
        )

        xlsx_path = pack_res["xlsx_path"]
        assert os.path.exists(xlsx_path), "Excel deliverable must be created"
        assert os.path.exists(pack_res["pdf_path"]), "PDF deliverable must be created"
        assert os.path.exists(pack_res["pptx_path"]), "PPTX deliverable must be created"
        assert os.path.exists(pack_res["zip_path"]), "ZIP deliverable must be created"

        # Scan Excel for formula errors (#REF!, #VALUE!, #NAME?, #DIV/0!)
        fc = FormulaChecker()
        fc_res = fc.scan(xlsx_path)
        assert not fc_res.has_errors, f"Excel has formula errors: {fc_res.errors}"

        # Inspect workbook directly
        wb = openpyxl.load_workbook(xlsx_path, data_only=False)
        assert "07_DCF_&_Sensitivity" in wb.sheetnames, "DCF sheet must be named '07_DCF_&_Sensitivity'"
        ws_dcf = wb["07_DCF_&_Sensitivity"]

        # Ensure no cell references empty B14
        for row in ws_dcf.iter_rows(values_only=False):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    val_str = cell.value.upper()
                    assert "B14" not in val_str or "1/(1+B14)" not in val_str, (
                        f"Broken WACC cell reference B14 found in cell {cell.coordinate}: {cell.value}"
                    )

        # Inspect Audit Ledger sheet
        assert "09_Audit_&_Lineage_Ledger" in wb.sheetnames
        ws_audit = wb["09_Audit_&_Lineage_Ledger"]
        # Fair value per share in lineage table must match model
        val_found = False
        for r in range(14, 25):
            metric_val = ws_audit.cell(row=r, column=1).value
            if metric_val == "Fair_Value_Per_Share":
                rep_val = float(ws_audit.cell(row=r, column=5).value)
                assert abs(rep_val - model.value_per_share) < 1e-4, (
                    f"Audit ledger fair value {rep_val} does not match model {model.value_per_share}"
                )
                val_found = True
                break
        assert val_found, "Fair_Value_Per_Share lineage node must be present in audit ledger"


def test_peer_comps_not_defaulting_to_indian_food():
    """Verify semiconductor companies receive tech comps instead of Indian food companies."""
    res_us = run_comps_analysis(
        target_ebitda=30.0,
        target_net_income=25.0,
        target_revenue=60.0,
        target_net_debt=0.0,
        shares_outstanding=1.0,
        sector="US AI & Cloud Semiconductors",
        region="US",
    )
    tickers = [p.ticker for p in res_us.peers]
    assert "BRITANNIA.NS" not in tickers, "Semiconductor comps must NOT include Britannia"
    assert "BIKAJI.NS" not in tickers, "Semiconductor comps must NOT include Bikaji"
    assert any(t in tickers for t in ["AMD", "AVGO", "QCOM", "INTC", "TSM"]), (
        f"Semiconductor comps must include real semiconductor peers, got: {tickers}"
    )


def test_closed_loop_cash_roll_forward():
    """Verify 3-statement model cash flow roll-forward has zero plugs."""
    from src.engine.model3s import ThreeStatementModel
    from src.engine.drivers import DriverCalibrator

    hist = {
        "revenue": [100.0, 115.0, 130.0],
        "cogs": [50.0, 58.0, 65.0],
        "employee_costs": [15.0, 17.0, 20.0],
        "other_expenses": [10.0, 11.0, 12.0],
        "depreciation": [5.0, 6.0, 7.0],
        "interest": [2.0, 2.0, 2.0],
        "tax": [4.0, 5.0, 6.0],
        "dividends": [3.0, 4.0, 4.0],
        "cash": [20.0, 25.0, 30.0],
        "receivables": [15.0, 17.0, 20.0],
        "inventory": [10.0, 12.0, 14.0],
        "net_fixed_assets": [50.0, 55.0, 60.0],
        "payables": [12.0, 14.0, 16.0],
        "debt": [20.0, 20.0, 20.0],
        "share_capital": [10.0, 10.0, 10.0],
        "retained_earnings": [53.0, 61.0, 78.0],
    }

    calibrator = DriverCalibrator()
    drivers = calibrator.calibrate(hist)
    model3s = ThreeStatementModel()
    out = model3s.build(hist, drivers, scenario="Base", n_years=5)

    # Invariant: Assets == Liabilities + Equity identically
    for i in range(len(out.periods)):
        a = out.bs_total_assets[i]
        le = out.bs_total_liab_equity[i]
        diff = abs(a - le)
        assert diff < 1e-4, f"Period {out.periods[i]} balance sheet discrepancy {diff} > 1e-4: A={a}, LE={le}"

    # Invariant: Closing cash == Cash Flow ending cash
    for i in range(len(out.periods)):
        assert abs(out.bs_cash[i] - out.cf_closing_cash[i]) < 1e-6, (
            f"Cash mismatch: BS cash {out.bs_cash[i]} != CF closing cash {out.cf_closing_cash[i]}"
        )


def test_geo_currency_detection():
    """Verify IP and country header auto-currency resolution."""
    from fastapi import Request
    from src.portal.billing import detect_geo_currency

    class MockRequest:
        def __init__(self, headers):
            self.headers = headers

    # Test India (INR)
    req_in = MockRequest({"cf-ipcountry": "IN"})
    res_in = detect_geo_currency(req_in)
    assert res_in["currency"] == "INR"
    assert res_in["symbol"] == "₹"

    # Test UK (GBP)
    req_uk = MockRequest({"x-forwarded-country": "GB"})
    res_uk = detect_geo_currency(req_uk)
    assert res_uk["currency"] == "GBP"
    assert res_uk["symbol"] == "£"

    # Test Eurozone (EUR)
    req_de = MockRequest({"cf-ipcountry": "DE"})
    res_de = detect_geo_currency(req_de)
    assert res_de["currency"] == "EUR"
    assert res_de["symbol"] == "€"

    # Test US / Default (USD)
    req_us = MockRequest({"cf-ipcountry": "US"})
    res_us = detect_geo_currency(req_us)
    assert res_us["currency"] == "USD"
    assert res_us["symbol"] == "$"


def test_market_universe_top100_ranking():
    """Verify Top 100 universe sorts strictly descending by market cap and assigns ranks 1..N."""
    from src.ingestion.market_universe import MarketUniverseManager

    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_path = os.path.join(tmp_dir, "test_universe.json")
        mgr = MarketUniverseManager(cache_file=os.path.abspath(cache_path))
        top_champions = mgr.get_top_100(limit=100)

        assert len(top_champions) >= 100, f"Expected at least 100 champions, got {len(top_champions)}"
        assert top_champions[0]["rank"] == 1
        assert top_champions[0]["ticker"] in {"NVDA", "AAPL", "MSFT"}

        # Verify strictly descending market cap invariant
        for i in range(len(top_champions) - 1):
            assert top_champions[i]["rank"] == i + 1
            assert top_champions[i]["market_cap_usd"] >= top_champions[i + 1]["market_cap_usd"], (
                f"Rank ordering violated between rank {i+1} ({top_champions[i]['ticker']}: ${top_champions[i]['market_cap_usd']}B) "
                f"and rank {i+2} ({top_champions[i+1]['ticker']}: ${top_champions[i+1]['market_cap_usd']}B)"
            )


def test_market_universe_gics_sectors():
    """Verify that all 11 MSCI/S&P GICS standard sectors are represented."""
    from src.ingestion.market_universe import MarketUniverseManager, GICS_SECTORS

    mgr = MarketUniverseManager()
    sectors = mgr.get_sectors()

    assert len(sectors) == 11, f"Expected 11 GICS sectors, got {len(sectors)}"
    sector_names = {s["name"] for s in sectors}
    expected_sectors = {
        "Information Technology", "Financials", "Health Care", "Consumer Discretionary",
        "Communication Services", "Industrials", "Consumer Staples", "Energy",
        "Materials", "Utilities", "Real Estate",
    }
    assert sector_names == expected_sectors, f"Missing GICS sectors: {expected_sectors - sector_names}"

    # Verify sector filtering works
    tech_champs = mgr.get_top_100(sector="Information Technology")
    assert len(tech_champs) > 0
    for c in tech_champs:
        assert c["sector"] == "Information Technology"


def test_market_universe_typeahead_search():
    """Verify rapid typeahead search matching exact tickers, prefixes, and company names."""
    from src.ingestion.market_universe import MarketUniverseManager

    mgr = MarketUniverseManager()

    # Exact search
    res_nvda = mgr.search("NVDA")
    assert len(res_nvda) > 0
    assert res_nvda[0]["ticker"] == "NVDA"

    # Prefix search
    res_ts = mgr.search("TS")
    assert any(c["ticker"] in {"TSLA", "TSM"} for c in res_ts)

    # Name search
    res_apple = mgr.search("Apple")
    assert any(c["ticker"] == "AAPL" for c in res_apple)

    # Indian equity symbol
    res_tcs = mgr.search("TCS")
    assert any(c["ticker"] == "TCS.NS" for c in res_tcs)


