"""
tab_02_assumptions.py
Build the Assumptions / Drivers sheet.
"""
from openpyxl.styles import Font, Alignment

from src.exporters.styles import ExcelStyles as S


def build_assumptions(wb, drivers: dict, scenarios: dict):
    """
    drivers  — dict of driver_name → {Base: val, Bull: val, Bear: val}
    scenarios— same structure (alias accepted)
    """
    ws = wb.create_sheet("02_Assumptions")

    # ── Title ─────────────────────────────────────────────────────────────
    ws["A1"] = "ASSUMPTIONS & DRIVERS"
    ws["A1"].font = Font(bold=True, size=14)
    ws.merge_cells("A1:F1")

    # ── Scenario switch ───────────────────────────────────────────────────
    ws["A2"] = "Active Scenario (1=Base, 2=Bull, 3=Bear)"
    ws["A2"].font = Font(bold=True)
    ws["B2"] = 1
    ws["B2"].font = Font(color=S.BLUE, bold=True)

    # ── Column headers ────────────────────────────────────────────────────
    row = 4
    headers = ["Driver", "Base", "Bull", "Bear", "Active (CHOOSE)"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row, c, h)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # ── Default drivers if not supplied ───────────────────────────────────
    default_drivers = {
        "Revenue Growth %":     {"Base": 0.10, "Bull": 0.18, "Bear": 0.04},
        "Gross Margin %":       {"Base": 0.45, "Bull": 0.50, "Bear": 0.38},
        "EBITDA Margin %":      {"Base": 0.20, "Bull": 0.26, "Bear": 0.13},
        "Employee Cost %":      {"Base": 0.15, "Bull": 0.13, "Bear": 0.18},
        "Other Opex %":         {"Base": 0.10, "Bull": 0.09, "Bear": 0.12},
        "D&A %":                {"Base": 0.03, "Bull": 0.03, "Bear": 0.04},
        "Interest Rate %":      {"Base": 0.08, "Bull": 0.07, "Bear": 0.09},
        "Tax Rate %":           {"Base": 0.25, "Bull": 0.24, "Bear": 0.26},
        "Dividend Payout %":    {"Base": 0.30, "Bull": 0.35, "Bear": 0.20},
        "Receivable Days":      {"Base": 45,   "Bull": 40,   "Bear": 55},
        "Inventory Days":       {"Base": 30,   "Bull": 25,   "Bear": 40},
        "Payable Days":         {"Base": 30,   "Bull": 35,   "Bear": 25},
        "CapEx % of Revenue":   {"Base": 0.05, "Bull": 0.04, "Bear": 0.07},
        "Terminal Growth Rate": {"Base": 0.03, "Bull": 0.04, "Bear": 0.02},
        "WACC":                 {"Base": 0.10, "Bull": 0.09, "Bear": 0.12},
    }

    all_drivers = default_drivers.copy()
    if isinstance(drivers, dict):
        all_drivers.update(drivers)
    elif hasattr(drivers, "__dataclass_fields__") or hasattr(drivers, "revenue_growth"):
        all_drivers["Revenue Growth %"]["Base"] = getattr(drivers, "revenue_growth", getattr(drivers, "revenue_cagr", 0.10))
        all_drivers["Gross Margin %"]["Base"] = getattr(drivers, "avg_gross_margin", 0.45)
        all_drivers["EBITDA Margin %"]["Base"] = getattr(drivers, "avg_ebitda_margin", 0.20)
        all_drivers["Receivable Days"]["Base"] = getattr(drivers, "dso_days", 45)
        all_drivers["Inventory Days"]["Base"] = getattr(drivers, "dii_days", 30)
        all_drivers["Payable Days"]["Base"] = getattr(drivers, "dpo_days", 30)
        all_drivers["Tax Rate %"]["Base"] = getattr(drivers, "effective_tax_rate", 0.25)
        all_drivers["CapEx % of Revenue"]["Base"] = getattr(drivers, "capex_intensity", 0.05)
        all_drivers["Interest Rate %"]["Base"] = getattr(drivers, "interest_rate", 0.08)
        all_drivers["Dividend Payout %"]["Base"] = getattr(drivers, "dividend_payout", 0.30)
    if isinstance(scenarios, dict):
        all_drivers.update(scenarios)

    is_pct_driver = lambda name: "%" in name or "rate" in name.lower() or "margin" in name.lower() or "payout" in name.lower() or "growth" in name.lower() or "wacc" in name.lower()

    for i, (driver_name, vals) in enumerate(all_drivers.items()):
        r = row + 1 + i
        base_val = vals.get("Base", vals.get("base", 0))
        bull_val = vals.get("Bull", vals.get("bull", 0))
        bear_val = vals.get("Bear", vals.get("bear", 0))

        # Column A: label
        ws.cell(r, 1, driver_name).font = Font(bold=False)

        # Columns B, C, D: hardcoded inputs (BLUE)
        for col, val in [(2, base_val), (3, bull_val), (4, bear_val)]:
            c = ws.cell(r, col, val)
            c.font = Font(color=S.BLUE)
            if is_pct_driver(driver_name):
                c.number_format = S.pct_format

        # Column E: CHOOSE formula (BLACK font)
        b_addr = f"B{r}"
        c_addr = f"C{r}"
        d_addr = f"D{r}"
        choose_cell = ws.cell(r, 5, f"=CHOOSE($B$2,{b_addr},{c_addr},{d_addr})")
        choose_cell.font = Font(color=S.BLACK)
        if is_pct_driver(driver_name):
            choose_cell.number_format = S.pct_format

    # ── Column widths ────────────────────────────────────────────────────
    ws.column_dimensions["A"].width = 28
    for col in ["B", "C", "D", "E"]:
        ws.column_dimensions[col].width = 16

    return ws
