import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from src.ingestion.live_web_scraper import LiveWebScraper
from financial_engine.core.config import ModelConfiguration
from financial_engine.engine import FinancialEngine
from financial_engine.reporting.html_dashboard import HTMLDashboardGenerator


def _fake_ticker():
    periods = pd.to_datetime(["2021-12-31", "2022-12-31", "2023-12-31", "2024-12-31"])
    income = pd.DataFrame(
        [
            [500e6, 550e6, 600e6, 650e6],
            [100e6, 110e6, 120e6, 130e6],
            [10e6, 11e6, 12e6, 13e6],
            [5e6, 5e6, 5e6, 5e6],
            [20e6, 22e6, 24e6, 26e6],
            [365e6, 402e6, 439e6, 476e6],
        ],
        index=[
            "Total Revenue",
            "Cost Of Revenue",
            "Depreciation And Amortization In Income Statement",
            "Interest Expense",
            "Tax Provision",
            "Net Income Common Stockholders",
        ],
        columns=periods,
    )
    balance = pd.DataFrame(
        [
            [1e9, 1.1e9, 1.2e9, 1.3e9],
            [300e6, 330e6, 360e6, 390e6],
            [700e6, 770e6, 840e6, 910e6],
            [100e6, 110e6, 120e6, 130e6],
            [100e6, 110e6, 120e6, 130e6],
            [100e6, 110e6, 120e6, 130e6],
            [700e6, 770e6, 840e6, 910e6],
            [50e6, 55e6, 60e6, 65e6],
            [40e6, 44e6, 48e6, 52e6],
            [10e6, 10e6, 10e6, 10e6],
            [690e6, 760e6, 830e6, 900e6],
        ],
        index=[
            "Total Assets",
            "Total Liabilities Net Minority Interest",
            "Total Equity Gross Minority Interest",
            "Cash And Cash Equivalents",
            "Accounts Receivable",
            "Inventory",
            "Net PPE",
            "Total Debt",
            "Accounts Payable",
            "Common Stock",
            "Retained Earnings",
        ],
        columns=periods,
    )
    cashflow = pd.DataFrame(
        [
            [350e6, 380e6, 410e6, 440e6],
            [-100e6, -110e6, -120e6, -130e6],
            [-200e6, -220e6, -240e6, -260e6],
            [-10e6, -11e6, -12e6, -13e6],
            [-20e6, -22e6, -24e6, -26e6],
        ],
        index=[
            "Operating Cash Flow",
            "Investing Cash Flow",
            "Financing Cash Flow",
            "Capital Expenditure",
            "Cash Dividends Paid",
        ],
        columns=periods,
    )
    return SimpleNamespace(
        info={
            "longName": "Live Example Corporation",
            "currency": "USD",
            "exchange": "NYQ",
            "industry": "Technology",
            "sector": "Technology",
            "currentPrice": 20.0,
            "sharesOutstanding": 1e9,
            "marketCap": 20e9,
            "beta": 1.1,
        },
        income_stmt=income,
        balance_sheet=balance,
        cashflow=cashflow,
    )


def test_extraction_uses_live_quote_and_common_annual_periods(monkeypatch):
    ticker = _fake_ticker()
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda symbol: ticker),
    )
    candidate = {
        "ticker": "EXAMPLE",
        "name": "Example Corporation",
        "industry": "Technology",
        "risk_free_rate": 0.04,
        "equity_risk_premium": 0.05,
        "terminal_growth_rate": 0.025,
        "exit_multiple_ev_ebitda": 15.0,
        "beta": 1.0,
    }

    company = LiveWebScraper._extract_live_company(candidate)
    config = LiveWebScraper()._build_engine_config(company)

    assert company["name"] == "Live Example Corporation"
    assert company["current_market_price"] == 20.0
    assert company["shares_outstanding"] == 1.0
    assert company["market_cap"] == 20.0
    assert company["years"] == ["FY21A", "FY22A", "FY23A", "FY24A"]
    assert company["historicals"]["revenue"] == [0.5, 0.55, 0.6, 0.65]
    assert company["historicals"]["operating_cash_flow"] == [0.35, 0.38, 0.41, 0.44]
    assert config["valuation_inputs"]["current_market_price"] == 20.0
    assert config["historicals"]["net_fixed_assets"][-1] == pytest.approx(0.91)
    model = FinancialEngine(ModelConfiguration.from_dict(config)).solve(run_mc=True, mc_iterations=20)
    assert model.audit_certificate.is_valid
    assert all(check.max_discrepancy == 0.0 for check in model.audit_certificate.checks)
    dashboard = HTMLDashboardGenerator(model).render()
    assert 'aria-label="Monte Carlo distribution of simulated share prices"' in dashboard
    assert "Monte Carlo Price Distribution (20 simulations)" in dashboard
    assert dashboard.count("<rect") == 25


def test_extraction_rejects_fewer_than_four_common_statement_years(monkeypatch):
    ticker = _fake_ticker()
    ticker.income_stmt = ticker.income_stmt.iloc[:, -3:]
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        SimpleNamespace(Ticker=lambda symbol: ticker),
    )

    with pytest.raises(ValueError, match="at least 4"):
        LiveWebScraper._extract_live_company({"ticker": "EXAMPLE"})
