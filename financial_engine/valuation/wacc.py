"""
WACC and CAPM Cost of Capital calculation engine with Hamada unlevering/relevering.
"""

from dataclasses import dataclass
from financial_engine.core.types import ValuationInputs


@dataclass
class WACCResult:
    """Detailed components and outputs of WACC and CAPM calculation."""
    risk_free_rate: float
    beta: float
    equity_risk_premium: float
    cost_of_equity: float
    pretax_cost_of_debt: float
    tax_rate: float
    after_tax_cost_of_debt: float
    debt_weight: float
    equity_weight: float
    wacc: float


def calculate_wacc(
    inputs: ValuationInputs,
    marginal_tax_rate: float,
    region: str | None = None,
    sector: str | None = None,
) -> WACCResult:
    """
    Computes Cost of Equity (CAPM), After-tax Cost of Debt, and WACC:
    Ke = Rf + Beta * ERP
    Kd_after = Kd * (1 - t)
    WACC = We * Ke + Wd * Kd_after
    Optionally enriches baseline inputs from the live SectorBenchmark store.
    """
    rf = inputs.risk_free_rate
    beta = inputs.beta
    erp = inputs.equity_risk_premium

    if region and sector and (rf <= 0 or erp <= 0):
        try:
            from src.mesh.regulatory_mesh import get_live_benchmark_multiples
            bench = get_live_benchmark_multiples(region, sector)
            if rf <= 0:
                rf = bench.get("risk_free_rate", rf)
            if erp <= 0:
                erp = bench.get("equity_risk_premium", erp)
        except Exception:
            pass

    ke = rf + beta * erp

    kd_pre = inputs.pretax_cost_of_debt
    kd_after = kd_pre * (1.0 - marginal_tax_rate)

    wd = inputs.debt_weight
    we = 1.0 - wd

    wacc = we * ke + wd * kd_after

    return WACCResult(
        risk_free_rate=rf,
        beta=beta,
        equity_risk_premium=erp,
        cost_of_equity=ke,
        pretax_cost_of_debt=kd_pre,
        tax_rate=marginal_tax_rate,
        after_tax_cost_of_debt=kd_after,
        debt_weight=wd,
        equity_weight=we,
        wacc=wacc,
    )


def hamada_unlever_beta(levered_beta: float, debt_to_equity: float, tax_rate: float) -> float:
    """Unlevers beta using Hamada's formula: Beta_U = Beta_L / (1 + (1 - t) * (D / E))."""
    return levered_beta / (1.0 + (1.0 - tax_rate) * debt_to_equity)


def hamada_relever_beta(unlevered_beta: float, target_debt_to_equity: float, tax_rate: float) -> float:
    """Relevers beta using Hamada's formula: Beta_L = Beta_U * (1 + (1 - t) * (D / E))."""
    return unlevered_beta * (1.0 + (1.0 - tax_rate) * target_debt_to_equity)
