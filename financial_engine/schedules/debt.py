"""
Debt Schedule: Opening Debt, Scheduled Repayments, Closing Debt, and Interest on Average Debt.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class DebtSchedule:
    """Debt schedule and roll-forward across projection periods."""
    opening_debt: List[float] = field(default_factory=list)
    repayment: List[float] = field(default_factory=list)
    closing_debt: List[float] = field(default_factory=list)
    average_debt: List[float] = field(default_factory=list)
    interest_expense: List[float] = field(default_factory=list)


def build_debt_schedule(
    hist_debt: List[float],
    proj_repayment: List[float],
    proj_interest_rate: List[float],
) -> DebtSchedule:
    """
    Rolls forward Debt:
    Closing(t) = Opening(t) - Repayment(t)
    Average(t) = (Opening(t) + Closing(t)) / 2
    Interest(t) = Average(t) * Interest_Rate(t)
    """
    n_proj = len(proj_repayment)
    opening_list: List[float] = []
    repay_list: List[float] = []
    closing_list: List[float] = []
    avg_list: List[float] = []
    interest_list: List[float] = []

    last_closing = hist_debt[-1]

    for i in range(n_proj):
        open_val = last_closing
        repay_val = proj_repayment[i]
        close_val = max(0.0, open_val - repay_val)
        avg_val = (open_val + close_val) / 2.0
        int_val = avg_val * proj_interest_rate[i]

        opening_list.append(open_val)
        repay_list.append(repay_val)
        closing_list.append(close_val)
        avg_list.append(avg_val)
        interest_list.append(int_val)

        last_closing = close_val

    return DebtSchedule(
        opening_debt=opening_list,
        repayment=repay_list,
        closing_debt=closing_list,
        average_debt=avg_list,
        interest_expense=interest_list,
    )
