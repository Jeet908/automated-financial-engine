"""
Leveraged Buyout (LBO) Quick Screening & Sponsor Returns Engine.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class LBOResult:
    entry_enterprise_value: float
    entry_debt_pct: float
    entry_debt: float
    sponsor_equity_invested: float
    exit_enterprise_value: float
    debt_paid_down: float
    exit_debt_remaining: float
    exit_sponsor_equity: float
    moic: float
    irr: float
    holding_period_years: int


def run_lbo_screening(
    base_ebitda: float,
    exit_ebitda: float,
    fcff_cash_generated: float,
    entry_multiple: float = 7.5,
    exit_multiple: float = 7.5,
    debt_leverage_ratio: float = 0.50,
    holding_period: int = 5,
) -> LBOResult:
    """
    Evaluates private equity sponsor returns:
    Entry EV = Entry Multiple * Base EBITDA
    Entry Debt = Entry EV * Debt %
    Sponsor Equity = Entry EV - Entry Debt
    Debt Paydown = min(Total FCF generated, Entry Debt)
    Exit Debt = Entry Debt - Debt Paydown
    Exit EV = Exit Multiple * Exit EBITDA
    Exit Equity = Exit EV - Exit Debt
    MoIC = Exit Equity / Sponsor Equity Invested
    IRR = MoIC ^ (1 / holding_period) - 1
    """
    entry_ev = entry_multiple * base_ebitda
    entry_debt = entry_ev * debt_leverage_ratio
    sponsor_equity = entry_ev - entry_debt

    debt_paydown = min(entry_debt, max(0.0, fcff_cash_generated * 0.70))  # 70% cash sweep
    exit_debt = entry_debt - debt_paydown
    exit_ev = exit_multiple * exit_ebitda
    exit_equity = exit_ev - exit_debt

    moic = exit_equity / sponsor_equity if sponsor_equity > 0 else 0.0
    irr = (moic ** (1.0 / holding_period)) - 1.0 if moic > 0 else -1.0

    return LBOResult(
        entry_enterprise_value=entry_ev,
        entry_debt_pct=debt_leverage_ratio,
        entry_debt=entry_debt,
        sponsor_equity_invested=sponsor_equity,
        exit_enterprise_value=exit_ev,
        debt_paid_down=debt_paydown,
        exit_debt_remaining=exit_debt,
        exit_sponsor_equity=exit_equity,
        moic=moic,
        irr=irr,
        holding_period_years=holding_period,
    )
