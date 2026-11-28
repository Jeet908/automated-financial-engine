"""
Cash Flow Statement: Operating, Investing, and Financing activities, and Cash Roll-Forward.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CashFlowStatement:
    """Cash Flow Statement for projection years and cash roll-forward."""
    # Operating Activities
    net_profit: List[float] = field(default_factory=list)
    depreciation_addback: List[float] = field(default_factory=list)
    change_in_nwc: List[float] = field(default_factory=list)  # As negative / deduction
    cash_from_operations: List[float] = field(default_factory=list)

    # Investing Activities
    capex: List[float] = field(default_factory=list)  # As negative / cash outflow
    cash_from_investing: List[float] = field(default_factory=list)

    # Financing Activities
    debt_repayment: List[float] = field(default_factory=list)  # As negative / cash outflow
    dividends_paid: List[float] = field(default_factory=list)  # As negative / cash outflow
    cash_from_financing: List[float] = field(default_factory=list)

    # Net Cash & Reconciliation
    net_change_in_cash: List[float] = field(default_factory=list)
    opening_cash: List[float] = field(default_factory=list)
    closing_cash: List[float] = field(default_factory=list)

    @property
    def cf_operations(self) -> List[float]:
        return self.cash_from_operations

    @property
    def cf_investing(self) -> List[float]:
        return self.cash_from_investing

    @property
    def cf_financing(self) -> List[float]:
        return self.cash_from_financing

    @property
    def ending_cash(self) -> List[float]:
        return self.closing_cash

    @property
    def operating_cash_flow(self) -> List[float]:
        return self.cash_from_operations


def build_cash_flow_statement(
    base_cash: float,
    proj_net_profit: List[float],
    proj_depreciation: List[float],
    proj_delta_nwc: List[float],
    proj_capex: List[float],
    proj_debt_repayment: List[float],
    proj_dividends: List[float],
) -> CashFlowStatement:
    """
    Constructs the Cash Flow Statement:
    CFO = PAT + Depreciation - ΔNWC
    CFI = -Capex
    CFF = -Repayment - Dividends
    Net Change = CFO + CFI + CFF
    Closing Cash = Opening Cash + Net Change
    """
    n_proj = len(proj_net_profit)

    cfo_list: List[float] = []
    cfi_list: List[float] = []
    cff_list: List[float] = []
    net_change_list: List[float] = []
    opening_cash_list: List[float] = []
    closing_cash_list: List[float] = []

    # Store negative signs for cash outflows in accordance with financial presentation
    cf_delta_nwc = [-d for d in proj_delta_nwc]
    cf_capex = [-c for c in proj_capex]
    cf_repayment = [-r for r in proj_debt_repayment]
    cf_dividends = [-d for d in proj_dividends]

    current_open_cash = base_cash

    for i in range(n_proj):
        pat_val = proj_net_profit[i]
        depr_val = proj_depreciation[i]
        nwc_sub = cf_delta_nwc[i]
        cfo_val = pat_val + depr_val + nwc_sub

        cfi_val = cf_capex[i]

        cff_val = cf_repayment[i] + cf_dividends[i]

        net_change = cfo_val + cfi_val + cff_val
        closing_cash = current_open_cash + net_change

        cfo_list.append(cfo_val)
        cfi_list.append(cfi_val)
        cff_list.append(cff_val)
        net_change_list.append(net_change)
        opening_cash_list.append(current_open_cash)
        closing_cash_list.append(closing_cash)

        current_open_cash = closing_cash

    return CashFlowStatement(
        net_profit=list(proj_net_profit),
        depreciation_addback=list(proj_depreciation),
        change_in_nwc=cf_delta_nwc,
        cash_from_operations=cfo_list,
        capex=cf_capex,
        cash_from_investing=cfi_list,
        debt_repayment=cf_repayment,
        dividends_paid=cf_dividends,
        net_change_in_cash=net_change_list,
        opening_cash=opening_cash_list,
        closing_cash=closing_cash_list,
    )
