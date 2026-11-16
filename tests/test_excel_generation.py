"""
Tests for institutional Excel workbook builder and live formulas.
"""

import os
from pathlib import Path
from financial_engine.excel.builder import InstitutionalExcelBuilder, OPENPYXL_AVAILABLE
from financial_engine.core.types import ModelConfiguration

try:
    import openpyxl
except ImportError:
    pass


def test_excel_generation(tmp_path):
    if not OPENPYXL_AVAILABLE:
        return

    output_file = tmp_path / "test_model.xlsx"
    builder = InstitutionalExcelBuilder(ModelConfiguration())
    saved_path = builder.build_workbook(str(output_file))

    assert Path(saved_path).exists()
    assert os.path.getsize(saved_path) > 5000

    wb = openpyxl.load_workbook(saved_path, data_only=False)
    sheet_names = wb.sheetnames

    # Verify all expected sheets exist
    for expected in ["Tutor Map", "Inputs", "IS", "BS", "CF", "Schedules", "DCF", "Checks"]:
        assert expected in sheet_names

    # Verify key formulas
    ws_is = wb["IS"]
    assert ws_is["C5"].value == "=Inputs!C5"
    assert ws_is["C7"].value == "=C5-C6"
    assert ws_is["F5"].value == "=E5*(1+Inputs!F32)"

    ws_bs = wb["BS"]
    assert ws_bs["F5"].value == "=CF!F19"
    assert ws_bs["C17"].value == "=C9-C15"

    ws_dcf = wb["DCF"]
    assert ws_dcf["C14"].value == "=Inputs!C47+Inputs!C48*Inputs!C49"
    assert ws_dcf["C37"].value == "=C35/C36"

    ws_chk = wb["Checks"]
    assert ws_chk["C5"].value == '=IF(MAX(BS!C17:J17)-MIN(BS!C17:J17)<0.01,"OK","ERROR")'
