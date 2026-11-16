"""
Advanced Financial & Valuation Analytics Engine:
ROIC, Economic Spread, Economic Value Added (EVA), DuPont 5-Way Decomposition, and Football Field Valuation Ranges.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ROICAnalysis:
    """Return on Invested Capital and Economic Value Added (EVA) trajectory."""
    years: List[str]
    invested_capital: List[float]
    nopat: List[float]
    roic: List[float]
    wacc: float
    economic_spread: List[float]  # ROIC - WACC
    eva: List[float]               # Economic Spread * Invested Capital


@dataclass
class DuPont5WayAnalysis:
    """Institutional 5-way DuPont ROE decomposition across projection horizons."""
    years: List[str]
    operating_margin: List[float]   # EBIT / Revenue
    asset_turnover: List[float]     # Revenue / Total Assets
    interest_burden: List[float]    # PBT / EBIT
    tax_retention: List[float]      # PAT / PBT
    financial_leverage: List[float] # Total Assets / Total Equity
    roe: List[float]                # PAT / Total Equity


@dataclass
class FootballFieldRange:
    """Valuation range band for institutional football field chart."""
    method: str
    min_val: float
    median_val: float
    max_val: float
    notes: str


def compute_roic_and_eva(
    years: List[str],
    ebit_list: List[float],
    tax_rate: float,
    debt_list: List[float],
    equity_list: List[float],
    cash_list: List[float],
    wacc: float,
) -> ROICAnalysis:
    """
    Computes Return on Invested Capital (ROIC) and Economic Value Added (EVA):
    Invested Capital = Total Debt + Total Equity - Cash
    NOPAT = EBIT * (1 - tax_rate)
    ROIC = NOPAT / Invested Capital
    Economic Spread = ROIC - WACC
    EVA = Economic Spread * Invested Capital
    """
    n = len(years)
    ic_list: List[float] = []
    nopat_list: List[float] = []
    roic_list: List[float] = []
    spread_list: List[float] = []
    eva_list: List[float] = []

    for i in range(n):
        ic = max(1e-6, debt_list[i] + equity_list[i] - cash_list[i])
        nopat = ebit_list[i] * (1.0 - tax_rate)
        roic_val = nopat / ic
        spread = roic_val - wacc
        eva_val = spread * ic

        ic_list.append(ic)
        nopat_list.append(nopat)
        roic_list.append(roic_val)
        spread_list.append(spread)
        eva_list.append(eva_val)

    return ROICAnalysis(
        years=years,
        invested_capital=ic_list,
        nopat=nopat_list,
        roic=roic_list,
        wacc=wacc,
        economic_spread=spread_list,
        eva=eva_list,
    )


def compute_dupont_5way(
    years: List[str],
    revenue_list: List[float],
    ebit_list: List[float],
    pbt_list: List[float],
    pat_list: List[float],
    assets_list: List[float],
    equity_list: List[float],
) -> DuPont5WayAnalysis:
    """
    Decomposes Return on Equity (ROE) into five distinct financial drivers:
    ROE = Operating Margin * Asset Turnover * Interest Burden * Tax Retention * Leverage
        = (EBIT/Rev) * (Rev/Assets) * (PBT/EBIT) * (PAT/PBT) * (Assets/Equity)
    """
    n = len(years)
    op_margin: List[float] = []
    at_list: List[float] = []
    int_burden: List[float] = []
    tax_ret: List[float] = []
    lev_list: List[float] = []
    roe_list: List[float] = []

    for i in range(n):
        rev = max(1e-6, revenue_list[i])
        ebit = max(1e-6, ebit_list[i])
        pbt = max(1e-6, pbt_list[i])
        assets = max(1e-6, assets_list[i])
        equity = max(1e-6, equity_list[i])
        pat = pat_list[i]

        op_m = ebit / rev
        at = rev / assets
        ib = pbt / ebit
        tr = pat / pbt
        lev = assets / equity
        roe = pat / equity

        op_margin.append(op_m)
        at_list.append(at)
        int_burden.append(ib)
        tax_ret.append(tr)
        lev_list.append(lev)
        roe_list.append(roe)

    return DuPont5WayAnalysis(
        years=years,
        operating_margin=op_margin,
        asset_turnover=at_list,
        interest_burden=int_burden,
        tax_retention=tax_ret,
        financial_leverage=lev_list,
        roe=roe_list,
    )


def build_football_field(
    dcf_base_price: float,
    dcf_exit_multiple_price: Optional[float],
    comps_median_price: float,
    lbo_price: float,
    current_market_price: float,
    mc_pct_5: float,
    mc_pct_95: float,
) -> List[FootballFieldRange]:
    """Generates institutional valuation bands across methodologies."""
    bands = [
        FootballFieldRange(
            method="52-Week Market Range",
            min_val=current_market_price * 0.85,
            median_val=current_market_price,
            max_val=current_market_price * 1.20,
            notes="Secondary market liquidity and trading history",
        ),
        FootballFieldRange(
            method="DCF: Gordon Perpetuity (FCFF)",
            min_val=dcf_base_price * 0.88,
            median_val=dcf_base_price,
            max_val=dcf_base_price * 1.15,
            notes="Intrinsic unlevered DCF baseline with Gordon growth",
        ),
        FootballFieldRange(
            method="Trading Multiples (Comps EV/EBITDA)",
            min_val=comps_median_price * 0.80,
            median_val=comps_median_price,
            max_val=comps_median_price * 1.25,
            notes="Peer comps multiple 25th-75th percentile band",
        ),
        FootballFieldRange(
            method="PE Sponsor LBO Floor (IRR > 18%)",
            min_val=lbo_price * 0.90,
            median_val=lbo_price,
            max_val=lbo_price * 1.10,
            notes="Financial sponsor maximum acquisition purchase price",
        ),
        FootballFieldRange(
            method="Monte Carlo Stochastic Range (90% CI)",
            min_val=mc_pct_5,
            median_val=(mc_pct_5 + mc_pct_95) / 2.0,
            max_val=mc_pct_95,
            notes="10,000-path stochastic parameter simulation confidence band",
        ),
    ]
    return bands
