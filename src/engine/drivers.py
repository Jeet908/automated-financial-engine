"""
drivers.py — DriverCalibrator: calibrates historical financial drivers
and generates Base/Bull/Bear scenario assumptions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ProjectedDrivers:
    revenue_cagr: float = 0.10
    avg_gross_margin: float = 0.40
    avg_ebitda_margin: float = 0.18
    dso_days: float = 45.0
    dii_days: float = 50.0
    dpo_days: float = 60.0
    effective_tax_rate: float = 0.25
    capex_intensity: float = 0.05
    interest_rate: float = 0.09
    debt_repayment_annual: float = 30.0
    depreciation_rate: float = 0.10
    dividend_payout: float = 0.25
    # optional per-year growth override (populated in scenario copies)
    revenue_growth: float = 0.10


def _safe(lst, default=0.0) -> List[float]:
    """Return a list of floats with None replaced by default, or [default] if empty."""
    if not lst:
        return [default]
    cleaned = []
    last_valid = default
    for v in lst:
        if v is not None:
            try:
                last_valid = float(v)
                cleaned.append(last_valid)
            except (ValueError, TypeError):
                cleaned.append(last_valid)
        else:
            cleaned.append(last_valid)
    return cleaned if cleaned else [default]


class DriverCalibrator:
    """Calibrates projection drivers from a historical financials dict."""

    def calibrate(self, hist: dict) -> ProjectedDrivers:
        """
        hist keys (all lists, most-recent last):
          revenue, cogs, gross_profit, ebitda, depreciation, interest, tax, pat,
          receivables, inventory, payables, net_fixed_assets, debt, capex
        Returns a ProjectedDrivers object.
        """
        rev = _safe(hist.get("revenue", []))
        cogs = _safe(hist.get("cogs", []))
        default_gp = [r - c for r, c in zip(rev, cogs)] if len(rev) == len(cogs) else [r * 0.4 for r in rev]
        gp = _safe(hist.get("gross_profit") or default_gp)
        ebitda = _safe(hist.get("ebitda", []))
        dep = _safe(hist.get("depreciation", []))
        interest = _safe(hist.get("interest", []))
        tax = _safe(hist.get("tax", []))
        pbt_list = _safe(hist.get("pbt", []))
        pat = _safe(hist.get("pat", []))

        receivables = _safe(hist.get("receivables", []))
        inventory = _safe(hist.get("inventory", []))
        payables = _safe(hist.get("payables", []))
        capex_list = _safe(hist.get("capex", []))
        debt_list = _safe(hist.get("debt", []))

        # --- Revenue CAGR ---
        n = len(rev)
        if n >= 2 and rev[0] > 0:
            revenue_cagr = (rev[-1] / rev[0]) ** (1.0 / (n - 1)) - 1.0
        else:
            revenue_cagr = 0.10

        # --- Gross margin (3yr rolling avg) ---
        gp_margins = [g / r for g, r in zip(gp, rev) if r != 0]
        window = gp_margins[-3:] if len(gp_margins) >= 3 else gp_margins
        avg_gross_margin = sum(window) / len(window) if window else 0.40

        # --- EBITDA margin ---
        if ebitda:
            ebitda_margins = [e / r for e, r in zip(ebitda, rev) if r != 0]
        else:
            # approximate: gross_profit - opex_below_GP + depreciation (not available here → use GP - interest as proxy)
            ebitda_approx = [g - i for g, i in zip(gp, interest)]
            ebitda_margins = [e / r for e, r in zip(ebitda_approx, rev) if r != 0]
        window_ebitda = ebitda_margins[-3:] if len(ebitda_margins) >= 3 else ebitda_margins
        avg_ebitda_margin = sum(window_ebitda) / len(window_ebitda) if window_ebitda else 0.18

        # --- Working capital days ---
        def avg_days(balances, base, scale=365):
            pairs = [(b / r * scale) for b, r in zip(balances, base) if r != 0]
            return sum(pairs) / len(pairs) if pairs else 45.0

        dso_days = avg_days(receivables, rev)
        dii_days = avg_days(inventory, cogs)
        dpo_days = avg_days(payables, cogs)

        # --- Effective tax rate ---
        if pbt_list:
            tax_rates = [t / p for t, p in zip(tax, pbt_list) if p > 0]
        elif pat:
            tax_rates = [t / (t + p) for t, p in zip(tax, pat) if (t + p) > 0]
        else:
            tax_rates = [0.25]
        window_tax = tax_rates[-3:] if len(tax_rates) >= 3 else tax_rates
        effective_tax_rate = sum(window_tax) / len(window_tax) if window_tax else 0.25

        # --- CapEx intensity ---
        if capex_list:
            capex_pcts = [abs(c) / r for c, r in zip(capex_list, rev) if r != 0]
            capex_intensity = sum(capex_pcts) / len(capex_pcts) if capex_pcts else 0.05
        else:
            capex_intensity = 0.05

        # --- Interest rate (interest / avg debt) ---
        if len(debt_list) >= 2:
            avg_debts = [(debt_list[i] + debt_list[i + 1]) / 2 for i in range(len(debt_list) - 1)]
            int_rates = [i / d for i, d in zip(interest, avg_debts) if d > 0]
            interest_rate = sum(int_rates) / len(int_rates) if int_rates else 0.09
        else:
            interest_rate = interest[-1] / debt_list[-1] if debt_list[-1] else 0.09

        # --- Debt repayment (average annual reduction) ---
        if len(debt_list) >= 2:
            reductions = [max(debt_list[i] - debt_list[i + 1], 0) for i in range(len(debt_list) - 1)]
            debt_repayment_annual = sum(reductions) / len(reductions)
        else:
            debt_repayment_annual = 30.0

        # --- Depreciation rate on opening NFA ---
        nfa = hist.get("net_fixed_assets") or []
        if nfa and len(nfa) >= 2:
            dep_rates = [d / n for d, n in zip(dep[1:], nfa[:-1]) if n > 0]
            dep_rate = sum(dep_rates) / len(dep_rates) if dep_rates else 0.10
        else:
            dep_rate = 0.10

        return ProjectedDrivers(
            revenue_cagr=revenue_cagr,
            avg_gross_margin=avg_gross_margin,
            avg_ebitda_margin=avg_ebitda_margin,
            dso_days=dso_days,
            dii_days=dii_days,
            dpo_days=dpo_days,
            effective_tax_rate=effective_tax_rate,
            capex_intensity=capex_intensity,
            interest_rate=interest_rate,
            debt_repayment_annual=debt_repayment_annual,
            depreciation_rate=dep_rate,
            revenue_growth=revenue_cagr,
        )

    def generate_scenarios(self, drivers: ProjectedDrivers) -> Dict[str, ProjectedDrivers]:
        """
        Returns Base, Bull, and Bear scenario ProjectedDrivers objects.
        Bull: revenue_growth +3%, margins +2%, capex -1%
        Bear: revenue_growth -3%, margins -2%, capex +1%
        """
        import copy

        base = copy.deepcopy(drivers)

        bull = copy.deepcopy(drivers)
        bull.revenue_cagr = drivers.revenue_cagr + 0.03
        bull.revenue_growth = bull.revenue_cagr
        bull.avg_gross_margin = min(drivers.avg_gross_margin + 0.02, 0.99)
        bull.avg_ebitda_margin = min(drivers.avg_ebitda_margin + 0.02, 0.99)
        bull.capex_intensity = max(drivers.capex_intensity - 0.01, 0.0)

        bear = copy.deepcopy(drivers)
        bear.revenue_cagr = max(drivers.revenue_cagr - 0.03, -0.50)
        bear.revenue_growth = bear.revenue_cagr
        bear.avg_gross_margin = max(drivers.avg_gross_margin - 0.02, 0.0)
        bear.avg_ebitda_margin = max(drivers.avg_ebitda_margin - 0.02, 0.0)
        bear.capex_intensity = drivers.capex_intensity + 0.01

        return {"Base": base, "Bull": bull, "Bear": bear}
