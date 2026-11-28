"""
Balance Sheet model and self-balancing identity verification.
"""

from dataclasses import dataclass, field
from typing import List
from financial_engine.core.types import HistoricalFinancials


@dataclass
class BalanceSheet:
    """Consolidated Balance Sheet across historical and projection horizons."""
    # Assets
    cash: List[float] = field(default_factory=list)
    receivables: List[float] = field(default_factory=list)
    inventory: List[float] = field(default_factory=list)
    net_fixed_assets: List[float] = field(default_factory=list)
    total_assets: List[float] = field(default_factory=list)

    # Liabilities & Equity
    payables: List[float] = field(default_factory=list)
    debt: List[float] = field(default_factory=list)
    share_capital: List[float] = field(default_factory=list)
    retained_earnings: List[float] = field(default_factory=list)
    total_liabilities_equity: List[float] = field(default_factory=list)

    # Invariant Check (Assets - L&E)
    balance_check: List[float] = field(default_factory=list)

    @property
    def total_debt(self) -> List[float]:
        return self.debt

    @property
    def total_liabilities_and_equity(self) -> List[float]:
        return self.total_liabilities_equity

    @property
    def total_equity(self) -> List[float]:
        n = min(len(self.share_capital), len(self.retained_earnings))
        return [self.share_capital[i] + self.retained_earnings[i] for i in range(n)]


def build_balance_sheet(
    historicals: HistoricalFinancials,
    proj_cash: List[float],
    proj_receivables: List[float],
    proj_inventory: List[float],
    proj_net_fixed_assets: List[float],
    proj_payables: List[float],
    proj_debt: List[float],
    proj_share_capital: List[float],
    proj_retained_earnings: List[float],
) -> BalanceSheet:
    """Builds the Balance Sheet across all years and computes the balance check."""
    all_cash = list(historicals.cash) + list(proj_cash)
    all_ar = list(historicals.receivables) + list(proj_receivables)
    all_inv = list(historicals.inventory) + list(proj_inventory)
    all_nfa = list(historicals.net_fixed_assets) + list(proj_net_fixed_assets)

    all_assets = [all_cash[i] + all_ar[i] + all_inv[i] + all_nfa[i] for i in range(len(all_cash))]

    all_ap = list(historicals.payables) + list(proj_payables)
    all_debt = list(historicals.debt) + list(proj_debt)
    all_sc = list(historicals.share_capital) + list(proj_share_capital)
    all_re = list(historicals.retained_earnings) + list(proj_retained_earnings)

    all_le = [all_ap[i] + all_debt[i] + all_sc[i] + all_re[i] for i in range(len(all_ap))]

    checks = [all_assets[i] - all_le[i] for i in range(len(all_assets))]

    return BalanceSheet(
        cash=all_cash,
        receivables=all_ar,
        inventory=all_inv,
        net_fixed_assets=all_nfa,
        total_assets=all_assets,
        payables=all_ap,
        debt=all_debt,
        share_capital=all_sc,
        retained_earnings=all_re,
        total_liabilities_equity=all_le,
        balance_check=checks,
    )
