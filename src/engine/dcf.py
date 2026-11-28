"""
dcf.py — DCFEngine: WACC, uFCF, Terminal Value, DCF valuation, sensitivity analysis.
"""
from __future__ import annotations

import math
from typing import List, Optional

from src.engine.model3s import ModelOutput


class DCFEngine:
    """Discounted Cash Flow valuation engine."""

    # ── WACC ────────────────────────────────────────────────────────────────

    def compute_wacc(
        self,
        equity_risk_premium: float,
        beta: float,
        risk_free: float,
        pretax_cod: float,
        tax_rate: float,
        debt_weight: float,
    ) -> float:
        """
        WACC = Ke * (1 - Wd) + Kd_at * Wd
        Ke = risk_free + beta * equity_risk_premium  (CAPM)
        Kd_at = pretax_cod * (1 - tax_rate)
        """
        equity_weight = 1.0 - debt_weight
        ke = risk_free + beta * equity_risk_premium
        kd_at = pretax_cod * (1.0 - tax_rate)
        wacc = ke * equity_weight + kd_at * debt_weight
        return wacc

    # ── Unlevered FCF ────────────────────────────────────────────────────────

    def compute_ufcf(self, model_output: ModelOutput) -> List[float]:
        """
        UFCF = EBIT * (1 - t) + D&A - CapEx - ΔNWC
        CapEx = -CFI (from CFS)
        ΔNWC  = Δreceivables + Δinventory - Δpayables (derived from BS changes)
        """
        n = len(model_output.is_ebit)
        ufcfs = []

        for i in range(n):
            ebit = model_output.is_ebit[i]
            tax_rate = (
                model_output.is_tax[i] / model_output.is_pbt[i]
                if model_output.is_pbt[i] != 0
                else 0.25
            )
            nopat = ebit * (1.0 - tax_rate)
            da = model_output.is_depreciation[i]
            capex = -model_output.cf_cfi[i]  # CFI is negative for capex

            if i == 0:
                delta_nwc = (
                    (model_output.bs_receivables[0] + model_output.bs_inventory[0] - model_output.bs_payables[0])
                )
            else:
                nwc_curr = model_output.bs_receivables[i] + model_output.bs_inventory[i] - model_output.bs_payables[i]
                nwc_prev = model_output.bs_receivables[i - 1] + model_output.bs_inventory[i - 1] - model_output.bs_payables[i - 1]
                delta_nwc = nwc_curr - nwc_prev

            ufcf = nopat + da - capex - delta_nwc
            ufcfs.append(ufcf)

        return ufcfs

    # ── Terminal Value ───────────────────────────────────────────────────────

    def compute_terminal_value(
        self,
        ufcf: List[float],
        wacc: float,
        tgr: float,
        exit_multiple: float = 8.0,
        ebitda_terminal: Optional[float] = None,
        method: str = "gordon",
    ) -> float:
        """
        method: 'gordon'  → TV = FCF_n * (1+tgr) / (wacc - tgr)
                'exit'    → TV = ebitda_terminal * exit_multiple
                'hybrid'  → average of both
        """
        last_ufcf = ufcf[-1] if ufcf else 0.0

        if wacc <= tgr:
            wacc = tgr + 0.01  # guard against infinite TV

        tv_gordon = last_ufcf * (1.0 + tgr) / (wacc - tgr)

        if ebitda_terminal is not None and exit_multiple:
            tv_exit = ebitda_terminal * exit_multiple
        else:
            tv_exit = tv_gordon  # fallback

        if method == "gordon":
            return tv_gordon
        elif method == "exit":
            return tv_exit
        else:  # hybrid
            return (tv_gordon + tv_exit) / 2.0

    # ── Full DCF ────────────────────────────────────────────────────────────

    def compute_dcf(
        self,
        ufcf: List[float],
        tv: float,
        wacc: float,
        periods: List[str],
        shares: float = 10.0,
        net_debt: float = 0.0,
    ) -> dict:
        """
        Returns enterprise_value, net_debt, equity_value, shares,
        price_per_share, npv, irr.
        """
        n = len(ufcf)
        discount_factors = [(1.0 / (1.0 + wacc) ** (i + 1)) for i in range(n)]

        pv_ufcfs = [f * df for f, df in zip(ufcf, discount_factors)]
        pv_tv = tv / (1.0 + wacc) ** n

        enterprise_value = sum(pv_ufcfs) + pv_tv
        equity_value = enterprise_value - net_debt
        price_per_share = equity_value / shares if shares else 0.0
        npv = sum(pv_ufcfs) + pv_tv  # same as EV here

        # IRR via Newton-Raphson
        irr = self._irr(ufcf, tv)

        return {
            "enterprise_value": enterprise_value,
            "net_debt": net_debt,
            "equity_value": equity_value,
            "shares": shares,
            "price_per_share": price_per_share,
            "npv": npv,
            "irr": irr,
            "pv_ufcfs": pv_ufcfs,
            "pv_tv": pv_tv,
            "discount_factors": discount_factors,
        }

    def _irr(self, ufcf: List[float], tv: float, max_iter: int = 200) -> float:
        """Compute IRR using Newton-Raphson with overflow guard."""
        cf = ufcf[:]
        if cf:
            cf[-1] += tv
        rate = 0.10
        for _ in range(max_iter):
            try:
                npv = sum(c / (1.0 + rate) ** (i + 1) for i, c in enumerate(cf))
                dnpv = sum(-(i + 1) * c / (1.0 + rate) ** (i + 2) for i, c in enumerate(cf))
            except (OverflowError, ZeroDivisionError):
                break
            if dnpv == 0:
                break
            step = npv / dnpv
            # Clamp step to avoid runaway
            step = max(-0.5, min(0.5, step))
            rate_new = rate - step
            # Keep rate in reasonable bounds
            rate_new = max(-0.99, min(10.0, rate_new))
            if abs(rate_new - rate) < 1e-9:
                rate = rate_new
                break
            rate = rate_new
        return rate

    # ── Sensitivity — WACC vs TGR ────────────────────────────────────────────

    def sensitivity_matrix(
        self,
        ufcf: List[float],
        tv_base: float,
        wacc_range: List[float],
        tgr_range: List[float],
    ) -> List[List[float]]:
        """
        Returns a 2D list [wacc_i][tgr_j] of equity values per share.
        Rows = WACC values, Columns = TGR values.
        """
        result = []
        n = len(ufcf)
        for wacc in wacc_range:
            row = []
            for tgr in tgr_range:
                tv = self.compute_terminal_value(ufcf, wacc, tgr, method="gordon")
                pv_fcf = sum(f / (1.0 + wacc) ** (i + 1) for i, f in enumerate(ufcf))
                pv_tv = tv / (1.0 + wacc) ** n
                ev = pv_fcf + pv_tv
                row.append(round(ev, 2))
            result.append(row)
        return result

    # ── Sensitivity — Revenue Growth vs EBITDA Margin ───────────────────────

    def sensitivity_margin(
        self,
        revenue_growth_range: List[float],
        ebitda_margin_range: List[float],
        hist: dict,
        drivers,
    ) -> List[List[float]]:
        """
        Returns a 2D list [growth_i][margin_j] of approximate equity values.
        Uses a simplified single-period proxy: last_revenue * g * margin / wacc.
        """
        import copy
        from src.engine.model3s import ThreeStatementModel

        result = []
        m3 = ThreeStatementModel()

        last_rev = hist.get("revenue", [1000.0])[-1]

        for g in revenue_growth_range:
            row = []
            for margin in ebitda_margin_range:
                d = copy.deepcopy(drivers)
                d.revenue_growth = g
                d.avg_ebitda_margin = margin
                mo = m3.build(hist, d, n_years=5)
                ufcf = self.compute_ufcf(mo)
                wacc = 0.12  # default for sensitivity
                tgr = 0.05
                tv = self.compute_terminal_value(ufcf, wacc, tgr, method="gordon")
                n = len(ufcf)
                pv_fcf = sum(f / (1.0 + wacc) ** (i + 1) for i, f in enumerate(ufcf))
                pv_tv = tv / (1.0 + wacc) ** n
                ev = pv_fcf + pv_tv
                row.append(round(ev, 2))
            result.append(row)
        return result
