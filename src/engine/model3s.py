"""
model3s.py — ThreeStatementModel: builds fully-linked IS, BS, CFS projections.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.engine.drivers import ProjectedDrivers


@dataclass
class ModelOutput:
    # Income Statement
    is_revenue: List[float] = field(default_factory=list)
    is_cogs: List[float] = field(default_factory=list)
    is_gross_profit: List[float] = field(default_factory=list)
    is_ebitda: List[float] = field(default_factory=list)
    is_depreciation: List[float] = field(default_factory=list)
    is_ebit: List[float] = field(default_factory=list)
    is_interest: List[float] = field(default_factory=list)
    is_pbt: List[float] = field(default_factory=list)
    is_tax: List[float] = field(default_factory=list)
    is_pat: List[float] = field(default_factory=list)

    # Balance Sheet — Assets
    bs_cash: List[float] = field(default_factory=list)
    bs_receivables: List[float] = field(default_factory=list)
    bs_inventory: List[float] = field(default_factory=list)
    bs_nfa: List[float] = field(default_factory=list)
    bs_other_assets: List[float] = field(default_factory=list)
    bs_total_assets: List[float] = field(default_factory=list)

    # Balance Sheet — L&E
    bs_payables: List[float] = field(default_factory=list)
    bs_debt: List[float] = field(default_factory=list)
    bs_other_liabilities: List[float] = field(default_factory=list)
    bs_share_capital: List[float] = field(default_factory=list)
    bs_retained_earnings: List[float] = field(default_factory=list)
    bs_total_equity: List[float] = field(default_factory=list)
    bs_total_liab_equity: List[float] = field(default_factory=list)

    # Cash Flow Statement
    cf_cfo: List[float] = field(default_factory=list)
    cf_cfi: List[float] = field(default_factory=list)
    cf_cff: List[float] = field(default_factory=list)
    cf_net_change: List[float] = field(default_factory=list)
    cf_opening_cash: List[float] = field(default_factory=list)
    cf_closing_cash: List[float] = field(default_factory=list)

    periods: List[str] = field(default_factory=list)


import re

def _last(lst, default=0.0) -> float:
    if not lst:
        return default
    for val in reversed(lst):
        if val is not None:
            try:
                return float(val)
            except (ValueError, TypeError):
                pass
    return default


class ThreeStatementModel:
    """Builds a fully-linked 3-statement financial model."""

    def build(
        self,
        hist: dict,
        drivers: ProjectedDrivers,
        scenario: str = "Base",
        n_years: int = 5,
    ) -> ModelOutput:
        """
        hist: dict of historical lists (most-recent last).
        drivers: ProjectedDrivers for the given scenario.
        Returns ModelOutput.
        """
        out = ModelOutput()

        # ── Seed from last historical year ──────────────────────────────────
        last_rev = _last(hist.get("revenue"), 1000.0)
        last_cogs = _last(hist.get("cogs"), 600.0)
        last_nfa = _last(hist.get("net_fixed_assets"), 400.0)
        last_debt = _last(hist.get("debt"), 240.0)
        last_cash = _last(hist.get("cash"), 100.0)
        last_re = _last(hist.get("retained_earnings"), 300.0)
        last_sc = _last(hist.get("share_capital"), 50.0)
        last_other_assets = _last(hist.get("other_assets"), 0.0)
        last_other_liab = _last(hist.get("other_liabilities"), 0.0)

        # Historical periods count — derive last FY label
        hist_periods = hist.get("periods", [])
        last_fy = 25
        if hist_periods:
            try:
                p_str = str(hist_periods[-1])
                match = re.search(r"(\d{2,4})", p_str)
                if match:
                    val = int(match.group(1))
                    last_fy = val % 100
            except Exception:
                last_fy = 25

        # Driver shortcuts
        g = drivers.revenue_growth                # revenue growth rate
        gross_margin = drivers.avg_gross_margin   # gross profit / revenue
        ebitda_margin = drivers.avg_ebitda_margin
        dso = drivers.dso_days
        dii = drivers.dii_days
        dpo = drivers.dpo_days
        tax_rate = drivers.effective_tax_rate
        capex_pct = drivers.capex_intensity
        dep_rate = drivers.depreciation_rate
        int_rate = drivers.interest_rate
        debt_repay = drivers.debt_repayment_annual
        div_payout = getattr(drivers, "dividend_payout", 0.25)

        # Carry-forward state
        prev_rev = last_rev
        prev_nfa = last_nfa
        prev_debt = last_debt
        prev_cash = last_cash
        prev_re = last_re
        sc = last_sc
        other_assets = last_other_assets
        other_liab = last_other_liab

        for yr in range(1, n_years + 1):
            period_label = f"FY{last_fy + yr}E"
            out.periods.append(period_label)

            # ── Income Statement ─────────────────────────────────────────────
            revenue = prev_rev * (1 + g)
            cogs = revenue * (1 - gross_margin)
            gross_profit = revenue - cogs
            ebitda = revenue * ebitda_margin

            # FA schedule: depreciation on opening NFA
            depreciation = prev_nfa * dep_rate
            ebit = ebitda - depreciation

            # Interest on PRIOR period debt (no circular reference)
            interest = prev_debt * int_rate
            pbt = ebit - interest
            tax = max(pbt * tax_rate, 0.0)
            pat = pbt - tax

            out.is_revenue.append(revenue)
            out.is_cogs.append(cogs)
            out.is_gross_profit.append(gross_profit)
            out.is_ebitda.append(ebitda)
            out.is_depreciation.append(depreciation)
            out.is_ebit.append(ebit)
            out.is_interest.append(interest)
            out.is_pbt.append(pbt)
            out.is_tax.append(tax)
            out.is_pat.append(pat)

            # ── Working Capital Schedule ─────────────────────────────────────
            receivables = revenue * dso / 365.0
            inventory = cogs * dii / 365.0
            payables = cogs * dpo / 365.0

            # ── Fixed Asset Schedule ─────────────────────────────────────────
            capex = revenue * capex_pct
            nfa = prev_nfa + capex - depreciation

            # ── Debt Schedule ────────────────────────────────────────────────
            debt = max(prev_debt - debt_repay, 0.0)

            # ── Dividends & Retained Earnings ────────────────────────────────
            dividends = pat * div_payout
            retained_earnings = prev_re + pat - dividends

            # ── Cash Flow Statement (Closed-Loop Invariant Roll-Forward) ─────
            # Prior-period working capital
            if yr == 1:
                prev_recv = _last(hist.get("receivables", [0.0]))
                prev_inv = _last(hist.get("inventory", [0.0]))
                prev_pay = _last(hist.get("payables", [0.0]))
                prev_other_assets = last_other_assets
                prev_other_liab = last_other_liab
            else:
                prev_recv = out.bs_receivables[-1]
                prev_inv = out.bs_inventory[-1]
                prev_pay = out.bs_payables[-1]
                prev_other_assets = out.bs_other_assets[-1]
                prev_other_liab = out.bs_other_liabilities[-1]

            delta_recv = receivables - prev_recv
            delta_inv = inventory - prev_inv
            delta_pay = payables - prev_pay
            delta_nwc = delta_recv + delta_inv - delta_pay

            cfo = pat + depreciation - delta_nwc
            cfi = -capex - (other_assets - prev_other_assets)
            cff = -debt_repay - dividends + (other_liab - prev_other_liab)
            opening_cash = prev_cash
            net_change = cfo + cfi + cff
            closing_cash = opening_cash + net_change

            # ── Balance Sheet (Deterministic Roll-Forward, Zero Plugs) ────────
            cash = closing_cash
            total_assets = cash + receivables + inventory + nfa + other_assets
            total_equity = sc + retained_earnings
            total_liab_equity = payables + debt + other_liab + sc + retained_earnings

            out.bs_cash.append(cash)
            out.bs_receivables.append(receivables)
            out.bs_inventory.append(inventory)
            out.bs_nfa.append(nfa)
            out.bs_other_assets.append(other_assets)
            out.bs_total_assets.append(total_assets)

            out.bs_payables.append(payables)
            out.bs_debt.append(debt)
            out.bs_other_liabilities.append(other_liab)
            out.bs_share_capital.append(sc)
            out.bs_retained_earnings.append(retained_earnings)
            out.bs_total_equity.append(total_equity)
            out.bs_total_liab_equity.append(total_liab_equity)

            out.cf_cfo.append(cfo)
            out.cf_cfi.append(cfi)
            out.cf_cff.append(cff)
            out.cf_net_change.append(net_change)
            out.cf_opening_cash.append(opening_cash)
            out.cf_closing_cash.append(closing_cash)

            # ── Advance state ────────────────────────────────────────────────
            prev_rev = revenue
            prev_nfa = nfa
            prev_debt = debt
            prev_cash = closing_cash
            prev_re = retained_earnings

        return out

    def verify_balance_sheet(self, model_output: ModelOutput, tol: float = 1e-6) -> bool:
        """Returns True if BS balances every period."""
        for a, le in zip(model_output.bs_total_assets, model_output.bs_total_liab_equity):
            if abs(a - le) > tol:
                return False
        return True
