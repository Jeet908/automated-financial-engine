"""
Gate 6 — Cross-Deliverable Numerical Parity Test Suite.

Verifies end-to-end numerical parity, integrity, and deliverable completeness
across the synchronized 4-artifact pack (.xlsx, .pdf, .pptx, .zip) for:
  - tests/fixtures/ind_as_fixture.json
  - tests/fixtures/gaap_fixture.json
  - inputs/quirky_infosys_tally_ind_as.xlsx
  - inputs/quirky_microsoft_zoho_us_gaap.xlsx
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import openpyxl
import pytest

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cli import process_file
from src.exporters.formula_checker import FormulaChecker


TEST_INPUTS = [
    PROJECT_ROOT / "tests" / "fixtures" / "ind_as_fixture.json",
    PROJECT_ROOT / "tests" / "fixtures" / "gaap_fixture.json",
    PROJECT_ROOT / "inputs" / "quirky_infosys_tally_ind_as.xlsx",
    PROJECT_ROOT / "inputs" / "quirky_microsoft_zoho_us_gaap.xlsx",
]


class TestGate6_CrossDeliverableParity:
    """
    Gate 6: Cross-Deliverable Numerical Parity & Institutional Pack Completeness.
    """

    @pytest.mark.parametrize("file_path", TEST_INPUTS, ids=lambda p: p.name)
    def test_pack_deliverable_generation_and_parity(self, file_path: Path, tmp_path: Path):
        assert file_path.exists(), f"Test input not found: {file_path}"

        # 1. Run the pack generator via process_file
        out_dir = tmp_path / "pack_out"
        out_dir.mkdir(parents=True, exist_ok=True)

        pack_res = process_file(str(file_path), output_dir=str(out_dir))
        assert isinstance(pack_res, dict), "pack_res must be a dictionary"

        xlsx_path = pack_res["xlsx_path"]
        pdf_path = pack_res["pdf_path"]
        pptx_path = pack_res["pptx_path"]
        zip_path = pack_res["zip_path"]
        preview = pack_res["preview"]

        # ── Assertion 3: Zip file contains exactly 3 files (.xlsx, .pdf, .pptx) ──
        assert os.path.exists(zip_path), f"ZIP pack not generated at {zip_path}"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zip_entries = zf.namelist()
            assert len(zip_entries) == 3, f"ZIP must contain exactly 3 files, found {len(zip_entries)}: {zip_entries}"
            zip_exts = sorted(os.path.splitext(e)[1].lower() for e in zip_entries)
            assert zip_exts == [".pdf", ".pptx", ".xlsx"], f"ZIP must contain .xlsx, .pdf, .pptx, got: {zip_exts}"

        # ── Assertion 4: PDF file exists and has size > 15,000 bytes ──
        assert os.path.exists(pdf_path), f"PDF tear-sheet not found at {pdf_path}"
        pdf_size = os.path.getsize(pdf_path)
        assert pdf_size > 15000, f"PDF file size {pdf_size} bytes is <= 15,000 bytes threshold"

        # ── Assertion 5: PPTX file exists and has size > 30,000 bytes ──
        assert os.path.exists(pptx_path), f"PPTX pitchbook not found at {pptx_path}"
        pptx_size = os.path.getsize(pptx_path)
        assert pptx_size > 30000, f"PPTX file size {pptx_size} bytes is <= 30,000 bytes threshold"

        # ── Assertion 6: Excel file has 0 formula errors ──
        assert os.path.exists(xlsx_path), f"Excel model not found at {xlsx_path}"
        checker = FormulaChecker()
        scan_res = checker.scan(xlsx_path)
        assert not scan_res.has_errors, f"Formula errors detected in {xlsx_path}: {scan_res.error_cells}"
        assert scan_res.total_formulas_scanned > 0, "No formulas were scanned in workbook"

        # ── Assertion 1: Total Revenue, EBITDA, Net Income in JSON preview matches .xlsx model cell values to 0.00 ──
        wb = openpyxl.load_workbook(xlsx_path, data_only=False)
        assert "03_Income_Statement" in wb.sheetnames, "Missing 03_Income_Statement sheet"
        ws_is = wb["03_Income_Statement"]

        # Locate the last historical column by inspecting row 5 (Revenue) for hardcoded values (non-formula)
        last_hist_col = 2
        for col_idx in range(2, 20):
            val = ws_is.cell(5, col_idx).value
            if val is not None and not str(val).startswith("="):
                last_hist_col = col_idx

        xlsx_revenue = float(ws_is.cell(5, last_hist_col).value)
        xlsx_ebitda = float(ws_is.cell(11, last_hist_col).value)
        xlsx_net_income = float(ws_is.cell(18, last_hist_col).value)

        preview_revenue = float(preview["total_revenue"])
        preview_ebitda = float(preview["ebitda"])
        preview_net_income = float(preview["net_income"])

        # Compare to 0.00 (within 0.01 tolerance for floating point representation)
        assert abs(preview_revenue - xlsx_revenue) < 0.01, (
            f"Revenue mismatch: Preview={preview_revenue:.2f} vs XLSX={xlsx_revenue:.2f}"
        )
        assert abs(preview_ebitda - xlsx_ebitda) < 0.01, (
            f"EBITDA mismatch: Preview={preview_ebitda:.2f} vs XLSX={xlsx_ebitda:.2f}"
        )
        assert abs(preview_net_income - xlsx_net_income) < 0.01, (
            f"Net Income mismatch: Preview={preview_net_income:.2f} vs XLSX={xlsx_net_income:.2f}"
        )

        # Check Executive Summary tab parity as well
        if "01_Exec_Summary" in wb.sheetnames:
            ws_summary = wb["01_Exec_Summary"]
            exec_hist_rev = float(ws_summary.cell(6, 2).value)
            assert abs(preview_revenue - exec_hist_rev) < 0.01, (
                f"Exec summary revenue mismatch: Preview={preview_revenue:.2f} vs ExecSummary={exec_hist_rev:.2f}"
            )

        # ── Assertion 2: Base Enterprise Value and Equity Value in preview match DCF output ──
        assert "ev_base" in preview, "ev_base missing in preview"
        assert "equity_base" in preview, "equity_base missing in preview"

        if "01_Exec_Summary" in wb.sheetnames:
            ws_summary = wb["01_Exec_Summary"]
            # Row 13 is Base Scenario valuation in Football Field: B13=EV, C13=Equity Value
            exec_ev = float(ws_summary.cell(13, 2).value)
            exec_equity = float(ws_summary.cell(13, 3).value)
            assert abs(preview["ev_base"] - exec_ev) < 0.01, (
                f"Base EV mismatch: Preview={preview['ev_base']:.2f} vs ExecSummary={exec_ev:.2f}"
            )
            assert abs(preview["equity_base"] - exec_equity) < 0.01, (
                f"Base Equity Value mismatch: Preview={preview['equity_base']:.2f} vs ExecSummary={exec_equity:.2f}"
            )
