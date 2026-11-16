"""
Monte Carlo Stochastic Valuation Engine.
Simulates parameter uncertainty over 10,000 iterations to compute confidence intervals and VaR.
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class MonteCarloStats:
    iterations: int
    mean_price: float
    median_price: float
    std_dev: float
    min_price: float
    max_price: float
    pct_5: float   # 95% Value-at-Risk boundary
    pct_10: float
    pct_25: float
    pct_75: float
    pct_90: float
    pct_95: float
    prob_undervalued: float  # Prob(Fair Value > Market Price)
    histogram_bins: List[float] = field(default_factory=list)
    histogram_counts: List[int] = field(default_factory=list)


def run_monte_carlo_simulation(
    base_ebitda: float,
    fcff_base_list: List[float],
    base_debt: float,
    base_cash: float,
    shares_outstanding: float,
    base_wacc: float,
    base_growth: float,
    current_market_price: Optional[float] = None,
    iterations: int = 10000,
    seed: int = 42,
) -> MonteCarloStats:
    """
    Executes stochastic valuation simulation:
    WACC ~ Normal(base_wacc, sigma_wacc)
    Terminal Growth ~ Normal(base_growth, sigma_g)
    FCFF Shock ~ Normal(1.0, sigma_fcff)
    """
    random.seed(seed)
    n_proj = len(fcff_base_list)
    prices: List[float] = []

    sigma_wacc = 0.0075      # 75 bps std dev on WACC
    sigma_growth = 0.0050    # 50 bps std dev on terminal growth
    sigma_fcff = 0.0800      # 8% std dev on annual cash flows

    for _ in range(iterations):
        # Sample stochastic parameters
        w = random.gauss(base_wacc, sigma_wacc)
        g = random.gauss(base_growth, sigma_growth)

        # Ensure mathematical boundaries
        w = max(0.04, min(0.25, w))
        g = max(0.01, min(w - 0.01, g))  # Enforce w > g by at least 100 bps

        # Perturb cash flow trajectory
        sim_fcff = []
        for cf in fcff_base_list:
            shock = random.gauss(1.0, sigma_fcff)
            sim_fcff.append(cf * shock)

        # Discount FCFF
        pv_fcff_sum = sum(sim_fcff[t] / ((1.0 + w) ** (t + 1)) for t in range(n_proj))

        # Terminal Value
        tv = sim_fcff[-1] * (1.0 + g) / (w - g)
        pv_tv = tv / ((1.0 + w) ** n_proj)

        ev = pv_fcff_sum + pv_tv
        equity = ev - base_debt + base_cash
        price = max(0.0, equity / shares_outstanding)

        prices.append(price)

    prices.sort()
    n = len(prices)
    mean_val = sum(prices) / n
    var_val = sum((p - mean_val) ** 2 for p in prices) / (n - 1)
    std_val = math.sqrt(var_val)

    def _get_pct(p):
        idx = int((n - 1) * p)
        return prices[idx]

    market_p = current_market_price or mean_val
    undervalued_count = sum(1 for p in prices if p > market_p)
    prob_undervalued = (undervalued_count / n) * 100.0

    # Build 25 histogram bins
    num_bins = 25
    min_p = prices[0]
    max_p = prices[-1]
    bin_width = (max_p - min_p) / num_bins if max_p > min_p else 1.0
    bins = [min_p + i * bin_width for i in range(num_bins + 1)]
    counts = [0] * num_bins

    for p in prices:
        idx = min(int((p - min_p) / bin_width), num_bins - 1)
        counts[idx] += 1

    return MonteCarloStats(
        iterations=iterations,
        mean_price=mean_val,
        median_price=_get_pct(0.50),
        std_dev=std_val,
        min_price=min_p,
        max_price=max_p,
        pct_5=_get_pct(0.05),
        pct_10=_get_pct(0.10),
        pct_25=_get_pct(0.25),
        pct_75=_get_pct(0.75),
        pct_90=_get_pct(0.90),
        pct_95=_get_pct(0.95),
        prob_undervalued=prob_undervalued,
        histogram_bins=bins,
        histogram_counts=counts,
    )
