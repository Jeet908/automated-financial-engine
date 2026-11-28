"""
tab_05_cash_flow.py
Build the Cash Flow Statement sheet.
"""
from openpyxl.styles import Font, PatternFill
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def _col(c: int) -> str:
    return get_column_letter(c)


def build_cash_flow(wb, engine_output: dict):
    ws = wb.create_sheet("05_Cash_Flow")

    ws["A1"] = "CASH FLOW STATEMENT"
    ws["A1"].font = Font(bold=True, size=14)

    base = engine_output.get("Base", engine_output.get("base", {}))
    cf   = base.get("cash_flow", {})
    bs   = base.get("balance_sheet", {})
    inc  = base.get("income_statement", {})

    all_periods = list(cf.get("cfo", {}).keys()) if isinstance(cf.get("cfo"), dict) else []
    if not all_periods:
        all_periods = list(inc.get("revenue", {}).keys()) if isinstance(inc.get("revenue"), dict) else []
    hist_candidates = [p for p in all_periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(all_periods) else max(1, len(all_periods) // 2)
    hist_periods = all_periods[:n_hist]
    proj_periods = all_periods[n_hist:]

    # Period headers
    ws.cell(3, 1, "Line Item").font = Font(bold=True)
    for c_idx, period in enumerate(all_periods, 2):
        ws.cell(3, c_idx, str(period)).font = Font(bold=True)

    # Row map
    rows = {
        "OPERATING ACTIVITIES":  5,
        "Net Income":            6,
        "Add: D&A":              7,
        "Change in Working Capital": 8,
        "CFO":                   9,
        "INVESTING ACTIVITIES": 11,
        "CapEx":                12,
        "CFI":                  13,
        "FINANCING ACTIVITIES": 15,
        "Debt Repayment":       16,
        "Dividends Paid":       17,
        "CFF":                  18,
        "Net Change in Cash":   20,
        "Opening Cash":         21,
        "Ending Cash":          22,  # used by BS cash link
        "CASH BRIDGE CHECK":    24,
    }

    # Section headers
    for label in ("OPERATING ACTIVITIES", "INVESTING ACTIVITIES", "FINANCING ACTIVITIES"):
        ws.cell(rows[label], 1, label).font = Font(bold=True, size=11)

    for label, r in rows.items():
        if label not in ("OPERATING ACTIVITIES", "INVESTING ACTIVITIES", "FINANCING ACTIVITIES"):
            ws.cell(r, 1, label)

    IS_ROW = {
        "PAT": 18, "DA": 13, "REV": 5,
    }

    def put_hist(row_key, cf_key):
        for c_idx, period in enumerate(hist_periods, 2):
            val = cf.get(cf_key, {}).get(period, 0)
            cell = ws.cell(rows[row_key], c_idx, val)
            cell.font = Font(color=S.BLUE)
            cell.number_format = S.currency_format

    put_hist("CFO", "cfo")
    put_hist("CFI", "cfi")
    put_hist("CFF", "cff")

    # Projected section
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        prev = _col(c_idx - 1)

        # Net Income from IS
        ni = ws.cell(rows["Net Income"], c_idx,
                     f"='03_Income_Statement'!{col}{IS_ROW['PAT']}")
        ni.font = Font(color=S.GREEN)
        ni.number_format = S.currency_format

        # D&A from IS
        da = ws.cell(rows["Add: D&A"], c_idx,
                     f"='03_Income_Statement'!{col}{IS_ROW['DA']}")
        da.font = Font(color=S.GREEN)
        da.number_format = S.currency_format

        # Change in WC from schedules
        wc = ws.cell(rows["Change in Working Capital"], c_idx,
                     f"=-'06_Schedules'!{col}10")
        wc.font = Font(color=S.GREEN)
        wc.number_format = S.currency_format

        # CFO
        cfo = ws.cell(rows["CFO"], c_idx,
                      f"={col}{rows['Net Income']}+"
                      f"{col}{rows['Add: D&A']}+"
                      f"{col}{rows['Change in Working Capital']}")
        cfo.font = Font(bold=True, color=S.BLACK)
        cfo.number_format = S.currency_format

        # CapEx from schedules
        capex = ws.cell(rows["CapEx"], c_idx,
                        f"=-'06_Schedules'!{col}14")
        capex.font = Font(color=S.GREEN)
        capex.number_format = S.currency_format

        # CFI
        cfi = ws.cell(rows["CFI"], c_idx,
                      f"={col}{rows['CapEx']}")
        cfi.font = Font(bold=True, color=S.BLACK)
        cfi.number_format = S.currency_format

        # Debt repayment from schedules
        dr = ws.cell(rows["Debt Repayment"], c_idx,
                     f"=-'06_Schedules'!{col}20")
        dr.font = Font(color=S.GREEN)
        dr.number_format = S.currency_format

        # Dividends
        div = ws.cell(rows["Dividends Paid"], c_idx,
                      f"=-'03_Income_Statement'!{col}{IS_ROW['PAT']}*'02_Assumptions'!E13")
        div.font = Font(color=S.GREEN)
        div.number_format = S.currency_format

        # CFF
        cff = ws.cell(rows["CFF"], c_idx,
                      f"={col}{rows['Debt Repayment']}+{col}{rows['Dividends Paid']}")
        cff.font = Font(bold=True, color=S.BLACK)
        cff.number_format = S.currency_format

        # Net change
        net = ws.cell(rows["Net Change in Cash"], c_idx,
                      f"={col}{rows['CFO']}+{col}{rows['CFI']}+{col}{rows['CFF']}")
        net.font = Font(bold=True, color=S.BLACK)
        net.number_format = S.currency_format

        # Opening cash (prev closing)
        oc = ws.cell(rows["Opening Cash"], c_idx,
                     f"={prev}{rows['Ending Cash']}")
        oc.font = Font(color=S.BLACK)
        oc.number_format = S.currency_format

        # Ending cash
        ec = ws.cell(rows["Ending Cash"], c_idx,
                     f"={col}{rows['Opening Cash']}+{col}{rows['Net Change in Cash']}")
        ec.font = Font(bold=True, color=S.BLACK)
        ec.number_format = S.currency_format

        # Historical opening cash for first hist period
        if c_idx == 2:
            opening_cash_val = bs.get("cash", {}).get(all_periods[0] if all_periods else 0, 0)
            ws.cell(rows["Opening Cash"], 2, opening_cash_val).font = Font(color=S.BLUE)

    # CASH BRIDGE CHECK row
    ws.cell(rows["CASH BRIDGE CHECK"], 1, "CASH BRIDGE CHECK").font = Font(bold=True)

    if all_periods:
        for c_idx in range(2, 2 + len(all_periods)):
            col = _col(c_idx)
            chk = ws.cell(rows["CASH BRIDGE CHECK"], c_idx,
                          f"={col}{rows['Ending Cash']}-'04_Balance_Sheet'!{col}6")
            chk.font = Font(bold=True, color=S.BLACK)
            chk.number_format = S.currency_format

        first_col = _col(2)
        last_col  = _col(1 + len(all_periods))
        chk_range = f"{first_col}{rows['CASH BRIDGE CHECK']}:{last_col}{rows['CASH BRIDGE CHECK']}"

        green_fill = PatternFill(fill_type="solid", fgColor=S.GREEN_FILL)
        red_fill   = PatternFill(fill_type="solid", fgColor=S.RED_FILL)

        ws.conditional_formatting.add(
            chk_range, CellIsRule(operator="equal", formula=["0"], fill=green_fill))
        ws.conditional_formatting.add(
            chk_range, CellIsRule(operator="notEqual", formula=["0"], fill=red_fill))

    ws.column_dimensions["A"].width = 28
    for c_idx in range(2, 2 + len(all_periods) + 1):
        ws.column_dimensions[_col(c_idx)].width = 15

    return ws
