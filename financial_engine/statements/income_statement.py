"""
Income Statement model and ratio analytics across historical and forecast horizons.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from financial_engine.core.types import HistoricalFinancials, ProjectionAssumptions


@dataclass
class IncomeStatement:
    """Consolidated Income Statement spanning historical and projection years."""
    # Line items
    revenue: List[float] = field(default_factory=list)
    cogs: List[float] = field(default_factory=list)
    gross_profit: List[float] = field(default_factory=list)
    employee_costs: List[float] = field(default_factory=list)
    other_expenses: List[float] = field(default_factory=list)
    ebitda: List[float] = field(default_factory=list)
    depreciation: List[float] = field(default_factory=list)
    ebit: List[float] = field(default_factory=list)
    interest: List[float] = field(default_factory=list)
    pbt: List[float] = field(default_factory=list)
    tax: List[float] = field(default_factory=list)
    pat: List[float] = field(default_factory=list)
    dividends: List[float] = field(default_factory=list)

    # Ratios
    revenue_growth: List[Optional[float]] = field(default_factory=list)
    gross_margin: List[float] = field(default_factory=list)
    ebitda_margin: List[float] = field(default_factory=list)
    ebit_margin: List[float] = field(default_factory=list)
    net_margin: List[float] = field(default_factory=list)

    @property
    def net_income(self) -> List[float]:
        return self.pat

    @property
    def operating_income(self) -> List[float]:
        return self.ebit

    @property
    def operating_profit(self) -> List[float]:
        return self.ebit

    @property
    def sga(self) -> List[float]:
        n = max(len(self.employee_costs), len(self.other_expenses))
        return [
            (self.employee_costs[i] if i < len(self.employee_costs) else 0.0)
            + (self.other_expenses[i] if i < len(self.other_expenses) else 0.0)
            for i in range(n)
        ]


def build_income_statement(
    historicals: HistoricalFinancials,
    assumptions: ProjectionAssumptions,
    sched_depreciation: List[float],
    sched_interest: List[float],
) -> IncomeStatement:
    """Builds the full multi-year income statement with margin and growth ratios."""
    n_hist = len(historicals.revenue)
    n_proj = len(assumptions.revenue_growth)

    # 1. Historicals
    all_revenue = list(historicals.revenue)
    all_cogs = list(historicals.cogs)
    all_gross_profit = [all_revenue[i] - all_cogs[i] for i in range(n_hist)]
    all_employee = list(historicals.employee_costs)
    all_other = list(historicals.other_expenses)
    all_ebitda = [all_gross_profit[i] - all_employee[i] - all_other[i] for i in range(n_hist)]
    all_depr = list(historicals.depreciation)
    all_ebit = [all_ebitda[i] - all_depr[i] for i in range(n_hist)]
    all_interest = list(historicals.interest)
    all_pbt = [all_ebit[i] - all_interest[i] for i in range(n_hist)]
    all_tax = list(historicals.tax)
    all_pat = [all_pbt[i] - all_tax[i] for i in range(n_hist)]
    all_dividends = list(historicals.dividends)

    # Determine COGS % assumption
    if assumptions.cogs_pct_revenue is not None:
        cogs_pct_list = assumptions.cogs_pct_revenue
    else:
        # Step 3.2: 1 - AVERAGE(historical gross margin)
        hist_gm = [all_gross_profit[i] / all_revenue[i] for i in range(n_hist)]
        avg_hist_gm = sum(hist_gm) / len(hist_gm)
        cogs_pct_val = 1.0 - avg_hist_gm
        cogs_pct_list = [cogs_pct_val] * n_proj

    # 2. Projections
    for i in range(n_proj):
        prev_rev = all_revenue[-1]
        rev_val = prev_rev * (1.0 + assumptions.revenue_growth[i])
        cogs_val = rev_val * cogs_pct_list[i]
        gp_val = rev_val - cogs_val
        emp_val = rev_val * assumptions.employee_pct_revenue[i]
        oth_val = rev_val * assumptions.other_opex_pct_revenue[i]
        ebitda_val = gp_val - emp_val - oth_val

        depr_val = sched_depreciation[i]
        ebit_val = ebitda_val - depr_val

        int_val = sched_interest[i]
        pbt_val = ebit_val - int_val

        tax_val = pbt_val * assumptions.tax_rate[i]
        pat_val = pbt_val - tax_val

        div_val = pat_val * assumptions.dividend_payout[i]

        all_revenue.append(rev_val)
        all_cogs.append(cogs_val)
        all_gross_profit.append(gp_val)
        all_employee.append(emp_val)
        all_other.append(oth_val)
        all_ebitda.append(ebitda_val)
        all_depr.append(depr_val)
        all_ebit.append(ebit_val)
        all_interest.append(int_val)
        all_pbt.append(pbt_val)
        all_tax.append(tax_val)
        all_pat.append(pat_val)
        all_dividends.append(div_val)

    # 3. Ratios
    total_periods = len(all_revenue)
    growth_list: List[Optional[float]] = [None]
    for i in range(1, total_periods):
        growth_list.append((all_revenue[i] / all_revenue[i - 1]) - 1.0)

    gm_list = [all_gross_profit[i] / all_revenue[i] for i in range(total_periods)]
    ebitda_m_list = [all_ebitda[i] / all_revenue[i] for i in range(total_periods)]
    ebit_m_list = [all_ebit[i] / all_revenue[i] for i in range(total_periods)]
    net_m_list = [all_pat[i] / all_revenue[i] for i in range(total_periods)]

    return IncomeStatement(
        revenue=all_revenue,
        cogs=all_cogs,
        gross_profit=all_gross_profit,
        employee_costs=all_employee,
        other_expenses=all_other,
        ebitda=all_ebitda,
        depreciation=all_depr,
        ebit=all_ebit,
        interest=all_interest,
        pbt=all_pbt,
        tax=all_tax,
        pat=all_pat,
        dividends=all_dividends,
        revenue_growth=growth_list,
        gross_margin=gm_list,
        ebitda_margin=ebitda_m_list,
        ebit_margin=ebit_m_list,
        net_margin=net_m_list,
    )
