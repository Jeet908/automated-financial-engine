"""
Unit tests for Advanced Financial Metrics: ROIC, EVA, 5-Way DuPont, and Football Field Ranges.
"""

from financial_engine.valuation.advanced_metrics import (
    compute_roic_and_eva,
    compute_dupont_5way,
    build_football_field,
)


def test_roic_and_eva_computation():
    years = ["FY26E", "FY27E"]
    ebit = [100.0, 120.0]
    tax_rate = 0.25
    debt = [50.0, 40.0]
    equity = [200.0, 250.0]
    cash = [30.0, 40.0]
    wacc = 0.10

    res = compute_roic_and_eva(years, ebit, tax_rate, debt, equity, cash, wacc)

    # FY26 Invested Capital = 50 + 200 - 30 = 220
    assert abs(res.invested_capital[0] - 220.0) < 1e-4
    # FY26 NOPAT = 100 * (1 - 0.25) = 75.0
    assert abs(res.nopat[0] - 75.0) < 1e-4
    # FY26 ROIC = 75 / 220 = 0.3409
    assert abs(res.roic[0] - (75.0 / 220.0)) < 1e-4
    # FY26 Economic Spread = ROIC - WACC = 0.3409 - 0.10 = 0.2409
    assert abs(res.economic_spread[0] - (75.0 / 220.0 - 0.10)) < 1e-4
    # FY26 EVA = Spread * Invested Capital = (75/220 - 0.10) * 220 = 75 - 22 = 53.0
    assert abs(res.eva[0] - 53.0) < 1e-4


def test_dupont_5way_reconciliation():
    years = ["FY26E"]
    rev = [1000.0]
    ebit = [200.0]
    pbt = [180.0]
    pat = [135.0]
    assets = [800.0]
    equity = [500.0]

    dupont = compute_dupont_5way(years, rev, ebit, pbt, pat, assets, equity)

    # ROE = PAT / Equity = 135 / 500 = 0.27 (27%)
    expected_roe = 135.0 / 500.0
    assert abs(dupont.roe[0] - expected_roe) < 1e-4

    # Product of the 5 factors must identically equal ROE
    product_of_5 = (
        dupont.operating_margin[0]
        * dupont.asset_turnover[0]
        * dupont.interest_burden[0]
        * dupont.tax_retention[0]
        * dupont.financial_leverage[0]
    )
    assert abs(product_of_5 - expected_roe) < 1e-6


def test_football_field_bands():
    bands = build_football_field(
        dcf_base_price=250.0,
        dcf_exit_multiple_price=260.0,
        comps_median_price=245.0,
        lbo_price=230.0,
        current_market_price=210.0,
        mc_pct_5=190.0,
        mc_pct_95=310.0,
    )
    assert len(bands) == 5
    for b in bands:
        assert b.min_val <= b.median_val <= b.max_val
