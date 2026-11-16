"""
Discounted Cash Flow (DCF) valuation engine: FCFF, Gordon Growth, Exit Multiples, and Equity Bridge.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from financial_engine.core.types import ValuationInputs, TerminalValueMethod
from financial_engine.valuation.wacc import calculate_wacc, WACCResult
from financial_engine.core.exceptions import ValuationDivergenceError


@dataclass
class DCFResult:
    """Comprehensive outputs from the DCF valuation model."""
    wacc_details: WACCResult
    wacc: float
    terminal_growth_rate: float
    discount_factors: List[float] = field(default_factory=list)

    # Free Cash Flow to Firm (FCFF)
    ebit: List[float] = field(default_factory=list)
    tax_on_ebit: List[float] = field(default_factory=list)
    nopat: List[float] = field(default_factory=list)
    depreciation_addback: List[float] = field(default_factory=list)
    capex_deduction: List[float] = field(default_factory=list)
    delta_nwc_deduction: List[float] = field(default_factory=list)
    fcff: List[float] = field(default_factory=list)
    pv_fcff: List[float] = field(default_factory=list)
    sum_pv_fcff: float = 0.0

    # Terminal Value
    terminal_value_gordon: float = 0.0
    pv_terminal_value_gordon: float = 0.0
    terminal_value_multiple: Optional[float] = None
    pv_terminal_value_multiple: Optional[float] = None
    implied_terminal_growth_from_multiple: Optional[float] = None

    # Valuation Totals (Gordon Growth Base)
    enterprise_value: float = 0.0
    base_debt: float = 0.0
    base_cash: float = 0.0
    net_debt: float = 0.0
    equity_value: float = 0.0
    shares_outstanding: float = 0.0
    value_per_share: float = 0.0

    # Valuation Totals (Exit Multiple Alternative)
    ev_exit_multiple: Optional[float] = None
    equity_value_exit_multiple: Optional[float] = None
    value_per_share_exit_multiple: Optional[float] = None


def run_dcf_valuation(
    proj_ebit: List[float],
    proj_ebitda: List[float],
    proj_depreciation: List[float],
    proj_capex: List[float],
    proj_delta_nwc: List[float],
    base_debt: float,
    base_cash: float,
    marginal_tax_rate: float,
    inputs: ValuationInputs,
) -> DCFResult:
    """
    Executes complete institutional DCF valuation:
    1. Unlevered FCFF = NOPAT + Depr - Capex - ΔNWC
    2. Discounting via WACC
    3. Terminal Value via Gordon Growth & Exit Multiple
    4. Enterprise to Equity Value Bridge
    5. Implied Value Per Share
    """
    wacc_res = calculate_wacc(inputs, marginal_tax_rate)
    wacc = wacc_res.wacc
    g = inputs.terminal_growth_rate

    if wacc <= g:
        raise ValuationDivergenceError(
            f"WACC ({wacc:.4%}) must be strictly greater than terminal growth rate ({g:.4%}) "
            "to prevent perpetual value divergence."
        )

    n_proj = len(proj_ebit)
    tax_ebit = [proj_ebit[i] * marginal_tax_rate for i in range(n_proj)]
    nopat = [proj_ebit[i] - tax_ebit[i] for i in range(n_proj)]

    # FCFF = NOPAT + Depr - Capex - ΔNWC
    fcff_list = [
        nopat[i] + proj_depreciation[i] - proj_capex[i] - proj_delta_nwc[i]
        for i in range(n_proj)
    ]

    # Discount factors: 1 / (1 + WACC)^t
    discount_factors = [1.0 / ((1.0 + wacc) ** (t + 1)) for t in range(n_proj)]
    pv_fcff_list = [fcff_list[i] * discount_factors[i] for i in range(n_proj)]
    sum_pv_fcff = sum(pv_fcff_list)

    # Terminal Value (Gordon Growth)
    # Step 11.8: TV = FCFF_N * (1 + g) / (WACC - g)
    terminal_fcff = fcff_list[-1]
    tv_gordon = terminal_fcff * (1.0 + g) / (wacc - g)
    pv_tv_gordon = tv_gordon * discount_factors[-1]

    # Enterprise Value & Equity Value Bridge
    ev = sum_pv_fcff + pv_tv_gordon
    net_debt = base_debt - base_cash
    equity_val = ev - base_debt + base_cash
    val_per_share = equity_val / inputs.shares_outstanding

    # Terminal Value (Exit Multiple Alternative)
    terminal_ebitda = proj_ebitda[-1]
    tv_mult = terminal_ebitda * inputs.exit_multiple_ev_ebitda
    pv_tv_mult = tv_mult * discount_factors[-1]
    ev_mult = sum_pv_fcff + pv_tv_mult
    eq_mult = ev_mult - base_debt + base_cash
    val_per_share_mult = eq_mult / inputs.shares_outstanding

    # Implied perpetual growth rate from exit multiple
    # tv_mult = terminal_fcff * (1 + g_imp) / (wacc - g_imp) => g_imp = (tv * wacc - fcff) / (tv + fcff)
    implied_g = (tv_mult * wacc - terminal_fcff) / (tv_mult + terminal_fcff) if (tv_mult + terminal_fcff) != 0 else None

    return DCFResult(
        wacc_details=wacc_res,
        wacc=wacc,
        terminal_growth_rate=g,
        discount_factors=discount_factors,
        ebit=list(proj_ebit),
        tax_on_ebit=tax_ebit,
        nopat=nopat,
        depreciation_addback=list(proj_depreciation),
        capex_deduction=list(proj_capex),
        delta_nwc_deduction=list(proj_delta_nwc),
        fcff=fcff_list,
        pv_fcff=pv_fcff_list,
        sum_pv_fcff=sum_pv_fcff,
        terminal_value_gordon=tv_gordon,
        pv_terminal_value_gordon=pv_tv_gordon,
        terminal_value_multiple=tv_mult,
        pv_terminal_value_multiple=pv_tv_mult,
        implied_terminal_growth_from_multiple=implied_g,
        enterprise_value=ev,
        base_debt=base_debt,
        base_cash=base_cash,
        net_debt=net_debt,
        equity_value=equity_val,
        shares_outstanding=inputs.shares_outstanding,
        value_per_share=val_per_share,
        ev_exit_multiple=ev_mult,
        equity_value_exit_multiple=eq_mult,
        value_per_share_exit_multiple=val_per_share_mult,
    )
