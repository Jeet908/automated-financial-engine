"""
Core types, enumerations, and dataclasses for the Automated Financial Modeling & Valuation Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any


class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class ScenarioType(str, Enum):
    BASE = "Base Case"
    BULL = "Bull Case"
    BEAR = "Bear Case"


class TerminalValueMethod(str, Enum):
    GORDON_GROWTH = "Gordon Growth (Perpetuity)"
    EXIT_MULTIPLE = "Exit Multiple (EV/EBITDA)"
    HYBRID = "Hybrid (Gordon + Multiple Average)"


@dataclass
class CompanyMetadata:
    """Metadata describing the target company and model horizon."""
    name: str = "Kaveri Foods Ltd"
    ticker: str = "KAVERI"
    industry: str = "Packaged Foods & Consumer Staples"
    currency: Currency = Currency.INR
    currency_unit: str = "INR crore"
    shares_unit: str = "crore"
    historical_years: List[str] = field(default_factory=lambda: ["FY23A", "FY24A", "FY25A"])
    projection_years: List[str] = field(default_factory=lambda: ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"])
    description: str = "Indian packaged-foods company model"


@dataclass
class HistoricalFinancials:
    """Raw historical financial data across the historical horizon."""
    # Income Statement items
    revenue: List[float] = field(default_factory=lambda: [1000.0, 1120.0, 1243.2])
    cogs: List[float] = field(default_factory=lambda: [585.0, 649.6, 716.1])
    employee_costs: List[float] = field(default_factory=lambda: [100.0, 109.8, 120.6])
    other_expenses: List[float] = field(default_factory=lambda: [122.0, 134.4, 147.9])
    depreciation: List[float] = field(default_factory=lambda: [38.0, 40.0, 43.0])
    interest: List[float] = field(default_factory=lambda: [28.4, 25.7, 23.0])
    tax: List[float] = field(default_factory=lambda: [31.9, 40.4, 48.5])
    dividends: List[float] = field(default_factory=lambda: [23.7, 30.0, 36.0])

    # Balance Sheet items
    cash: List[float] = field(default_factory=lambda: [222.8, 239.8, 269.5])
    receivables: List[float] = field(default_factory=lambda: [123.3, 138.1, 153.3])
    inventory: List[float] = field(default_factory=lambda: [80.1, 89.0, 98.1])
    net_fixed_assets: List[float] = field(default_factory=lambda: [400.0, 430.0, 465.0])
    payables: List[float] = field(default_factory=lambda: [96.2, 106.8, 117.7])
    debt: List[float] = field(default_factory=lambda: [300.0, 270.0, 240.0])
    share_capital: List[float] = field(default_factory=lambda: [50.0, 50.0, 50.0])
    retained_earnings: List[float] = field(default_factory=lambda: [380.0, 470.1, 578.2])


@dataclass
class ProjectionAssumptions:
    """Projection drivers and operational assumptions."""
    revenue_growth: List[float] = field(default_factory=lambda: [0.12, 0.11, 0.10, 0.09, 0.08])
    cogs_pct_revenue: Optional[List[float]] = None  # If None, computed as 1 - 3yr avg gross margin
    employee_pct_revenue: List[float] = field(default_factory=lambda: [0.097, 0.097, 0.097, 0.097, 0.097])
    other_opex_pct_revenue: List[float] = field(default_factory=lambda: [0.119, 0.119, 0.119, 0.119, 0.119])
    
    # Working capital drivers (in days)
    receivable_days: List[float] = field(default_factory=lambda: [45.0, 45.0, 45.0, 45.0, 45.0])
    inventory_days: List[float] = field(default_factory=lambda: [50.0, 50.0, 50.0, 50.0, 50.0])
    payable_days: List[float] = field(default_factory=lambda: [60.0, 60.0, 60.0, 60.0, 60.0])
    
    # Capital expenditure & depreciation
    capex_pct_revenue: List[float] = field(default_factory=lambda: [0.05, 0.05, 0.05, 0.05, 0.05])
    depreciation_pct_opening_nb: List[float] = field(default_factory=lambda: [0.10, 0.10, 0.10, 0.10, 0.10])
    
    # Financing & tax
    interest_rate: List[float] = field(default_factory=lambda: [0.09, 0.09, 0.09, 0.09, 0.09])
    debt_repayment: List[float] = field(default_factory=lambda: [30.0, 30.0, 30.0, 30.0, 30.0])
    tax_rate: List[float] = field(default_factory=lambda: [0.2517, 0.2517, 0.2517, 0.2517, 0.2517])
    dividend_payout: List[float] = field(default_factory=lambda: [0.25, 0.25, 0.25, 0.25, 0.25])


@dataclass
class ValuationInputs:
    """Valuation parameters and market data."""
    risk_free_rate: float = 0.065          # 6.5% (10Y G-Sec / Treasury)
    beta: float = 0.90                     # Equity Beta
    equity_risk_premium: float = 0.070     # 7.0% ERP
    pretax_cost_of_debt: float = 0.090     # 9.0%
    debt_weight: float = 0.20              # 20.0% D/V
    terminal_growth_rate: float = 0.050    # 5.0%
    shares_outstanding: float = 10.0       # 10.0 crore shares
    exit_multiple_ev_ebitda: float = 8.0   # 8.0x EV/EBITDA
    current_market_price: Optional[float] = 210.0  # Optional current price for upside calculation
