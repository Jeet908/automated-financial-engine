"""
tab_04_balance_sheet.py
Build the Balance Sheet sheet with balance-check conditional formatting.
"""
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def _col(c: int) -> str:
    return get_column_letter(c)


def build_balance_sheet(wb, engine_output: dict):
    ws = wb.create_sheet("04_Balance_Sheet")

    ws["A1"] = "BALANCE SHEET"
    ws["A1"].font = Font(bold=True, size=14)

    base = engine_output.get("Base", engine_output.get("base", {}))
    bs   = base.get("balance_sheet", {})

    all_periods = list(bs.get("cash", {}).keys()) if isinstance(bs.get("cash"), dict) else []
    hist_candidates = [p for p in all_periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(all_periods) else max(1, len(all_periods) // 2)
    hist_periods = all_periods[:n_hist]
    proj_periods = all_periods[n_hist:]

    # ── Period headers ─────────────────────────────────────────────────────
    ws.cell(3, 1, "Line Item").font = Font(bold=True)
    for c_idx, period in enumerate(all_periods, 2):
        ws.cell(3, c_idx, str(period)).font = Font(bold=True)

    # Row map
    rows = {
        "ASSETS":           5,
        "Cash":             6,
        "Receivables":      7,
        "Inventory":        8,
        "Net Fixed Assets": 9,
        "Other Assets":    10,
        "TOTAL ASSETS":    11,
        "LIABILITIES & EQUITY": 13,
        "Payables":        14,
        "Debt":            15,
        "Other Liabilities":16,
        "Share Capital":   17,
        "Retained Earnings":18,
        "TOTAL EQUITY":    19,
        "TOTAL LIAB+EQUITY":20,
        "BALANCE CHECK":   21,
    }

    # Section headers
    for label in ("ASSETS", "LIABILITIES & EQUITY"):
        r = rows[label]
        ws.cell(r, 1, label).font = Font(bold=True, size=11)

    for label, r in rows.items():
        if label not in ("ASSETS", "LIABILITIES & EQUITY"):
            ws.cell(r, 1, label)

    def put_hist(row_key, bs_key):
        for c_idx, period in enumerate(hist_periods, 2):
            val = bs.get(bs_key, {}).get(period, 0)
            cell = ws.cell(rows[row_key], c_idx, val)
            cell.font = Font(color=S.BLUE)
            cell.number_format = S.currency_format

    put_hist("Cash", "cash")
    put_hist("Receivables", "receivables")
    put_hist("Inventory", "inventory")
    put_hist("Net Fixed Assets", "net_fixed_assets")
    put_hist("Other Assets", "other_assets")
    put_hist("Payables", "payables")
    put_hist("Debt", "debt")
    put_hist("Other Liabilities", "other_liabilities")
    put_hist("Share Capital", "share_capital")
    put_hist("Retained Earnings", "retained_earnings")

    # Projected formulas — link to schedules / cash flow
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col = _col(c_idx)

        # Cash — from CFS ending cash
        ws.cell(rows["Cash"], c_idx,
                f"='05_Cash_Flow'!{col}22").font = Font(color=S.GREEN)
        ws.cell(rows["Cash"], c_idx).number_format = S.currency_format

        # Receivables from WC schedule
        ws.cell(rows["Receivables"], c_idx,
                f"='06_Schedules'!{col}6").font = Font(color=S.GREEN)
        ws.cell(rows["Receivables"], c_idx).number_format = S.currency_format

        # Inventory from WC schedule
        ws.cell(rows["Inventory"], c_idx,
                f"='06_Schedules'!{col}7").font = Font(color=S.GREEN)
        ws.cell(rows["Inventory"], c_idx).number_format = S.currency_format

        # NFA from FA schedule closing NB
        ws.cell(rows["Net Fixed Assets"], c_idx,
                f"='06_Schedules'!{col}16").font = Font(color=S.GREEN)
        ws.cell(rows["Net Fixed Assets"], c_idx).number_format = S.currency_format

        # Other assets — static / placeholder
        ws.cell(rows["Other Assets"], c_idx, 0).font = Font(color=S.BLUE)
        ws.cell(rows["Other Assets"], c_idx).number_format = S.currency_format

        # Payables from WC schedule
        ws.cell(rows["Payables"], c_idx,
                f"='06_Schedules'!{col}8").font = Font(color=S.GREEN)
        ws.cell(rows["Payables"], c_idx).number_format = S.currency_format

        # Debt from debt schedule closing
        ws.cell(rows["Debt"], c_idx,
                f"='06_Schedules'!{col}21").font = Font(color=S.GREEN)
        ws.cell(rows["Debt"], c_idx).number_format = S.currency_format

        # Other liabilities — static
        ws.cell(rows["Other Liabilities"], c_idx, 0).font = Font(color=S.BLUE)
        ws.cell(rows["Other Liabilities"], c_idx).number_format = S.currency_format

        # Share Capital — constant
        prev = _col(c_idx - 1)
        ws.cell(rows["Share Capital"], c_idx,
                f"={prev}{rows['Share Capital']}").font = Font(color=S.BLACK)
        ws.cell(rows["Share Capital"], c_idx).number_format = S.currency_format

        # Retained Earnings
        ws.cell(rows["Retained Earnings"], c_idx,
                f"={prev}{rows['Retained Earnings']}+'03_Income_Statement'!{col}{18}-"
                f"('03_Income_Statement'!{col}{18}*'02_Assumptions'!E13)").font = Font(color=S.GREEN)
        ws.cell(rows["Retained Earnings"], c_idx).number_format = S.currency_format

    # ── Totals for all periods ─────────────────────────────────────────────
    for c_idx in range(2, 2 + len(all_periods)):
        col = _col(c_idx)
        # Total Assets
        cell = ws.cell(rows["TOTAL ASSETS"], c_idx,
                       f"=SUM({col}{rows['Cash']}:{col}{rows['Other Assets']})")
        cell.font = Font(bold=True, color=S.BLACK)
        cell.number_format = S.currency_format

        # Total Equity
        cell = ws.cell(rows["TOTAL EQUITY"], c_idx,
                       f"=SUM({col}{rows['Share Capital']}:{col}{rows['Retained Earnings']})")
        cell.font = Font(bold=True, color=S.BLACK)
        cell.number_format = S.currency_format

        # Total Liab+Equity
        cell = ws.cell(rows["TOTAL LIAB+EQUITY"], c_idx,
                       f"=SUM({col}{rows['Payables']}:{col}{rows['Other Liabilities']})"
                       f"+{col}{rows['TOTAL EQUITY']}")
        cell.font = Font(bold=True, color=S.BLACK)
        cell.number_format = S.currency_format

        # Balance Check
        chk = ws.cell(rows["BALANCE CHECK"], c_idx,
                      f"={col}{rows['TOTAL ASSETS']}-{col}{rows['TOTAL LIAB+EQUITY']}")
        chk.font = Font(bold=True, color=S.BLACK)
        chk.number_format = S.currency_format

    ws.cell(rows["BALANCE CHECK"], 1, "BALANCE CHECK").font = Font(bold=True)

    # ── Conditional formatting on balance check row ────────────────────────
    if all_periods:
        first_col = _col(2)
        last_col  = _col(1 + len(all_periods))
        chk_range = f"{first_col}{rows['BALANCE CHECK']}:{last_col}{rows['BALANCE CHECK']}"

        green_fill = PatternFill(fill_type="solid", fgColor=S.GREEN_FILL)
        red_fill   = PatternFill(fill_type="solid", fgColor=S.RED_FILL)

        ws.conditional_formatting.add(
            chk_range,
            CellIsRule(operator="equal", formula=["0"], fill=green_fill)
        )
        ws.conditional_formatting.add(
            chk_range,
            CellIsRule(operator="notEqual", formula=["0"], fill=red_fill)
        )

    ws.column_dimensions["A"].width = 24
    for c_idx in range(2, 2 + len(all_periods) + 1):
        ws.column_dimensions[_col(c_idx)].width = 15

    return ws
