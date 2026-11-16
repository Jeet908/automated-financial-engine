"""
Equity Schedule: Share Capital and Retained Earnings Roll-Forward.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class EquitySchedule:
    """Equity roll-forward across projection periods."""
    share_capital: List[float] = field(default_factory=list)
    opening_retained_earnings: List[float] = field(default_factory=list)
    net_profit_addition: List[float] = field(default_factory=list)
    dividends_deduction: List[float] = field(default_factory=list)
    closing_retained_earnings: List[float] = field(default_factory=list)
    total_equity: List[float] = field(default_factory=list)


def build_equity_schedule(
    hist_share_capital: List[float],
    hist_retained_earnings: List[float],
    proj_net_profit: List[float],
    proj_dividends: List[float],
) -> EquitySchedule:
    """
    Rolls forward Retained Earnings:
    Closing RE(t) = Opening RE(t) + PAT(t) - Dividends(t)
    where Opening RE(t) = Closing RE(t-1)
    """
    n_proj = len(proj_net_profit)
    sc_val = hist_share_capital[-1]
    share_cap = [sc_val] * n_proj

    opening_re: List[float] = []
    closing_re: List[float] = []
    tot_equity: List[float] = []

    last_closing = hist_retained_earnings[-1]

    for i in range(n_proj):
        open_val = last_closing
        pat_val = proj_net_profit[i]
        div_val = proj_dividends[i]
        close_val = open_val + pat_val - div_val

        opening_re.append(open_val)
        closing_re.append(close_val)
        tot_equity.append(share_cap[i] + close_val)

        last_closing = close_val

    return EquitySchedule(
        share_capital=share_cap,
        opening_retained_earnings=opening_re,
        net_profit_addition=list(proj_net_profit),
        dividends_deduction=list(proj_dividends),
        closing_retained_earnings=closing_re,
        total_equity=tot_equity,
    )
