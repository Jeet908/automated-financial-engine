"""
workbook_compiler.py
WorkbookCompiler compiles an institutional-grade .xlsx model using openpyxl.
"""
import os
import openpyxl

from src.exporters.styles import ExcelStyles
from src.exporters.tabs.tab_01_exec_summary import build_exec_summary
from src.exporters.tabs.tab_02_assumptions import build_assumptions
from src.exporters.tabs.tab_03_income_statement import build_income_statement
from src.exporters.tabs.tab_04_balance_sheet import build_balance_sheet
from src.exporters.tabs.tab_05_cash_flow import build_cash_flow
from src.exporters.tabs.tab_06_schedules import build_schedules
from src.exporters.tabs.tab_07_dcf import build_dcf
from src.exporters.tabs.tab_08_raw_data import build_raw_data


def _prepare_output(engine_output: dict, normalized_financials) -> dict:
    if hasattr(normalized_financials, "model_dump"):
        data = normalized_financials.model_dump()
    elif hasattr(normalized_financials, "dict"):
        data = normalized_financials.dict()
    elif isinstance(normalized_financials, dict):
        data = normalized_financials
    else:
        data = {}

    hist_periods = data.get("periods", [])

    # Ensure historical gross_profit, EBITDA, and PAT exist in data if not directly provided
    if not data.get("gross_profit"):
        rev_h = data.get("revenue", [])
        cogs_h = data.get("cogs", [0.0] * len(rev_h))
        if rev_h and cogs_h:
            data["gross_profit"] = [r - c for r, c in zip(rev_h, cogs_h)]

    if not data.get("ebitda"):
        rev_h = data.get("revenue", [])
        cogs_h = data.get("cogs", [0.0] * len(rev_h))
        emp_h = data.get("employee_costs", [0.0] * len(rev_h))
        opex_h = data.get("other_opex", [0.0] * len(rev_h))
        if rev_h:
            data["ebitda"] = [r - c - e - o for r, c, e, o in zip(rev_h, cogs_h, emp_h, opex_h)]

    if not data.get("pat") and not data.get("net_income"):
        rev_h = data.get("revenue", [])
        dep_h = data.get("depreciation", [0.0] * len(rev_h))
        int_h = data.get("interest", [0.0] * len(rev_h))
        tax_h = data.get("tax", [0.0] * len(rev_h))
        eb_h = data.get("ebitda", [0.0] * len(rev_h))
        if eb_h:
            data["pat"] = [eb - d - i - t for eb, d, i, t in zip(eb_h, dep_h, int_h, tax_h)]

    for s_name, s_data in list(engine_output.items()):
        if not isinstance(s_data, dict):
            continue
        mo = s_data.get("model_output")
        proj_periods = mo.periods if mo and hasattr(mo, "periods") else []

        if not s_data.get("income_statement"):
            is_dict = {}
            for k, proj_attr in [
                ("revenue", "is_revenue"),
                ("cogs", "is_cogs"),
                ("gross_profit", "is_gross_profit"),
                ("ebitda", "is_ebitda"),
                ("depreciation", "is_depreciation"),
                ("ebit", "is_ebit"),
                ("interest", "is_interest"),
                ("pbt", "is_pbt"),
                ("tax", "is_tax"),
                ("pat", "is_pat"),
            ]:
                hist_vals = data.get(k, [])
                proj_vals = getattr(mo, proj_attr, []) if mo else []
                d = {p: (hist_vals[i] if i < len(hist_vals) else 0) for i, p in enumerate(hist_periods)}
                for i, p in enumerate(proj_periods):
                    d[p] = proj_vals[i] if i < len(proj_vals) else 0
                is_dict[k] = d

            for k in ["employee_costs", "other_opex"]:
                hist_vals = data.get(k, [])
                is_dict[k] = {p: (hist_vals[i] if i < len(hist_vals) else 0) for i, p in enumerate(hist_periods)}

            s_data["income_statement"] = is_dict

        if not s_data.get("balance_sheet"):
            bs_dict = {}
            for k, proj_attr in [
                ("cash", "bs_cash"),
                ("receivables", "bs_receivables"),
                ("inventory", "bs_inventory"),
                ("net_fixed_assets", "bs_nfa"),
                ("other_assets", "bs_other_assets"),
                ("payables", "bs_payables"),
                ("debt", "bs_debt"),
                ("other_liabilities", "bs_other_liabilities"),
                ("share_capital", "bs_share_capital"),
                ("retained_earnings", "bs_retained_earnings"),
            ]:
                hist_vals = data.get(k, [])
                proj_vals = getattr(mo, proj_attr, []) if mo else []
                d = {p: (hist_vals[i] if i < len(hist_vals) else 0) for i, p in enumerate(hist_periods)}
                for i, p in enumerate(proj_periods):
                    d[p] = proj_vals[i] if i < len(proj_vals) else 0
                bs_dict[k] = d

            capex_hist = data.get("capex", [])
            bs_dict["capex"] = {p: (capex_hist[i] if i < len(capex_hist) else 0) for i, p in enumerate(hist_periods)}
            s_data["balance_sheet"] = bs_dict

        if not s_data.get("cash_flow"):
            cf_dict = {}
            for k, proj_attr in [
                ("cfo", "cf_cfo"),
                ("cfi", "cf_cfi"),
                ("cff", "cf_cff"),
            ]:
                hist_vals = data.get(k, [])
                proj_vals = getattr(mo, proj_attr, []) if mo else []
                d = {p: (hist_vals[i] if i < len(hist_vals) else 0) for i, p in enumerate(hist_periods)}
                for i, p in enumerate(proj_periods):
                    d[p] = proj_vals[i] if i < len(proj_vals) else 0
                cf_dict[k] = d
            s_data["cash_flow"] = cf_dict

        if not s_data.get("dcf"):
            dcf_res = s_data.get("dcf_results") or {}
            dcf_dict = dict(dcf_res) if isinstance(dcf_res, dict) else {}
            dcf_dict["wacc"] = s_data.get("wacc", 0.10)
            dcf_dict["terminal_value"] = s_data.get("terminal_value", 0.0)
            s_data["dcf"] = dcf_dict

    return engine_output


class WorkbookCompiler:
    def __init__(self):
        pass

    def compile(self, engine_output: dict, normalized_financials, metadata: dict, output_path: str) -> str:
        """
        Compiles the 8-tab institutional financial model workbook.
        
        engine_output: dict keyed by scenario (e.g. Base, Bull, Bear)
        normalized_financials: NormalizedFinancials model or dict
        metadata: company metadata dict
        output_path: path to save .xlsx
        
        Returns output_path
        """
        wb = openpyxl.Workbook()
        # Remove default sheet
        default_sheet = wb.active

        # Ensure engine_output has all expected structures
        engine_output = _prepare_output(engine_output, normalized_financials)
        
        # Extract drivers / scenarios if present
        base_scenario = engine_output.get("Base", engine_output.get("base", {}))
        bull_scenario = engine_output.get("Bull", engine_output.get("bull", {}))
        bear_scenario = engine_output.get("Bear", engine_output.get("bear", {}))

        drivers = base_scenario.get("drivers", {})
        scenarios = engine_output.get("scenarios")

        if not scenarios:
            bull_d = bull_scenario.get("drivers")
            bear_d = bear_scenario.get("drivers")
            if bull_d or bear_d:
                scenarios = {
                    "Revenue Growth %": {
                        "Bull": getattr(bull_d, "revenue_growth", getattr(bull_d, "revenue_cagr", 0.18)),
                        "Bear": getattr(bear_d, "revenue_growth", getattr(bear_d, "revenue_cagr", 0.04)),
                    },
                    "Gross Margin %": {
                        "Bull": getattr(bull_d, "avg_gross_margin", 0.50),
                        "Bear": getattr(bear_d, "avg_gross_margin", 0.38),
                    },
                    "EBITDA Margin %": {
                        "Bull": getattr(bull_d, "avg_ebitda_margin", 0.26),
                        "Bear": getattr(bear_d, "avg_ebitda_margin", 0.13),
                    },
                    "Receivable Days": {
                        "Bull": getattr(bull_d, "dso_days", 40),
                        "Bear": getattr(bear_d, "dso_days", 55),
                    },
                    "Inventory Days": {
                        "Bull": getattr(bull_d, "dii_days", 25),
                        "Bear": getattr(bear_d, "dii_days", 40),
                    },
                    "Payable Days": {
                        "Bull": getattr(bull_d, "dpo_days", 35),
                        "Bear": getattr(bear_d, "dpo_days", 25),
                    },
                    "CapEx % of Revenue": {
                        "Bull": getattr(bull_d, "capex_intensity", 0.04),
                        "Bear": getattr(bear_d, "capex_intensity", 0.07),
                    },
                    "Tax Rate %": {
                        "Bull": getattr(bull_d, "effective_tax_rate", 0.24),
                        "Bear": getattr(bear_d, "effective_tax_rate", 0.26),
                    },
                    "Interest Rate %": {
                        "Bull": getattr(bull_d, "interest_rate", 0.07),
                        "Bear": getattr(bear_d, "interest_rate", 0.09),
                    },
                    "Dividend Payout %": {
                        "Bull": getattr(bull_d, "dividend_payout", 0.35),
                        "Bear": getattr(bear_d, "dividend_payout", 0.20),
                    },
                }

        # Build tabs in order
        build_exec_summary(wb, engine_output, metadata or {})
        build_assumptions(wb, drivers, scenarios)
        build_income_statement(wb, engine_output)
        build_balance_sheet(wb, engine_output)
        build_cash_flow(wb, engine_output)
        build_schedules(wb, engine_output)
        build_dcf(wb, engine_output)
        build_raw_data(wb, normalized_financials)

        # Remove the initial default sheet
        if default_sheet in wb.worksheets:
            wb.remove(default_sheet)

        # Freeze panes on row 2, column B for all sheets (cell B2)
        for ws in wb.worksheets:
            ws.freeze_panes = "B2"

        # Ensure output directory exists
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        wb.save(output_path)
        return output_path
