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


def test_pain_points_diagnostic():
    from financial_engine.reporting.pain_points import diagnose

    sample_model_data = {
        "revenue": [1000.0, 1150.0],
        "cogs": [600.0, 680.0],
        "ebitda": [220.0, 260.0],
        "ebit": [170.0, 205.0],
        "sga": [180.0, 210.0],
        "accounts_receivable": [120.0, 140.0],
        "inventory": [90.0, 105.0],
        "accounts_payable": [80.0, 95.0],
        "total_debt": [150.0, 120.0],
        "total_equity": [450.0, 520.0],
        "tax_rate": [0.25],
        "enterprise_value": 2400.0,
    }

    report = diagnose(sample_model_data, wacc=0.10)
    data = report.to_dict()

    assert "ccc" in data
    assert "margin" in data
    assert "roic" in data
    assert report.ccc.dso > 0
    assert report.ccc.dio > 0
    assert report.ccc.dpo > 0
    assert report.ccc.ccc_days > 0
    assert report.margin.ebitda_margin > 0
    assert report.margin.target_ebitda_margin > report.margin.ebitda_margin
    assert report.roic.roic_pct > 0
    assert report.overall_health_score >= 0.0
    assert len(report.top_recommendation) > 0


def test_regional_accounting_rulebook():
    from financial_engine.core.accounting import RegionalAccountingRulebook

    us_rule = RegionalAccountingRulebook.detect_jurisdiction(currency="USD")
    assert us_rule.standard == "US GAAP"
    assert us_rule.revenue_standard == "ASC 606"

    in_rule = RegionalAccountingRulebook.detect_jurisdiction(currency="INR", exchange="NSE")
    assert in_rule.standard == "Ind AS"
    assert in_rule.fiscal_year_end_month == 3
    assert in_rule.currency_symbol == "₹"

    eu_rule = RegionalAccountingRulebook.detect_jurisdiction(currency="EUR", exchange="LSE")
    assert eu_rule.standard == "IFRS / IASB"
    assert eu_rule.lease_standard.startswith("IFRS 16")


def test_saas_plan_catalog():
    from src.portal.plans import plan_catalog

    catalog = plan_catalog()
    assert "free_trial" in catalog
    assert "free" in catalog
    assert "pro" in catalog
    assert "business" in catalog
    assert catalog["free_trial"]["trial_days"] == 14
    assert catalog["free_trial"]["monthly_valuations"] >= 5
    assert catalog["pro"]["prices"]["USD"] == 49
    assert catalog["business"]["prices"]["USD"] == 199

