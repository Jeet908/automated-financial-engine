"""
tab_03_income_statement.py
Build the Income Statement sheet.
"""
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


# Row index map (1-based, below headers)
_ROWS = {
    "Revenue":        5,
    "COGS":           6,
    "Gross Profit":   7,
    "Gross Margin %": 8,
    "Employee Costs": 9,
    "Other Opex":    10,
    "EBITDA":        11,
    "EBITDA Margin %": 12,
    "D&A":           13,
    "EBIT":          14,
    "Interest":      15,
    "PBT":           16,
    "Tax":           17,
    "PAT":           18,
    "Net Margin %":  19,
}


def _col(c: int) -> str:
    return get_column_letter(c)


def build_income_statement(wb, engine_output: dict):
    ws = wb.create_sheet("03_Income_Statement")

    # ── Title ─────────────────────────────────────────────────────────────
    ws["A1"] = "INCOME STATEMENT"
    ws["A1"].font = Font(bold=True, size=14)

    # Gather periods from Base scenario
    base       = engine_output.get("Base", engine_output.get("base", {}))
    inc        = base.get("income_statement", {})
    all_periods = list(inc.get("revenue", {}).keys()) if isinstance(inc.get("revenue"), dict) else []

    # Separate historical vs projected
    hist_candidates = [p for p in all_periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(all_periods) else max(1, len(all_periods) // 2)
    hist_periods = all_periods[:n_hist]
    proj_periods = all_periods[n_hist:]

    # ── Period headers (row 3) ─────────────────────────────────────────────
    ws.cell(3, 1, "Line Item").font = Font(bold=True)
    ws.cell(4, 1, "").font           = Font(bold=True)

    for c_idx, period in enumerate(all_periods, 2):
        hdr = ws.cell(3, c_idx, str(period))
        hdr.font = Font(bold=True)
        hdr.alignment = Alignment(horizontal="center")

    # ── Row labels (column A) ──────────────────────────────────────────────
    for label, r in _ROWS.items():
        ws.cell(r, 1, label).font = Font(bold=("%" not in label and label not in ("COGS", "D&A", "Interest", "Tax")))

    # Helpers
    is_pct = lambda lbl: "%" in lbl

    def fill_hist(row, label, period_data: dict):
        for c_idx, period in enumerate(hist_periods, 2):
            val  = period_data.get(period, "")
            cell = ws.cell(row, c_idx, val if val != "" else 0)
            cell.font = Font(color=S.BLUE)
            if is_pct(label):
                cell.number_format = S.pct_format
            else:
                cell.number_format = S.currency_format

    def fill_proj_formula(row, label, formula_tpl):
        """formula_tpl receives col_letter; returns formula string."""
        for c_idx, period in enumerate(proj_periods, 2 + len(hist_periods)):
            col  = _col(c_idx)
            cell = ws.cell(row, c_idx, formula_tpl(col, c_idx, row))
            cell.font = Font(color=S.BLACK)
            if is_pct(label):
                cell.number_format = S.pct_format
            else:
                cell.number_format = S.currency_format

    # Assumption lookup: row in 02_Assumptions for each driver
    # We'll hard-code cross-sheet references using GREEN font
    ASM = "02_Assumptions"

    # Row numbers in 02_Assumptions (1-based, driver rows start at 5)
    ASM_ROW = {
        "rev_growth":   5,
        "gross_margin": 6,
        "emp_cost":     8,
        "other_opex":   9,
        "da":           10,
        "interest_rate":11,
        "tax_rate":     12,
        "capex":        16,
    }

    # ── Revenue ───────────────────────────────────────────────────────────
    rev_dict = inc.get("revenue", {})
    fill_hist(_ROWS["Revenue"], "Revenue", rev_dict)

    for c_idx, period in enumerate(proj_periods, 2 + len(hist_periods)):
        col      = _col(c_idx)
        prev_col = _col(c_idx - 1)
        # =PREV_REV * (1 + CHOOSE growth rate from assumptions)
        formula = (f"={prev_col}{_ROWS['Revenue']}*"
                   f"(1+'02_Assumptions'!E{ASM_ROW['rev_growth']})")
        cell = ws.cell(_ROWS["Revenue"], c_idx, formula)
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── COGS ──────────────────────────────────────────────────────────────
    cogs_dict = inc.get("cogs", {})
    fill_hist(_ROWS["COGS"], "COGS", cogs_dict)

    for c_idx, period in enumerate(proj_periods, 2 + len(hist_periods)):
        col     = _col(c_idx)
        # COGS = Revenue * (1 - Gross Margin %)
        formula = (f"={col}{_ROWS['Revenue']}*"
                   f"(1-'02_Assumptions'!E{ASM_ROW['gross_margin']})")
        cell = ws.cell(_ROWS["COGS"], c_idx, formula)
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── Gross Profit ──────────────────────────────────────────────────────
    gp_dict = inc.get("gross_profit", {})
    fill_hist(_ROWS["Gross Profit"], "Gross Profit", gp_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col = _col(c_idx)
        cell = ws.cell(_ROWS["Gross Profit"], c_idx,
                       f"={col}{_ROWS['Revenue']}-{col}{_ROWS['COGS']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format

    # ── Gross Margin % ────────────────────────────────────────────────────
    for c_idx in range(2, 2 + len(all_periods)):
        col = _col(c_idx)
        cell = ws.cell(_ROWS["Gross Margin %"], c_idx,
                       f"=IF({col}{_ROWS['Revenue']}=0,0,"
                       f"{col}{_ROWS['Gross Profit']}/{col}{_ROWS['Revenue']})")
        cell.font = Font(color=S.BLACK if c_idx >= 2 + len(hist_periods) else S.BLUE)
        cell.number_format = S.pct_format

    # ── Employee Costs ────────────────────────────────────────────────────
    emp_dict = inc.get("employee_costs", {})
    fill_hist(_ROWS["Employee Costs"], "Employee Costs", emp_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["Employee Costs"], c_idx,
                       f"={col}{_ROWS['Revenue']}*'02_Assumptions'!E{ASM_ROW['emp_cost']}")
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── Other Opex ───────────────────────────────────────────────────────
    opex_dict = inc.get("other_opex", {})
    fill_hist(_ROWS["Other Opex"], "Other Opex", opex_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["Other Opex"], c_idx,
                       f"={col}{_ROWS['Revenue']}*'02_Assumptions'!E{ASM_ROW['other_opex']}")
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── EBITDA ───────────────────────────────────────────────────────────
    ebitda_dict = inc.get("ebitda", {})
    fill_hist(_ROWS["EBITDA"], "EBITDA", ebitda_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["EBITDA"], c_idx,
                       f"={col}{_ROWS['Gross Profit']}-"
                       f"{col}{_ROWS['Employee Costs']}-"
                       f"{col}{_ROWS['Other Opex']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format

    # ── EBITDA Margin % ───────────────────────────────────────────────────
    for c_idx in range(2, 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["EBITDA Margin %"], c_idx,
                       f"=IF({col}{_ROWS['Revenue']}=0,0,"
                       f"{col}{_ROWS['EBITDA']}/{col}{_ROWS['Revenue']})")
        cell.font = Font(color=S.BLACK if c_idx >= 2 + len(hist_periods) else S.BLUE)
        cell.number_format = S.pct_format

    # ── D&A ──────────────────────────────────────────────────────────────
    da_dict = inc.get("depreciation", {})
    fill_hist(_ROWS["D&A"], "D&A", da_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["D&A"], c_idx,
                       f"={col}{_ROWS['Revenue']}*'02_Assumptions'!E{ASM_ROW['da']}")
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── EBIT ─────────────────────────────────────────────────────────────
    ebit_dict = inc.get("ebit", {})
    fill_hist(_ROWS["EBIT"], "EBIT", ebit_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["EBIT"], c_idx,
                       f"={col}{_ROWS['EBITDA']}-{col}{_ROWS['D&A']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format

    # ── Interest ─────────────────────────────────────────────────────────
    int_dict = inc.get("interest", {})
    fill_hist(_ROWS["Interest"], "Interest", int_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["Interest"], c_idx,
                       f"='06_Schedules'!{col}22")  # Debt schedule interest row
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── PBT ──────────────────────────────────────────────────────────────
    pbt_dict = inc.get("pbt", {})
    fill_hist(_ROWS["PBT"], "PBT", pbt_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["PBT"], c_idx,
                       f"={col}{_ROWS['EBIT']}-{col}{_ROWS['Interest']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format

    # ── Tax ───────────────────────────────────────────────────────────────
    tax_dict = inc.get("tax", {})
    fill_hist(_ROWS["Tax"], "Tax", tax_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["Tax"], c_idx,
                       f"=MAX(0,{col}{_ROWS['PBT']}*'02_Assumptions'!E{ASM_ROW['tax_rate']})")
        cell.font = Font(color=S.GREEN)
        cell.number_format = S.currency_format

    # ── PAT ───────────────────────────────────────────────────────────────
    pat_dict = inc.get("pat", {})
    fill_hist(_ROWS["PAT"], "PAT", pat_dict)
    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["PAT"], c_idx,
                       f"={col}{_ROWS['PBT']}-{col}{_ROWS['Tax']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format

    # ── Net Margin % ─────────────────────────────────────────────────────
    for c_idx in range(2, 2 + len(all_periods)):
        col  = _col(c_idx)
        cell = ws.cell(_ROWS["Net Margin %"], c_idx,
                       f"=IF({col}{_ROWS['Revenue']}=0,0,"
                       f"{col}{_ROWS['PAT']}/{col}{_ROWS['Revenue']})")
        cell.font = Font(color=S.BLACK if c_idx >= 2 + len(hist_periods) else S.BLUE)
        cell.number_format = S.pct_format

    ws.column_dimensions["A"].width = 22
    for c_idx in range(2, 2 + len(all_periods) + 1):
        ws.column_dimensions[_col(c_idx)].width = 15

    return ws
