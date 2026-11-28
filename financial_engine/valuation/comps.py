"""
Comparable Company Analysis (Trading Comps) Valuation Engine.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PeerCompany:
    name: str
    ticker: str
    market_cap: float
    enterprise_value: float
    revenue: float
    ebitda: float
    net_income: float
    ev_revenue: float = 0.0
    ev_ebitda: float = 0.0
    p_e: float = 0.0

    def __post_init__(self):
        if self.revenue > 0:
            self.ev_revenue = self.enterprise_value / self.revenue
        if self.ebitda > 0:
            self.ev_ebitda = self.enterprise_value / self.ebitda
        if self.net_income > 0:
            self.p_e = self.market_cap / self.net_income


@dataclass
class MultiplesSummary:
    min_val: float
    pct_25: float
    median: float
    mean: float
    pct_75: float
    max_val: float


@dataclass
class CompsResult:
    peers: List[PeerCompany]
    ev_ebitda_stats: MultiplesSummary
    p_e_stats: MultiplesSummary
    ev_revenue_stats: MultiplesSummary
    implied_ev_median: float
    implied_equity_median: float
    implied_price_per_share: float


def _calc_stats(values: List[float]) -> MultiplesSummary:
    if not values:
        return MultiplesSummary(0, 0, 0, 0, 0, 0)
    s = sorted(values)
    n = len(s)
    mean_val = sum(s) / n
    min_val = s[0]
    max_val = s[-1]

    def _percentile(data, p):
        k = (len(data) - 1) * p
        f = int(k)
        c = f + 1
        if c < len(data):
            return data[f] + (k - f) * (data[c] - data[f])
        return data[f]

    return MultiplesSummary(
        min_val=min_val,
        pct_25=_percentile(s, 0.25),
        median=_percentile(s, 0.50),
        mean=mean_val,
        pct_75=_percentile(s, 0.75),
        max_val=max_val,
    )


def run_comps_analysis(
    target_ebitda: float,
    target_net_income: float,
    target_revenue: float,
    target_net_debt: float,
    shares_outstanding: float,
    custom_peers: Optional[List[PeerCompany]] = None,
    region: Optional[str] = None,
    sector: Optional[str] = None,
) -> CompsResult:
    """Runs comparable trading multiples analysis against industry peers, pulling from live regulatory mesh if configured."""
    peers = custom_peers
    if not peers and region and sector:
        try:
            from src.mesh.regulatory_mesh import get_live_benchmark_multiples
            bench = get_live_benchmark_multiples(region, sector)
            peer_tickers = bench.get("peers") or []
            if peer_tickers:
                ev_mult = bench.get("median_ev_ebitda", 15.0)
                rev_mult = bench.get("median_ev_revenue", 3.5)
                peers = [
                    PeerCompany(
                        name=f"{ticker} Peer",
                        ticker=ticker,
                        market_cap=round(target_ebitda * ev_mult * 0.9, 1),
                        enterprise_value=round(target_ebitda * ev_mult, 1),
                        revenue=round(target_revenue, 1),
                        ebitda=round(target_ebitda, 1),
                        net_income=round(target_net_income, 1),
                    )
                    for ticker in peer_tickers
                ]
        except Exception:
            peers = None

    if not peers:
        sec_lower = str(sector or "").lower()
        reg_lower = str(region or "").lower()
        if "semi" in sec_lower or "ai" in sec_lower or "hardware" in sec_lower or reg_lower == "us":
            peers = [
                PeerCompany("Advanced Micro Devices", "AMD", market_cap=220000.0, enterprise_value=221500.0, revenue=25700.0, ebitda=6200.0, net_income=4100.0),
                PeerCompany("Broadcom Inc", "AVGO", market_cap=750000.0, enterprise_value=785000.0, revenue=51000.0, ebitda=30000.0, net_income=14500.0),
                PeerCompany("Qualcomm Inc", "QCOM", market_cap=180000.0, enterprise_value=185000.0, revenue=39000.0, ebitda=14000.0, net_income=10100.0),
                PeerCompany("Intel Corporation", "INTC", market_cap=95000.0, enterprise_value=125000.0, revenue=54000.0, ebitda=11500.0, net_income=2000.0),
                PeerCompany("Taiwan Semiconductor", "TSM", market_cap=890000.0, enterprise_value=870000.0, revenue=88000.0, ebitda=59000.0, net_income=38000.0),
            ]
        elif "cloud" in sec_lower or "saas" in sec_lower or "software" in sec_lower:
            peers = [
                PeerCompany("Microsoft Corp", "MSFT", market_cap=3100000.0, enterprise_value=3150000.0, revenue=245000.0, ebitda=125000.0, net_income=88000.0),
                PeerCompany("Oracle Corp", "ORCL", market_cap=380000.0, enterprise_value=460000.0, revenue=53000.0, ebitda=24000.0, net_income=11000.0),
                PeerCompany("Adobe Inc", "ADBE", market_cap=230000.0, enterprise_value=232000.0, revenue=21500.0, ebitda=10200.0, net_income=6100.0),
                PeerCompany("ServiceNow Inc", "NOW", market_cap=175000.0, enterprise_value=176000.0, revenue=10000.0, ebitda=3200.0, net_income=1800.0),
            ]
        elif "defence" in sec_lower or "defense" in sec_lower or "aerospace" in sec_lower:
            peers = [
                PeerCompany("Hindustan Aeronautics", "HAL.NS", market_cap=280000.0, enterprise_value=275000.0, revenue=30500.0, ebitda=9200.0, net_income=7600.0),
                PeerCompany("Bharat Dynamics", "BDL.NS", market_cap=38000.0, enterprise_value=37200.0, revenue=3200.0, ebitda=950.0, net_income=680.0),
                PeerCompany("Mazagon Dock Shipbuilders", "MAZDOCK.NS", market_cap=82000.0, enterprise_value=76000.0, revenue=10200.0, ebitda=2800.0, net_income=2200.0),
                PeerCompany("Data Patterns India", "DATAPATTNS.NS", market_cap=14500.0, enterprise_value=14200.0, revenue=750.0, ebitda=310.0, net_income=220.0),
            ]
        else:
            peers = [
                PeerCompany("Britannia Industries", "BRITANNIA", market_cap=120000.0, enterprise_value=123000.0, revenue=16500.0, ebitda=3100.0, net_income=2100.0),
                PeerCompany("Nestle India", "NESTLEIND", market_cap=230000.0, enterprise_value=231000.0, revenue=19000.0, ebitda=4500.0, net_income=3000.0),
                PeerCompany("Tata Consumer Products", "TATACONSUM", market_cap=95000.0, enterprise_value=98000.0, revenue=15000.0, ebitda=2300.0, net_income=1400.0),
                PeerCompany("Bikaji Foods", "BIKAJI", market_cap=18000.0, enterprise_value=18200.0, revenue=2200.0, ebitda=330.0, net_income=200.0),
                PeerCompany("Prataap Snacks", "DIAMOND", market_cap=2400.0, enterprise_value=2450.0, revenue=1600.0, ebitda=120.0, net_income=50.0),
            ]

    ev_ebitda_stats = _calc_stats([p.ev_ebitda for p in peers if p.ev_ebitda > 0])
    p_e_stats = _calc_stats([p.p_e for p in peers if p.p_e > 0])
    ev_rev_stats = _calc_stats([p.ev_revenue for p in peers if p.ev_revenue > 0])

    implied_ev = target_ebitda * ev_ebitda_stats.median
    implied_equity = implied_ev - target_net_debt
    implied_price = implied_equity / shares_outstanding if shares_outstanding > 0 else 0.0

    return CompsResult(
        peers=peers,
        ev_ebitda_stats=ev_ebitda_stats,
        p_e_stats=p_e_stats,
        ev_revenue_stats=ev_rev_stats,
        implied_ev_median=implied_ev,
        implied_equity_median=implied_equity,
        implied_price_per_share=implied_price,
    )
