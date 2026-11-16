"""
tab_06_schedules.py
Build the Supporting Schedules sheet (WC, FA, Debt).
"""
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def _col(c: int) -> str:
    return get_column_letter(c)


def build_schedules(wb, engine_output: dict):
    ws = wb.create_sheet("06_Schedules")

    ws["A1"] = "SUPPORTING SCHEDULES"
    ws["A1"].font = Font(bold=True, size=14)

    base = engine_output.get("Base", engine_output.get("base", {}))
    inc  = base.get("income_statement", {})
    bs   = base.get("balance_sheet", {})

    all_periods = list(inc.get("revenue", {}).keys()) if isinstance(inc.get("revenue"), dict) else []
    hist_candidates = [p for p in all_periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(all_periods) else max(1, len(all_periods) // 2)
    hist_periods = all_periods[:n_hist]
    proj_periods = all_periods[n_hist:]

    # Period headers (row 3)
    ws.cell(3, 1, "Line Item").font = Font(bold=True)
    for c_idx, period in enumerate(all_periods, 2):
        ws.cell(3, c_idx, str(period)).font = Font(bold=True)

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 1 — WORKING CAPITAL SCHEDULE (rows 4-11)
    # ════════════════════════════════════════════════════════════════════════
    WC = {
        "WC SCHEDULE":  4,
        "Receivables":  6,
        "Inventory":    7,
        "Payables":     8,
        "NWC":          9,
        "ΔNWC":        10,
    }

    ws.cell(WC["WC SCHEDULE"], 1, "WORKING CAPITAL SCHEDULE").font = Font(bold=True, size=11)

    for label, r in WC.items():
        if label != "WC SCHEDULE":
            ws.cell(r, 1, label)

    # Historical values
    for c_idx, period in enumerate(hist_periods, 2):
        col = _col(c_idx)
        for key, bs_key in [("Receivables", "receivables"),
                             ("Inventory", "inventory"),
                             ("Payables", "payables")]:
            cell = ws.cell(WC[key], c_idx, bs.get(bs_key, {}).get(period, 0))
            cell.font = Font(color=S.BLUE)
            cell.number_format = S.currency_format

    # NWC historical
    for c_idx, period in enumerate(hist_periods, 2):
        col  = _col(c_idx)
        cell = ws.cell(WC["NWC"], c_idx,
                       f"={col}{WC['Receivables']}+{col}{WC['Inventory']}-{col}{WC['Payables']}")
        cell.font = Font(color=S.BLACK)
        cell.number_format = S.currency_format
        ws.cell(WC["ΔNWC"], c_idx, 0).font = Font(color=S.BLUE)

    # Projected WC via days formulas
    ASM_ROW_REC = 14   # Receivable Days in 02_Assumptions
    ASM_ROW_INV = 15   # Inventory Days
    ASM_ROW_PAY = 16   # Payable Days

    for c_idx in range(2 + len(hist_periods), 2 + len(all_periods)):
        col  = _col(c_idx)
        prev = _col(c_idx - 1)
        IS_REV_ROW = 5

        ws.cell(WC["Receivables"], c_idx,
                f"='03_Income_Statement'!{col}{IS_REV_ROW}/"
                f"365*'02_Assumptions'!E{ASM_ROW_REC}").font = Font(color=S.GREEN)
        ws.cell(WC["Receivables"], c_idx).number_format = S.currency_format

        ws.cell(WC["Inventory"], c_idx,
                f"='03_Income_Statement'!{col}{IS_REV_ROW}/"
                f"365*'02_Assumptions'!E{ASM_ROW_INV}").font = Font(color=S.GREEN)
        ws.cell(WC["Inventory"], c_idx).number_format = S.currency_format

        ws.cell(WC["Payables"], c_idx,
                f"='03_Income_Statement'!{col}{IS_REV_ROW}/"
                f"365*'02_Assumptions'!E{ASM_ROW_PAY}").font = Font(color=S.GREEN)
        ws.cell(WC["Payables"], c_idx).number_format = S.currency_format

        ws.cell(WC["NWC"], c_idx,
                f"={col}{WC['Receivables']}+{col}{WC['Inventory']}-{col}{WC['Payables']}").font = Font(color=S.BLACK)
        ws.cell(WC["NWC"], c_idx).number_format = S.currency_format

        ws.cell(WC["ΔNWC"], c_idx,
                f"={col}{WC['NWC']}-{prev}{WC['NWC']}").font = Font(color=S.BLACK)
        ws.cell(WC["ΔNWC"], c_idx).number_format = S.currency_format

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 2 — FIXED ASSET SCHEDULE (rows 12-16)
    # ════════════════════════════════════════════════════════════════════════
    FA = {
        "FA SCHEDULE":  12,
        "Opening NB":   13,
        "CapEx":        13,   # same section, offset below
        "Depreciation": 14,
        "Closing NB":   15,
    }
    # Re-define properly
    FA_ROWS = {
        "FA SCHEDULE": 12,
        "Opening NB":  13,
        "CapEx":       14,
        "Depreciation":15,
        "Closing NB":  16,
    }

    ws.cell(FA_ROWS["FA SCHEDULE"], 1, "FIXED ASSET SCHEDULE").font = Font(bold=True, size=11)
    for label, r in FA_ROWS.items():
        if label != "FA SCHEDULE":
            ws.cell(r, 1, label)

    ASM_DA_ROW  = 10   # D&A % in 02_Assumptions
    ASM_CAP_ROW = 17   # CapEx % in 02_Assumptions
    IS_REV_ROW  = 5

    for c_idx in range(2, 2 + len(all_periods)):
        col  = _col(c_idx)
        prev = _col(c_idx - 1)
        is_hist = c_idx < 2 + len(hist_periods)

        if c_idx == 2:
            opening = bs.get("net_fixed_assets", {}).get(all_periods[0] if all_periods else 0, 0)
            ws.cell(FA_ROWS["Opening NB"], c_idx, opening).font = Font(color=S.BLUE)
            ws.cell(FA_ROWS["Opening NB"], c_idx).number_format = S.currency_format
        else:
            ws.cell(FA_ROWS["Opening NB"], c_idx,
                    f"={prev}{FA_ROWS['Closing NB']}").font = Font(color=S.BLACK)
            ws.cell(FA_ROWS["Opening NB"], c_idx).number_format = S.currency_format

        if is_hist:
            capex_val = -bs.get("capex", {}).get(all_periods[c_idx - 2] if len(all_periods) > c_idx - 2 else 0, 0)
            ws.cell(FA_ROWS["CapEx"], c_idx, capex_val).font = Font(color=S.BLUE)
        else:
            ws.cell(FA_ROWS["CapEx"], c_idx,
                    f"='03_Income_Statement'!{col}{IS_REV_ROW}*'02_Assumptions'!E{ASM_CAP_ROW}").font = Font(color=S.GREEN)
        ws.cell(FA_ROWS["CapEx"], c_idx).number_format = S.currency_format

        if is_hist:
            da_val = inc.get("depreciation", {}).get(all_periods[c_idx - 2] if len(all_periods) > c_idx - 2 else 0, 0)
            ws.cell(FA_ROWS["Depreciation"], c_idx, da_val).font = Font(color=S.BLUE)
        else:
            ws.cell(FA_ROWS["Depreciation"], c_idx,
                    f"='03_Income_Statement'!{col}{IS_REV_ROW}*'02_Assumptions'!E{ASM_DA_ROW}").font = Font(color=S.GREEN)
        ws.cell(FA_ROWS["Depreciation"], c_idx).number_format = S.currency_format

        ws.cell(FA_ROWS["Closing NB"], c_idx,
                f"={col}{FA_ROWS['Opening NB']}+{col}{FA_ROWS['CapEx']}-{col}{FA_ROWS['Depreciation']}").font = Font(color=S.BLACK)
        ws.cell(FA_ROWS["Closing NB"], c_idx).number_format = S.currency_format

    # ════════════════════════════════════════════════════════════════════════
    # SECTION 3 — DEBT SCHEDULE (rows 18-23)
    # ════════════════════════════════════════════════════════════════════════
    DS_ROWS = {
        "DEBT SCHEDULE":    18,
        "Opening Debt":     19,
        "Repayment":        20,
        "Closing Debt":     21,
        "Interest Expense": 22,
    }

    ws.cell(DS_ROWS["DEBT SCHEDULE"], 1, "DEBT SCHEDULE").font = Font(bold=True, size=11)
    for label, r in DS_ROWS.items():
        if label != "DEBT SCHEDULE":
            ws.cell(r, 1, label)

    ASM_INT_ROW = 11   # Interest Rate in 02_Assumptions
    REPAYMENT_PCT = 0.05  # 5% annual repayment as default

    for c_idx in range(2, 2 + len(all_periods)):
        col  = _col(c_idx)
        prev = _col(c_idx - 1)
        is_hist = c_idx < 2 + len(hist_periods)

        if c_idx == 2:
            opening_debt = bs.get("debt", {}).get(all_periods[0] if all_periods else 0, 0)
            ws.cell(DS_ROWS["Opening Debt"], c_idx, opening_debt).font = Font(color=S.BLUE)
        else:
            ws.cell(DS_ROWS["Opening Debt"], c_idx,
                    f"={prev}{DS_ROWS['Closing Debt']}").font = Font(color=S.BLACK)
        ws.cell(DS_ROWS["Opening Debt"], c_idx).number_format = S.currency_format

        if is_hist:
            repay = bs.get("debt_repayment", {}).get(all_periods[c_idx - 2] if len(all_periods) > c_idx - 2 else 0, 0)
            ws.cell(DS_ROWS["Repayment"], c_idx, repay).font = Font(color=S.BLUE)
        else:
            ws.cell(DS_ROWS["Repayment"], c_idx,
                    f"={col}{DS_ROWS['Opening Debt']}*{REPAYMENT_PCT}").font = Font(color=S.BLACK)
        ws.cell(DS_ROWS["Repayment"], c_idx).number_format = S.currency_format

        ws.cell(DS_ROWS["Closing Debt"], c_idx,
                f"={col}{DS_ROWS['Opening Debt']}-{col}{DS_ROWS['Repayment']}").font = Font(color=S.BLACK)
        ws.cell(DS_ROWS["Closing Debt"], c_idx).number_format = S.currency_format

        ws.cell(DS_ROWS["Interest Expense"], c_idx,
                f"={col}{DS_ROWS['Opening Debt']}*'02_Assumptions'!E{ASM_INT_ROW}").font = Font(color=S.GREEN)
        ws.cell(DS_ROWS["Interest Expense"], c_idx).number_format = S.currency_format

    ws.column_dimensions["A"].width = 24
    for c_idx in range(2, 2 + len(all_periods) + 1):
        ws.column_dimensions[_col(c_idx)].width = 15

    return ws
