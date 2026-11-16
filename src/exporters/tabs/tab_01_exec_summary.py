"""
tab_01_exec_summary.py
Build the Executive Summary sheet.
"""
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def build_exec_summary(wb, engine_output: dict, metadata: dict):
    ws = wb.create_sheet("01_Exec_Summary")

    # ── Title ─────────────────────────────────────────────────────────────
    ws["A1"] = metadata.get("company_name", "Company") + " — Executive Summary"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:H1")
    ws["A1"].alignment = Alignment(horizontal="center")

    # ── Scenario selector ─────────────────────────────────────────────────
    ws["A2"] = "Scenario (1=Base, 2=Bull, 3=Bear)"
    ws["A2"].font = Font(bold=True)
    ws["B2"] = 1  # default Base
    ws["B2"].font = Font(color=S.BLUE, bold=True)

    dv = DataValidation(type="whole", operator="between", formula1="1", formula2="3",
                        showDropDown=False, showErrorMessage=True,
                        errorTitle="Invalid", error="Enter 1 (Base), 2 (Bull), or 3 (Bear)")
    dv.add("B2")
    ws.add_data_validation(dv)

    # ── KPI Cards ─────────────────────────────────────────────────────────
    row = 4
    ws.cell(row, 1, "KEY PERFORMANCE INDICATORS").font = Font(bold=True, size=11)
    S.header_style(ws, row, "FF1F4E79")  # dark navy header

    row = 5
    headers = ["Metric", "Value", "Source"]
    for c, h in enumerate(headers, 1):
        ws.cell(row, c, h).font = Font(bold=True)

    # Attempt to pull from engine_output; fall back gracefully
    base = engine_output.get("Base", engine_output.get("base", {}))
    inc  = base.get("income_statement", {})
    dcf  = base.get("dcf", {})
    periods = list(inc.get("revenue", {}).keys()) if isinstance(inc.get("revenue"), dict) else []
    hist_candidates = [p for p in periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(periods) else max(1, len(periods) // 2)
    last_hist_col = get_column_letter(1 + n_hist) if periods else "D"
    last_proj_col = get_column_letter(1 + len(periods)) if periods else "I"

    # Last historical revenue
    hist_rev = 0
    rev_dict = inc.get("revenue", {})
    if isinstance(rev_dict, dict) and rev_dict:
        vals = list(rev_dict.values())
        hist_rev = vals[n_hist - 1] if n_hist <= len(vals) else vals[-1]

    # Terminal year revenue (last projected)
    terminal_rev = list(rev_dict.values())[-1] if isinstance(rev_dict, dict) and rev_dict else hist_rev

    # EBITDA margin
    ebitda_m = inc.get("ebitda_margin", 0.20)
    net_m    = inc.get("net_margin", 0.10)

    kpis = [
        ("Revenue (Last Historical)", hist_rev,
         f"='03_Income_Statement'!{last_hist_col}5"),
        ("Revenue (Terminal Year)",   terminal_rev,
         f"='03_Income_Statement'!{last_proj_col}5"),
        ("EBITDA Margin",             ebitda_m,
         f"='03_Income_Statement'!{last_proj_col}12"),
        ("Net Margin",                net_m,
         f"='03_Income_Statement'!{last_proj_col}19"),
    ]

    for i, (metric, val, link_formula) in enumerate(kpis):
        r = row + 1 + i
        ws.cell(r, 1, metric)
        ws.cell(r, 2, val)
        ws.cell(r, 2).number_format = S.pct_format if "Margin" in metric else S.currency_format
        ws.cell(r, 3, link_formula).font = Font(color=S.GREEN)

    # ── Valuation Football Field ──────────────────────────────────────────
    row = 11
    ws.cell(row, 1, "VALUATION FOOTBALL FIELD").font = Font(bold=True, size=11)
    S.header_style(ws, row, "FF1F4E79")

    row = 12
    for c, h in enumerate(["Scenario", "Enterprise Value", "Equity Value", "Implied Price / Share"], 1):
        ws.cell(row, c, h).font = Font(bold=True)

    scenarios = ["Base", "Bull", "Bear"]
    for i, scen in enumerate(scenarios):
        r = row + 1 + i
        s_data = engine_output.get(scen, engine_output.get(scen.lower(), {}))
        dcf_s  = s_data.get("dcf", {})
        ws.cell(r, 1, scen)
        ws.cell(r, 2, dcf_s.get("enterprise_value", ""))
        ws.cell(r, 2).number_format = S.currency_format
        ws.cell(r, 3, dcf_s.get("equity_value", ""))
        ws.cell(r, 3).number_format = S.currency_format
        ws.cell(r, 4, dcf_s.get("price_per_share", ""))
        ws.cell(r, 4).number_format = S.currency_format
        # Cross-sheet link formula
        ws.cell(r, 5, f"='07_DCF_&_Sensitivity'!B{30 + i}").font = Font(color=S.GREEN)

    # ── Column widths ────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 20
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.column_dimensions["E"].width = 28

    return ws
