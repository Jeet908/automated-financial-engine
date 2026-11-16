"""
Unit tests for 2D Sensitivity, Scenario Manager, and Monte Carlo simulation.
"""

from financial_engine.engine import FinancialEngine
from financial_engine.simulation.sensitivity import build_wacc_growth_sensitivity
from financial_engine.simulation.monte_carlo import run_monte_carlo_simulation


def test_sensitivity_dimensions_and_monotonicity():
    engine = FinancialEngine.from_template("kaveri_foods")
    model = engine.solve(run_mc=False)
    sens = model.sensitivity

    assert len(sens.row_values) == 5
    assert len(sens.col_values) == 5
    assert len(sens.matrix) == 5
    assert len(sens.matrix[0]) == 5

    # Check monotonicity: Higher growth -> Higher value per share
    for row in sens.matrix:
        for j in range(1, len(row)):
            assert row[j] >= row[j - 1]

    # Check monotonicity: Higher WACC -> Lower value per share
    for j in range(len(sens.col_values)):
        for i in range(1, len(sens.row_values)):
            assert sens.matrix[i][j] <= sens.matrix[i - 1][j]


def test_monte_carlo_distribution():
    engine = FinancialEngine.from_template("kaveri_foods")
    model = engine.solve(run_mc=False)
    dcf = model.dcf_result

    mc = run_monte_carlo_simulation(
        base_ebitda=model.income_statement.ebitda[2],
        fcff_base_list=dcf.fcff,
        base_debt=dcf.base_debt,
        base_cash=dcf.base_cash,
        shares_outstanding=dcf.shares_outstanding,
        base_wacc=dcf.wacc,
        base_growth=dcf.terminal_growth_rate,
        iterations=1000,
        seed=123,
    )

    assert mc.iterations == 1000
    assert mc.min_price < mc.pct_5 < mc.median_price < mc.pct_95 < mc.max_price
    assert 200 < mc.median_price < 350
    assert 0.0 <= mc.prob_undervalued <= 100.0
    assert len(mc.histogram_bins) == 26
    assert sum(mc.histogram_counts) == 1000
