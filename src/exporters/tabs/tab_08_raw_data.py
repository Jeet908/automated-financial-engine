"""
tab_08_raw_data.py
Audit trail — dump the full normalized source data.
"""
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def _col(c: int) -> str:
    return get_column_letter(c)


def build_raw_data(wb, normalized):
    """
    normalized — NormalizedFinancials Pydantic object OR dict.
    Dumps every numeric field as an audit-trail table with BLUE font.
    """
    ws = wb.create_sheet("08_Raw_Data")

    ws["A1"] = "RAW DATA — AUDIT TRAIL"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "All values are hardcoded source inputs (blue = hard-coded)."
    ws["A2"].font = Font(italic=True, color=S.BLUE)

    # Convert to dict
    if hasattr(normalized, "model_dump"):
        data = normalized.model_dump()
    elif hasattr(normalized, "dict"):
        data = normalized.dict()
    elif isinstance(normalized, dict):
        data = normalized
    else:
        data = {}

    # Find all periods from any list field
    periods = data.get("periods", [])

    # Header row
    ws.cell(4, 1, "Line Item").font = Font(bold=True)
    for c_idx, period in enumerate(periods, 2):
        ws.cell(4, c_idx, str(period)).font = Font(bold=True)

    # Dump each field
    skip_fields = {"standard", "currency", "unit", "multiplier", "fiscal_year_end",
                   "periods", "is_startup"}
    row = 5

    for field, value in data.items():
        if field in skip_fields:
            continue

        ws.cell(row, 1, field.replace("_", " ").title())
        ws.cell(row, 1).font = Font(bold=False)

        if isinstance(value, (list, tuple)):
            for c_idx, val in enumerate(value, 2):
                cell = ws.cell(row, c_idx, val if val is not None else "")
                cell.font = Font(color=S.BLUE)
                if isinstance(val, float):
                    cell.number_format = S.currency_format
        elif isinstance(value, dict):
            for c_idx, (k, v) in enumerate(value.items(), 2):
                cell = ws.cell(row, c_idx, v if v is not None else "")
                cell.font = Font(color=S.BLUE)
                if isinstance(v, float):
                    cell.number_format = S.currency_format
        elif isinstance(value, (int, float)):
            cell = ws.cell(row, 2, value)
            cell.font = Font(color=S.BLUE)
            if isinstance(value, float):
                cell.number_format = S.currency_format
        else:
            cell = ws.cell(row, 2, str(value) if value is not None else "")
            cell.font = Font(color=S.BLUE)

        row += 1

    # Also dump metadata row
    ws.cell(row + 1, 1, "Standard").font = Font(bold=True)
    ws.cell(row + 1, 2, data.get("standard", "")).font = Font(color=S.BLUE)
    ws.cell(row + 2, 1, "Currency").font = Font(bold=True)
    ws.cell(row + 2, 2, data.get("currency", "")).font = Font(color=S.BLUE)
    ws.cell(row + 3, 1, "Unit").font = Font(bold=True)
    ws.cell(row + 3, 2, data.get("unit", "")).font = Font(color=S.BLUE)
    ws.cell(row + 4, 1, "Multiplier").font = Font(bold=True)
    ws.cell(row + 4, 2, data.get("multiplier", 1)).font = Font(color=S.BLUE)

    ws.column_dimensions["A"].width = 28
    for c_idx in range(2, max(3, len(periods) + 2)):
        ws.column_dimensions[_col(c_idx)].width = 15

    return ws
