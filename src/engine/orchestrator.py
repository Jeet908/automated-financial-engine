"""
orchestrator.py — ModelOrchestrator: end-to-end pipeline from input to EngineOutput.

Accepts either:
  (a) A NormalizedFinancials Pydantic object (from src.ingestion.normalizer), or
  (b) The legacy financial_engine.core.types dataclasses, or
  (c) A plain dict of historical financials.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Union


def _to_hist_dict(data: Any) -> dict:
    """Convert various input types to a plain hist dict."""
    # Already a dict
    if isinstance(data, dict):
        return data

    # Try NormalizedFinancials (Pydantic model)
    try:
        from src.ingestion.normalizer import NormalizedFinancials
        if isinstance(data, NormalizedFinancials):
            return {
                "revenue": data.revenue,
                "cogs": data.cogs,
                "gross_profit": data.gross_profit,
                "ebitda": data.ebitda,
                "depreciation": data.depreciation,
                "ebit": data.ebit,
                "interest": data.interest,
                "pbt": data.pbt,
                "tax": data.tax,
                "pat": data.pat,
                "cash": data.cash,
                "receivables": data.receivables,
                "inventory": data.inventory,
                "net_fixed_assets": data.net_fixed_assets,
                "other_assets": data.other_assets or [],
                "payables": data.payables,
                "debt": data.debt,
                "other_liabilities": data.other_liabilities or [],
                "share_capital": data.share_capital,
                "retained_earnings": data.retained_earnings,
                "total_equity": data.total_equity,
                "total_liab_equity": data.total_liab_equity,
                "cfo": data.cfo,
                "cfi": data.cfi,
                "cff": data.cff,
                "capex": data.capex or [],
                "dividends": data.dividends or [],
                "periods": data.periods or [],
                "is_startup": data.is_startup,
            }
    except ImportError:
        pass

    # Try legacy HistoricalFinancials dataclass
    try:
        from financial_engine.core.types import HistoricalFinancials
        if isinstance(data, HistoricalFinancials):
            return {
                "revenue": data.revenue,
                "cogs": data.cogs,
                "depreciation": data.depreciation,
                "interest": data.interest,
                "tax": data.tax,
                "cash": data.cash,
                "receivables": data.receivables,
                "inventory": data.inventory,
                "net_fixed_assets": data.net_fixed_assets,
                "payables": data.payables,
                "debt": data.debt,
                "share_capital": data.share_capital,
                "retained_earnings": data.retained_earnings,
                "dividends": data.dividends,
                "capex": [],
                "is_startup": False,
            }
    except ImportError:
        pass

    raise TypeError(f"Unsupported input type: {type(data)}")


class ModelOrchestrator:
    """Orchestrates the full 3-statement + DCF pipeline for all scenarios."""

    def __init__(self):
        from src.engine.drivers import DriverCalibrator
        from src.engine.model3s import ThreeStatementModel
        from src.engine.dcf import DCFEngine
        from src.engine.startup import StartupMetrics

        self.calibrator = DriverCalibrator()
        self.model3s = ThreeStatementModel()
        self.dcf_engine = DCFEngine()
        self.startup = StartupMetrics()

    def run(
        self,
        normalized_financials_or_hist: Any,
        scenarios: List[str] = None,
        n_years: int = 5,
        valuation_inputs: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Run the full engine pipeline.

        Parameters
        ----------
        normalized_financials_or_hist : NormalizedFinancials | HistoricalFinancials | dict
        scenarios : list of scenario names (default: ["Base", "Bull", "Bear"])
        n_years : projection horizon in years
        valuation_inputs : ValuationInputs dataclass or dict (optional)

        Returns
        -------
        EngineOutput: dict keyed by scenario name, each value is a dict with:
            model_output, dcf_results, startup_metrics (if applicable), drivers
        """
        if scenarios is None:
            scenarios = ["Base", "Bull", "Bear"]

        hist = _to_hist_dict(normalized_financials_or_hist)
        is_startup = hist.get("is_startup", False)

        # Calibrate drivers
        base_drivers = self.calibrator.calibrate(hist)
        all_scenarios = self.calibrator.generate_scenarios(base_drivers)

        # Valuation inputs (defaults)
        if valuation_inputs is None:
            vi = {
                "risk_free_rate": 0.065,
                "beta": 0.90,
                "equity_risk_premium": 0.070,
                "pretax_cost_of_debt": 0.090,
                "debt_weight": 0.20,
                "terminal_growth_rate": 0.050,
                "shares_outstanding": 10.0,
                "exit_multiple_ev_ebitda": 8.0,
            }
        elif isinstance(valuation_inputs, dict):
            vi = valuation_inputs
        else:
            # Try dataclass
            vi = {
                "risk_free_rate": getattr(valuation_inputs, "risk_free_rate", 0.065),
                "beta": getattr(valuation_inputs, "beta", 0.90),
                "equity_risk_premium": getattr(valuation_inputs, "equity_risk_premium", 0.070),
                "pretax_cost_of_debt": getattr(valuation_inputs, "pretax_cost_of_debt", 0.090),
                "debt_weight": getattr(valuation_inputs, "debt_weight", 0.20),
                "terminal_growth_rate": getattr(valuation_inputs, "terminal_growth_rate", 0.050),
                "shares_outstanding": getattr(valuation_inputs, "shares_outstanding", 10.0),
                "exit_multiple_ev_ebitda": getattr(valuation_inputs, "exit_multiple_ev_ebitda", 8.0),
            }

        engine_output = {}

        for scenario_name in scenarios:
            if scenario_name not in all_scenarios:
                continue
            drivers = all_scenarios[scenario_name]

            # Build 3-statement model
            model_output = self.model3s.build(hist, drivers, scenario=scenario_name, n_years=n_years)

            # DCF
            wacc = self.dcf_engine.compute_wacc(
                equity_risk_premium=vi["equity_risk_premium"],
                beta=vi["beta"],
                risk_free=vi["risk_free_rate"],
                pretax_cod=vi["pretax_cost_of_debt"],
                tax_rate=drivers.effective_tax_rate,
                debt_weight=vi["debt_weight"],
            )
            ufcf = self.dcf_engine.compute_ufcf(model_output)
            tgr = vi["terminal_growth_rate"]
            ebitda_terminal = model_output.is_ebitda[-1] if model_output.is_ebitda else None
            tv = self.dcf_engine.compute_terminal_value(
                ufcf, wacc, tgr,
                exit_multiple=vi["exit_multiple_ev_ebitda"],
                ebitda_terminal=ebitda_terminal,
                method="gordon",
            )
            net_debt = (model_output.bs_debt[0] if model_output.bs_debt else 0.0) - (model_output.bs_cash[0] if model_output.bs_cash else 0.0)
            dcf_results = self.dcf_engine.compute_dcf(
                ufcf, tv, wacc,
                periods=model_output.periods,
                shares=vi["shares_outstanding"],
                net_debt=max(net_debt, 0.0),
            )

            # Sensitivity matrices
            wacc_range = [round(wacc - 0.02 + i * 0.01, 4) for i in range(5)]
            tgr_range = [round(tgr - 0.01 + i * 0.005, 4) for i in range(5)]
            sensitivity = self.dcf_engine.sensitivity_matrix(ufcf, tv, wacc_range, tgr_range)

            # Startup metrics
            startup_metrics = None
            if is_startup:
                startup_data = {
                    "arr_series": hist.get("arr_series", hist.get("revenue", [])),
                    "mrr_series": hist.get("mrr_series", [r / 12.0 for r in hist.get("revenue", [])]),
                    "cash_balance": (hist.get("cash") or [0.0])[-1],
                    "monthly_burn": abs((hist.get("cfo") or [0.0])[-1]) / 12.0,
                    "gross_margin": drivers.avg_gross_margin,
                    "churn_rate": hist.get("churn_rate", 0.02),
                    "new_customers": hist.get("new_customers", 1),
                    "total_customers": hist.get("total_customers", 1),
                    "sales_marketing_spend": hist.get("sales_marketing_spend", 0.0),
                    "expansion_arr": hist.get("expansion_arr", 0.0),
                    "churned_arr": hist.get("churned_arr", 0.0),
                }
                startup_metrics = self.startup.compute(startup_data)

            engine_output[scenario_name] = {
                "drivers": drivers,
                "model_output": model_output,
                "wacc": wacc,
                "ufcf": ufcf,
                "terminal_value": tv,
                "dcf_results": dcf_results,
                "sensitivity_wacc_tgr": sensitivity,
                "startup_metrics": startup_metrics,
            }

        return engine_output
