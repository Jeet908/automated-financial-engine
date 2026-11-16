"""
Two-way sensitivity analysis engine for WACC vs Terminal Growth and Driver Variations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class SensitivityMatrix:
    title: str
    row_label: str
    col_label: str
    row_values: List[float]
    col_values: List[float]
    matrix: List[List[float]]  # matrix[row_idx][col_idx]
    center_value: float


def build_wacc_growth_sensitivity(
    fcff_list: List[float],
    base_debt: float,
    base_cash: float,
    shares_outstanding: float,
    center_wacc: float,
    center_growth: float,
    wacc_steps: Optional[List[float]] = None,
    growth_steps: Optional[List[float]] = None,
) -> SensitivityMatrix:
    """
    Constructs the 5x5 WACC vs Terminal Growth Rate sensitivity table:
    Row: WACC (WACC - 2%, WACC - 1%, WACC, WACC + 1%, WACC + 2%)
    Col: Growth (4.0%, 4.5%, 5.0%, 5.5%, 6.0%)
    Formula:
    EV = SUM(FCFF_t / (1 + WACC)^t) + [FCFF_N * (1 + g) / (WACC - g)] / (1 + WACC)^N
    Equity = EV - Debt + Cash
    Per Share = Equity / Shares
    """
    n_proj = len(fcff_list)
    terminal_fcff = fcff_list[-1]

    # Default grid matching standard financial layouts
    row_vals = wacc_steps or [
        center_wacc - 0.02,
        center_wacc - 0.01,
        center_wacc,
        center_wacc + 0.01,
        center_wacc + 0.02,
    ]

    col_vals = growth_steps or [
        center_growth - 0.010,
        center_growth - 0.005,
        center_growth,
        center_growth + 0.005,
        center_growth + 0.010,
    ]

    grid: List[List[float]] = []

    for w in row_vals:
        row_res: List[float] = []
        for g in col_vals:
            if w <= g:
                # Singularity guard
                row_res.append(0.0)
                continue

            # 1. Discounted FCFF
            pv_fcff_sum = sum(fcff_list[t] / ((1.0 + w) ** (t + 1)) for t in range(n_proj))

            # 2. Terminal Value
            tv = terminal_fcff * (1.0 + g) / (w - g)
            pv_tv = tv / ((1.0 + w) ** n_proj)

            # 3. Enterprise Value & Equity Bridge
            ev = pv_fcff_sum + pv_tv
            equity = ev - base_debt + base_cash
            price = equity / shares_outstanding if shares_outstanding > 0 else 0.0

            row_res.append(price)
        grid.append(row_res)

    center_val = grid[2][2] if len(grid) > 2 and len(grid[2]) > 2 else 0.0

    return SensitivityMatrix(
        title="Value Per Share (Rs) Sensitivity: WACC vs Terminal Growth Rate",
        row_label="WACC ↓",
        col_label="Terminal Growth →",
        row_values=row_vals,
        col_values=col_vals,
        matrix=grid,
        center_value=center_val,
    )
