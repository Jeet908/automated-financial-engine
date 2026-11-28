"""
Configuration loading and management for financial modeling scenarios and datasets.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from financial_engine.core.types import (
    CompanyMetadata,
    HistoricalFinancials,
    ProjectionAssumptions,
    ValuationInputs,
    Currency,
)


class ModelConfiguration:
    """Encapsulates all metadata, historicals, assumptions, and valuation inputs."""

    def __init__(
        self,
        metadata: Optional[CompanyMetadata] = None,
        historicals: Optional[HistoricalFinancials] = None,
        assumptions: Optional[ProjectionAssumptions] = None,
        valuation_inputs: Optional[ValuationInputs] = None,
    ):
        self.metadata = metadata or CompanyMetadata()
        self.historicals = historicals or HistoricalFinancials()
        self.assumptions = assumptions or ProjectionAssumptions()
        self.valuation_inputs = valuation_inputs or ValuationInputs()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelConfiguration":
        meta_dict = data.get("metadata", {})
        metadata = CompanyMetadata(
            name=meta_dict.get("name", "Target Company"),
            ticker=meta_dict.get("ticker", "TGT"),
            industry=meta_dict.get("industry", "General"),
            currency=Currency(meta_dict.get("currency", "INR")),
            currency_unit=meta_dict.get("currency_unit", "INR crore"),
            shares_unit=meta_dict.get("shares_unit", "crore"),
            historical_years=meta_dict.get("historical_years", ["FY23A", "FY24A", "FY25A"]),
            projection_years=meta_dict.get("projection_years", ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"]),
            description=meta_dict.get("description", ""),
        )

        hist_dict = data.get("historicals", {})
        historicals = HistoricalFinancials(
            revenue=hist_dict.get("revenue", [1000.0, 1120.0, 1243.2]),
            cogs=hist_dict.get("cogs", [585.0, 649.6, 716.1]),
            employee_costs=hist_dict.get("employee_costs", [100.0, 109.8, 120.6]),
            other_expenses=hist_dict.get("other_expenses", [122.0, 134.4, 147.9]),
            depreciation=hist_dict.get("depreciation", [38.0, 40.0, 43.0]),
            interest=hist_dict.get("interest", [28.4, 25.7, 23.0]),
            tax=hist_dict.get("tax", [31.9, 40.4, 48.5]),
            dividends=hist_dict.get("dividends", [23.7, 30.0, 36.0]),
            cash=hist_dict.get("cash", [222.8, 239.8, 269.5]),
            receivables=hist_dict.get("receivables", [123.3, 138.1, 153.3]),
            inventory=hist_dict.get("inventory", [80.1, 89.0, 98.1]),
            net_fixed_assets=hist_dict.get("net_fixed_assets", [400.0, 430.0, 465.0]),
            payables=hist_dict.get("payables", [96.2, 106.8, 117.7]),
            debt=hist_dict.get("debt", [300.0, 270.0, 240.0]),
            share_capital=hist_dict.get("share_capital", [50.0, 50.0, 50.0]),
            retained_earnings=hist_dict.get("retained_earnings", [380.0, 470.1, 578.2]),
        )

        assump_dict = data.get("assumptions", {})
        assumptions = ProjectionAssumptions(
            revenue_growth=assump_dict.get("revenue_growth", [0.12, 0.11, 0.10, 0.09, 0.08]),
            cogs_pct_revenue=assump_dict.get("cogs_pct_revenue", None),
            employee_pct_revenue=assump_dict.get("employee_pct_revenue", [0.097] * 5),
            other_opex_pct_revenue=assump_dict.get("other_opex_pct_revenue", [0.119] * 5),
            receivable_days=assump_dict.get("receivable_days", [45.0] * 5),
            inventory_days=assump_dict.get("inventory_days", [50.0] * 5),
            payable_days=assump_dict.get("payable_days", [60.0] * 5),
            capex_pct_revenue=assump_dict.get("capex_pct_revenue", [0.05] * 5),
            depreciation_pct_opening_nb=assump_dict.get("depreciation_pct_opening_nb", [0.10] * 5),
            interest_rate=assump_dict.get("interest_rate", [0.09] * 5),
            debt_repayment=assump_dict.get("debt_repayment", [30.0] * 5),
            tax_rate=assump_dict.get("tax_rate", [0.2517] * 5),
            dividend_payout=assump_dict.get("dividend_payout", [0.25] * 5),
        )

        val_dict = data.get("valuation_inputs", {})
        valuation_inputs = ValuationInputs(
            risk_free_rate=val_dict.get("risk_free_rate", 0.065),
            beta=val_dict.get("beta", 0.90),
            equity_risk_premium=val_dict.get("equity_risk_premium", 0.070),
            pretax_cost_of_debt=val_dict.get("pretax_cost_of_debt", 0.090),
            debt_weight=val_dict.get("debt_weight", 0.20),
            terminal_growth_rate=val_dict.get("terminal_growth_rate", 0.050),
            shares_outstanding=val_dict.get("shares_outstanding", 10.0),
            exit_multiple_ev_ebitda=val_dict.get("exit_multiple_ev_ebitda", 8.0),
            current_market_price=val_dict.get("current_market_price", 210.0),
        )

        return cls(
            metadata=metadata,
            historicals=historicals,
            assumptions=assumptions,
            valuation_inputs=valuation_inputs,
        )

    @classmethod
    def from_json_file(cls, path: str) -> "ModelConfiguration":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": {
                "name": self.metadata.name,
                "ticker": self.metadata.ticker,
                "industry": self.metadata.industry,
                "currency": self.metadata.currency.value,
                "currency_unit": self.metadata.currency_unit,
                "shares_unit": self.metadata.shares_unit,
                "historical_years": self.metadata.historical_years,
                "projection_years": self.metadata.projection_years,
                "description": self.metadata.description,
            },
            "historicals": {
                "revenue": self.historicals.revenue,
                "cogs": self.historicals.cogs,
                "employee_costs": self.historicals.employee_costs,
                "other_expenses": self.historicals.other_expenses,
                "depreciation": self.historicals.depreciation,
                "interest": self.historicals.interest,
                "tax": self.historicals.tax,
                "dividends": self.historicals.dividends,
                "cash": self.historicals.cash,
                "receivables": self.historicals.receivables,
                "inventory": self.historicals.inventory,
                "net_fixed_assets": self.historicals.net_fixed_assets,
                "payables": self.historicals.payables,
                "debt": self.historicals.debt,
                "share_capital": self.historicals.share_capital,
                "retained_earnings": self.historicals.retained_earnings,
            },
            "assumptions": {
                "revenue_growth": self.assumptions.revenue_growth,
                "cogs_pct_revenue": self.assumptions.cogs_pct_revenue,
                "employee_pct_revenue": self.assumptions.employee_pct_revenue,
                "other_opex_pct_revenue": self.assumptions.other_opex_pct_revenue,
                "receivable_days": self.assumptions.receivable_days,
                "inventory_days": self.assumptions.inventory_days,
                "payable_days": self.assumptions.payable_days,
                "capex_pct_revenue": self.assumptions.capex_pct_revenue,
                "depreciation_pct_opening_nb": self.assumptions.depreciation_pct_opening_nb,
                "interest_rate": self.assumptions.interest_rate,
                "debt_repayment": self.assumptions.debt_repayment,
                "tax_rate": self.assumptions.tax_rate,
                "dividend_payout": self.assumptions.dividend_payout,
            },
            "valuation_inputs": {
                "risk_free_rate": self.valuation_inputs.risk_free_rate,
                "beta": self.valuation_inputs.beta,
                "equity_risk_premium": self.valuation_inputs.equity_risk_premium,
                "pretax_cost_of_debt": self.valuation_inputs.pretax_cost_of_debt,
                "debt_weight": self.valuation_inputs.debt_weight,
                "terminal_growth_rate": self.valuation_inputs.terminal_growth_rate,
                "shares_outstanding": self.valuation_inputs.shares_outstanding,
                "exit_multiple_ev_ebitda": self.valuation_inputs.exit_multiple_ev_ebitda,
                "current_market_price": self.valuation_inputs.current_market_price,
            },
        }

    def save_json_file(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
