"""
Working Capital Schedule: Days metrics, accounts receivable, inventory, accounts payable, and net working capital.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class WorkingCapitalSchedule:
    """Complete Working Capital Schedule across historical and projection years."""
    # Drivers (in days)
    receivable_days: List[float] = field(default_factory=list)
    inventory_days: List[float] = field(default_factory=list)
    payable_days: List[float] = field(default_factory=list)

    # Balances
    receivables: List[float] = field(default_factory=list)
    inventory: List[float] = field(default_factory=list)
    payables: List[float] = field(default_factory=list)

    # Aggregates
    net_working_capital: List[float] = field(default_factory=list)
    change_in_nwc: List[float] = field(default_factory=list)  # ΔNWC for CF statement (t - (t-1))


def build_working_capital_schedule(
    hist_revenue: List[float],
    hist_cogs: List[float],
    hist_ar: List[float],
    hist_inv: List[float],
    hist_ap: List[float],
    proj_revenue: List[float],
    proj_cogs: List[float],
    proj_dso: List[float],
    proj_dio: List[float],
    proj_dpo: List[float],
) -> WorkingCapitalSchedule:
    """Builds and projects working capital metrics and balances."""
    n_hist = len(hist_revenue)
    n_proj = len(proj_revenue)

    # 1. Historical days calculation
    hist_dso = [hist_ar[i] / hist_revenue[i] * 365.0 for i in range(n_hist)]
    hist_dio = [hist_inv[i] / hist_cogs[i] * 365.0 for i in range(n_hist)]
    hist_dpo = [hist_ap[i] / hist_cogs[i] * 365.0 for i in range(n_hist)]

    all_dso = hist_dso + list(proj_dso)
    all_dio = hist_dio + list(proj_dio)
    all_dpo = hist_dpo + list(proj_dpo)

    # 2. Historical balances
    all_ar = list(hist_ar)
    all_inv = list(hist_inv)
    all_ap = list(hist_ap)

    # 3. Projected balances
    for i in range(n_proj):
        ar_val = proj_dso[i] / 365.0 * proj_revenue[i]
        inv_val = proj_dio[i] / 365.0 * proj_cogs[i]
        ap_val = proj_dpo[i] / 365.0 * proj_cogs[i]
        all_ar.append(ar_val)
        all_inv.append(inv_val)
        all_ap.append(ap_val)

    # 4. Net Working Capital = AR + Inventory - AP
    all_nwc = [all_ar[i] + all_inv[i] - all_ap[i] for i in range(len(all_ar))]

    # 5. Change in Working Capital (ΔNWC)
    # delta_nwc[0] is for the 2nd historical year (FY24 vs FY23)
    all_delta_nwc = []
    for i in range(1, len(all_nwc)):
        all_delta_nwc.append(all_nwc[i] - all_nwc[i - 1])

    return WorkingCapitalSchedule(
        receivable_days=all_dso,
        inventory_days=all_dio,
        payable_days=all_dpo,
        receivables=all_ar,
        inventory=all_inv,
        payables=all_ap,
        net_working_capital=all_nwc,
        change_in_nwc=all_delta_nwc,
    )
