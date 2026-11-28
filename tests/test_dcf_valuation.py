"""
Unit tests for DCF valuation, WACC, CAPM, and Hamada equations.
"""

import pytest
from financial_engine.valuation.wacc import (
    calculate_wacc,
    hamada_unlever_beta,
    hamada_relever_beta,
)
from financial_engine.core.types import ValuationInputs
from financial_engine.valuation.dcf import run_dcf_valuation
from financial_engine.core.exceptions import ValuationDivergenceError


def test_wacc_calculation():
    inputs = ValuationInputs(
        risk_free_rate=0.065,
        beta=0.90,
        equity_risk_premium=0.070,
        pretax_cost_of_debt=0.090,
        debt_weight=0.20,
    )
    res = calculate_wacc(inputs, marginal_tax_rate=0.2517)

    # Ke = 6.5% + 0.9 * 7% = 12.8%
    assert round(res.cost_of_equity, 4) == 0.1280
    # Kd_after = 9% * (1 - 0.2517) = 6.7347%
    assert round(res.after_tax_cost_of_debt, 4) == 0.0673
    # WACC = 0.8 * 12.8% + 0.2 * 6.7347% = 11.5869% (~11.6%)
    assert round(res.wacc, 4) == 0.1159


def test_hamada_relevering():
    # If beta_L = 1.2, D/E = 0.5, t = 0.25
    # beta_U = 1.2 / (1 + (1 - 0.25) * 0.5) = 1.2 / 1.375 = 0.8727
    b_u = hamada_unlever_beta(1.2, 0.5, 0.25)
    assert round(b_u, 4) == 0.8727

    # Relever with new D/E = 1.0
    # beta_L_new = 0.8727 * (1 + 0.75 * 1.0) = 1.5273
    b_l_new = hamada_relever_beta(b_u, 1.0, 0.25)
    assert round(b_l_new, 4) == 1.5273


def test_valuation_divergence_guard():
    inputs = ValuationInputs(
        risk_free_rate=0.02,
        beta=0.5,
        equity_risk_premium=0.04,
        pretax_cost_of_debt=0.03,
        debt_weight=0.5,
        terminal_growth_rate=0.08,  # WACC will be < 8%, causing divergence
    )
    with pytest.raises(ValuationDivergenceError):
        run_dcf_valuation(
            proj_ebit=[100.0] * 5,
            proj_ebitda=[120.0] * 5,
            proj_depreciation=[20.0] * 5,
            proj_capex=[20.0] * 5,
            proj_delta_nwc=[5.0] * 5,
            base_debt=50.0,
            base_cash=20.0,
            marginal_tax_rate=0.25,
            inputs=inputs,
        )
