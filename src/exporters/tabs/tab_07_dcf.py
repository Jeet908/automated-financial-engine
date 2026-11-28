"""
tab_07_dcf.py
Build the DCF & Sensitivity sheet.
"""
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

from src.exporters.styles import ExcelStyles as S


def _col(c: int) -> str:
    return get_column_letter(c)


def build_dcf(wb, engine_output: dict):
    ws = wb.create_sheet("07_DCF_&_Sensitivity")

    ws["A1"] = "DCF VALUATION & SENSITIVITY ANALYSIS"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:L1")

    base = engine_output.get("Base", engine_output.get("base", {}))
    inc  = base.get("income_statement", {})
    dcf  = base.get("dcf", {})
    bs   = base.get("balance_sheet", {})

    all_periods = list(inc.get("revenue", {}).keys()) if isinstance(inc.get("revenue"), dict) else []
    hist_candidates = [p for p in all_periods if str(p).endswith(('A', 'a', 'H', 'h')) or 'actual' in str(p).lower()]
    n_hist = len(hist_candidates) if hist_candidates and len(hist_candidates) < len(all_periods) else max(1, len(all_periods) // 2)
    hist_periods = all_periods[:n_hist]
    proj_periods = all_periods[n_hist:]

    # ── WACC Breakdown (rows 3-11) ─────────────────────────────────────────
    ws["A3"] = "WACC CALCULATION"
    ws["A3"].font = Font(bold=True, size=11)

    wacc_items = [
        ("Risk-Free Rate",          dcf.get("risk_free_rate",   0.065)),
        ("Equity Risk Premium",     dcf.get("erp",              0.055)),
        ("Beta",                    dcf.get("beta",             1.0)),
        ("Cost of Equity (Ke)",     "=B4+B5*B6"),
        ("Cost of Debt (Kd)",       dcf.get("cost_of_debt",     0.08)),
        ("Tax Rate",                "='02_Assumptions'!E12"),
        ("After-tax Kd",            "=B8*(1-B9)"),
        ("Equity Weight",           dcf.get("equity_weight",    0.70)),
        ("Debt Weight",             dcf.get("debt_weight",      0.30)),
        ("WACC",                    "=B7*B11+B10*B12"),
    ]

    for i, (label, val) in enumerate(wacc_items):
        r = 4 + i
        ws.cell(r, 1, label)
        c = ws.cell(r, 2, val)
        if isinstance(val, str) and val.startswith("="):
            c.font = Font(color=S.GREEN if "Assumptions" in val else S.BLACK)
        else:
            c.font = Font(color=S.BLUE)
        if "Weight" in label or "Rate" in label or "Ke" in label or "Kd" in label or "WACC" in label or "Tax" in label or "Premium" in label or "Beta" in label:
            c.number_format = S.pct_format if "Beta" not in label else "0.00"

    wacc_row = 14  # row of WACC value

    # ── UFCF Table (rows 16-26) ────────────────────────────────────────────
    ws.cell(16, 1, "UFCF TABLE").font = Font(bold=True, size=11)

    for c_idx, period in enumerate(proj_periods, 2):
        ws.cell(17, c_idx, str(period)).font = Font(bold=True)

    ufcf_rows = {
        "EBIT":           18,
        "Tax on EBIT":    19,
        "NOPAT":          20,
        "Add: D&A":       21,
        "Less: CapEx":    22,
        "Less: ΔNWC":     23,
        "UFCF":           24,
        "Discount Factor":25,
        "PV of UFCF":     26,
    }

    for label, r in ufcf_rows.items():
        ws.cell(r, 1, label)

    ASM_TAX = 12
    IS_EBIT_ROW = 14
    IS_DA_ROW   = 13
    FA_CAPEX_ROW = 14
    WC_DNWC_ROW  = 10

    for c_idx, period in enumerate(proj_periods, 2):
        col = _col(c_idx)
        src_c_idx = c_idx + len(hist_periods)
        src_col = _col(src_c_idx)

        ws.cell(ufcf_rows["EBIT"], c_idx,
                f"='03_Income_Statement'!{src_col}{IS_EBIT_ROW}").font = Font(color=S.GREEN)
        ws.cell(ufcf_rows["EBIT"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["Tax on EBIT"], c_idx,
                f"={col}{ufcf_rows['EBIT']}*'02_Assumptions'!E{ASM_TAX}").font = Font(color=S.GREEN)
        ws.cell(ufcf_rows["Tax on EBIT"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["NOPAT"], c_idx,
                f"={col}{ufcf_rows['EBIT']}-{col}{ufcf_rows['Tax on EBIT']}").font = Font(color=S.BLACK)
        ws.cell(ufcf_rows["NOPAT"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["Add: D&A"], c_idx,
                f"='03_Income_Statement'!{src_col}{IS_DA_ROW}").font = Font(color=S.GREEN)
        ws.cell(ufcf_rows["Add: D&A"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["Less: CapEx"], c_idx,
                f"='06_Schedules'!{src_col}{FA_CAPEX_ROW}").font = Font(color=S.GREEN)
        ws.cell(ufcf_rows["Less: CapEx"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["Less: ΔNWC"], c_idx,
                f"='06_Schedules'!{src_col}{WC_DNWC_ROW}").font = Font(color=S.GREEN)
        ws.cell(ufcf_rows["Less: ΔNWC"], c_idx).number_format = S.currency_format

        ws.cell(ufcf_rows["UFCF"], c_idx,
                f"={col}{ufcf_rows['NOPAT']}+{col}{ufcf_rows['Add: D&A']}"
                f"-{col}{ufcf_rows['Less: CapEx']}-{col}{ufcf_rows['Less: ΔNWC']}").font = Font(color=S.BLACK)
        ws.cell(ufcf_rows["UFCF"], c_idx).number_format = S.currency_format

        # Discount factor = 1/(1+WACC)^n
        n = c_idx - 1
        ws.cell(ufcf_rows["Discount Factor"], c_idx,
                f"=1/(1+$B$13)^{n}").font = Font(color=S.BLACK)
        ws.cell(ufcf_rows["Discount Factor"], c_idx).number_format = "0.0000"

        ws.cell(ufcf_rows["PV of UFCF"], c_idx,
                f"={col}{ufcf_rows['UFCF']}*{col}{ufcf_rows['Discount Factor']}").font = Font(color=S.BLACK)
        ws.cell(ufcf_rows["PV of UFCF"], c_idx).number_format = S.currency_format

    # ── Terminal Value (rows 28-35) ─────────────────────────────────────────
    ws.cell(28, 1, "TERMINAL VALUE").font = Font(bold=True, size=11)

    last_is_col = _col(1 + len(all_periods))
    tv_items = [
        ("Terminal Growth Rate (g)",    "='02_Assumptions'!E18",   29),
        ("Last Year UFCF",              f"={_col(1 + len(proj_periods))}{ufcf_rows['UFCF']}", 30),
        ("TV — Gordon Growth",          "=B30*(1+B29)/(B13-B29)", 31),
        ("Exit Multiple (EV/EBITDA)",   dcf.get("exit_multiple", 8.0), 32),
        ("Last Year EBITDA",            f"='03_Income_Statement'!{last_is_col}{11}", 33),
        ("TV — Exit Multiple",          "=B32*B33",               34),
        ("Selected TV (Gordon Growth)", "=B31",                   35),
    ]

    for label, val, r in tv_items:
        ws.cell(r, 1, label)
        c = ws.cell(r, 2, val)
        if isinstance(val, str) and val.startswith("="):
            c.font = Font(color=S.GREEN if "Assumptions" in val or "Income" in val else S.BLACK)
        else:
            c.font = Font(color=S.BLUE)
        if r not in (32,):
            c.number_format = S.currency_format
        else:
            c.number_format = "0.0x"

    # ── Enterprise & Equity Value (rows 37-42) ─────────────────────────────
    ws.cell(37, 1, "ENTERPRISE & EQUITY VALUE").font = Font(bold=True, size=11)

    n_proj = len(proj_periods)
    sum_pv_range = f"{_col(2)}{ufcf_rows['PV of UFCF']}:{_col(1+n_proj)}{ufcf_rows['PV of UFCF']}"

    ev_items = [
        ("Sum of PV of FCFs",   f"=SUM({sum_pv_range})",     38),
        ("PV of Terminal Value", f"=B35/(1+B13)^{n_proj}",   39),
        ("Enterprise Value (EV)", "=B38+B39",                 40),
        ("Less: Net Debt",       dcf.get("net_debt", 0),      41),
        ("Equity Value",         "=B40-B41",                  42),
        ("Shares Outstanding",   dcf.get("shares_outstanding", 1000000), 43),
        ("Price Per Share",      "=B42/B43",                  44),
    ]

    for label, val, r in ev_items:
        ws.cell(r, 1, label)
        c = ws.cell(r, 2, val)
        if isinstance(val, str) and val.startswith("="):
            c.font = Font(color=S.BLACK)
        else:
            c.font = Font(color=S.BLUE)
        c.number_format = S.currency_format

    # Scenario rows (for Exec Summary cross-sheet link)
    ws.cell(30, 5, "Base EV").font = Font(bold=True)
    ws.cell(31, 5, "Bull EV").font = Font(bold=True)
    ws.cell(32, 5, "Bear EV").font = Font(bold=True)
    for i, scen in enumerate(["Base", "Bull", "Bear"]):
        s_data = engine_output.get(scen, engine_output.get(scen.lower(), {}))
        dcf_s  = s_data.get("dcf", {})
        ws.cell(30 + i, 6, dcf_s.get("enterprise_value", "")).font = Font(color=S.BLUE)
        ws.cell(30 + i, 6).number_format = S.currency_format

    # ── 2D Sensitivity Matrix (rows 46-54) ─────────────────────────────────
    ws.cell(46, 1, "SENSITIVITY: Equity Value vs WACC × Terminal Growth Rate").font = Font(bold=True, size=11)

    wacc_steps = [-0.02, -0.01, 0, 0.01, 0.02]
    tgr_steps  = [-0.01, -0.005, 0, 0.005, 0.01]

    ws.cell(47, 1, "WACC \\ TGR →").font = Font(bold=True)
    for c_idx, step in enumerate(tgr_steps, 2):
        ws.cell(47, c_idx, f"TGR {step:+.1%}").font = Font(bold=True)
        ws.cell(47, c_idx).alignment = Alignment(horizontal="center")

    for r_idx, w_step in enumerate(wacc_steps):
        r = 48 + r_idx
        ws.cell(r, 1, f"WACC {w_step:+.1%}").font = Font(bold=True)
        for c_idx, t_step in enumerate(tgr_steps, 2):
            # Sensitivity formula: adjust WACC and TGR from base
            formula = (f"=(B38+(B35*(1+(B29+{t_step})))/((B13+{w_step})-(B29+{t_step}))/"
                       f"(1+(B13+{w_step}))^{n_proj})-B41")
            ws.cell(r, c_idx, formula).font = Font(color=S.BLACK)
            ws.cell(r, c_idx).number_format = S.currency_format

    ws.column_dimensions["A"].width = 36
    for c_idx in range(2, 12):
        ws.column_dimensions[_col(c_idx)].width = 16

    return ws
