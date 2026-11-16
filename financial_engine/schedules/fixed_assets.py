"""
Fixed Assets Schedule: Opening Net Block, Capex, Depreciation, and Closing Net Block roll-forward.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class FixedAssetsSchedule:
    """Fixed assets schedule and roll-forward across projection periods."""
    opening_net_block: List[float] = field(default_factory=list)
    capex: List[float] = field(default_factory=list)
    depreciation: List[float] = field(default_factory=list)
    closing_net_block: List[float] = field(default_factory=list)


def build_fixed_assets_schedule(
    hist_net_block: List[float],
    proj_revenue: List[float],
    proj_capex_pct: List[float],
    proj_depr_pct: List[float],
) -> FixedAssetsSchedule:
    """
    Rolls forward PP&E / Net Block:
    Closing(t) = Opening(t) + Capex(t) - Depreciation(t)
    where Opening(t) = Closing(t-1)
    """
    n_proj = len(proj_revenue)
    opening_nb: List[float] = []
    capex_list: List[float] = []
    depr_list: List[float] = []
    closing_nb: List[float] = []

    last_closing = hist_net_block[-1]

    for i in range(n_proj):
        open_val = last_closing
        capex_val = proj_revenue[i] * proj_capex_pct[i]
        depr_val = open_val * proj_depr_pct[i]
        close_val = open_val + capex_val - depr_val

        opening_nb.append(open_val)
        capex_list.append(capex_val)
        depr_list.append(depr_val)
        closing_nb.append(close_val)

        last_closing = close_val

    return FixedAssetsSchedule(
        opening_net_block=opening_nb,
        capex=capex_list,
        depreciation=depr_list,
        closing_net_block=closing_nb,
    )
