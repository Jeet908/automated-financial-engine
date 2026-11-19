"""
pain_points.py — C-Suite Operational Pain Point Diagnostic Engine.

Automatically diagnoses:
  1. Cash Conversion Cycle (CCC) & Working Capital bottleneck
  2. Cost Structure, COGS & SG&A Margin Bridge
  3. Capital Allocation, Debt Service & ROIC vs WACC Spread

Returns structured pain_points dict for embedding in valuation result payloads and executive memo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CCCDiagnostic:
    dso: float = 0.0          # Days Sales Outstanding (Receivable Days)
    dio: float = 0.0          # Days Inventory Outstanding
    dpo: float = 0.0          # Days Payable Outstanding
    ccc: float = 0.0          # Cash Conversion Cycle = DSO + DIO - DPO
    cash_trapped_cr: float = 0.0   # Cash trapped in AR + Inventory (in millions / crores)
    fcf_unlock_pct: float = 0.0    # % FCF unlock if DSO/DIO reduced by 7-10 days
    ev_unlock_pct: float = 0.0     # % EV unlock from CCC compression
    severity: str = "low"     # "low" | "medium" | "high"


@dataclass
class MarginDiagnostic:
    ebitda_margin: float = 0.0     # Current EBITDA margin %
    gross_margin: float = 0.0      # Gross margin %
    cogs_pct: float = 0.0          # COGS as % of revenue
    sga_pct: float = 0.0           # SG&A as % of revenue
    uplift_potential: float = 0.0  # EBITDA uplift if margins improve 150-300 bps
    target_ebitda_margin: float = 0.0
    severity: str = "low"


@dataclass
class ROICDiagnostic:
    roic_pct: float = 0.0          # Return on Invested Capital %
    wacc_pct: float = 0.0          # Weighted Average Cost of Capital %
    spread_pct: float = 0.0        # ROIC - WACC spread
    value_destruction: bool = False
    nopat: float = 0.0
    invested_capital: float = 0.0
    optimal_capex_reallocation: str = ""
    severity: str = "low"


@dataclass
class PainPointReport:
    ccc: CCCDiagnostic = field(default_factory=CCCDiagnostic)
    margin: MarginDiagnostic = field(default_factory=MarginDiagnostic)
    roic: ROICDiagnostic = field(default_factory=ROICDiagnostic)
    overall_health_score: float = 100.0  # 0–100, higher is healthier
    top_recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ccc": {
                "dso": round(self.ccc.dso, 2),
                "dio": round(self.ccc.dio, 2),
                "dpo": round(self.ccc.dpo, 2),
                "ccc_days": round(self.ccc.ccc, 2),
                "cash_trapped_cr": round(self.ccc.cash_trapped_cr, 2),
                "fcf_unlock_pct": round(self.ccc.fcf_unlock_pct, 2),
                "ev_unlock_pct": round(self.ccc.ev_unlock_pct, 2),
                "severity": self.ccc.severity,
            },
            "margin": {
                "ebitda_margin": round(self.margin.ebitda_margin, 2),
                "gross_margin": round(self.margin.gross_margin, 2),
                "cogs_pct": round(self.margin.cogs_pct, 2),
                "sga_pct": round(self.margin.sga_pct, 2),
                "uplift_potential": round(self.margin.uplift_potential, 2),
                "target_ebitda_margin": round(self.margin.target_ebitda_margin, 2),
                "severity": self.margin.severity,
            },
            "roic": {
                "roic_pct": round(self.roic.roic_pct, 2),
                "wacc_pct": round(self.roic.wacc_pct, 2),
                "spread_pct": round(self.roic.spread_pct, 2),
                "value_destruction": self.roic.value_destruction,
                "nopat": round(self.roic.nopat, 2),
                "invested_capital": round(self.roic.invested_capital, 2),
                "optimal_capex_reallocation": self.roic.optimal_capex_reallocation,
                "severity": self.roic.severity,
            },
            "overall_health_score": round(self.overall_health_score, 1),
            "top_recommendation": self.top_recommendation,
        }


def _safe_avg(lst: List[float], default: float = 0.0) -> float:
    valid = [x for x in lst if x is not None and x == x]  # filter NaN
    return sum(valid) / len(valid) if valid else default


def _safe_last(lst: List[float], default: float = 0.0) -> float:
    if not lst:
        return default
    for v in reversed(lst):
        if v is not None and v == v:
            return float(v)
    return default


def diagnose(model_data: Dict[str, Any], wacc: float = 0.10) -> PainPointReport:
    """
    Runs the full C-Suite Pain Point diagnostic against model_data dict.

    Args:
        model_data: dict with keys like revenue, cogs, ebitda, net_income,
                    total_assets, total_debt, accounts_receivable, inventory,
                    accounts_payable, capex, depreciation, etc.
        wacc: blended WACC decimal (e.g. 0.10 for 10%).

    Returns:
        PainPointReport with structured diagnostics.
    """
    report = PainPointReport()

    # ---- 1. Cash Conversion Cycle ----------------------------------------
    revenue = model_data.get("revenue", model_data.get("is_revenue", []))
    cogs = model_data.get("cogs", model_data.get("is_cogs", []))
    ar = model_data.get("accounts_receivable", model_data.get("bs_accounts_receivable", []))
    inv = model_data.get("inventory", model_data.get("bs_inventory", []))
    ap = model_data.get("accounts_payable", model_data.get("bs_accounts_payable", []))

    if revenue and cogs:
        last_rev = _safe_last(revenue)
        last_cogs = _safe_last(cogs)
        last_ar = _safe_last(ar)
        last_inv = _safe_last(inv)
        last_ap = _safe_last(ap)

        daily_rev = last_rev / 365.0 if last_rev > 0 else 1.0
        daily_cogs = last_cogs / 365.0 if last_cogs > 0 else 1.0

        dso = (last_ar / daily_rev) if daily_rev > 0 else 0.0
        dio = (last_inv / daily_cogs) if daily_cogs > 0 else 0.0
        dpo = (last_ap / daily_cogs) if daily_cogs > 0 else 0.0
        ccc = dso + dio - dpo

        cash_trapped = last_ar + last_inv
        # FCF unlock: 8-day reduction in DSO+DIO
        fcf_unlock = 8.0 * daily_rev
        fcf_unlock_pct = (fcf_unlock / last_rev * 100.0) if last_rev > 0 else 0.0

        # EV unlock: FCF improvement capitalized at WACC
        ev_unlock = (fcf_unlock / wacc) if wacc > 0 else 0.0
        ev_base = model_data.get("enterprise_value", last_rev * 2.0)
        if not isinstance(ev_base, (int, float)) or ev_base <= 0:
            ev_base = max(last_rev * 2.0, 1.0)
        ev_unlock_pct = (ev_unlock / ev_base * 100.0) if ev_base > 0 else 0.0

        severity = "high" if ccc > 90.0 else ("medium" if ccc > 50.0 else "low")

        report.ccc = CCCDiagnostic(
            dso=round(dso, 1),
            dio=round(dio, 1),
            dpo=round(dpo, 1),
            ccc=round(ccc, 1),
            cash_trapped_cr=round(cash_trapped, 2),
            fcf_unlock_pct=round(fcf_unlock_pct, 2),
            ev_unlock_pct=round(ev_unlock_pct, 2),
            severity=severity,
        )

    # ---- 2. Margin Bridge -----------------------------------------------
    ebitda = model_data.get("ebitda", model_data.get("is_ebitda", []))
    sga = model_data.get("sga", model_data.get("is_sga", []))

    if revenue and ebitda:
        last_rev = _safe_last(revenue)
        last_cogs = _safe_last(cogs)
        last_ebitda = _safe_last(ebitda)
        last_sga = _safe_last(sga)

        gross_profit = last_rev - last_cogs if last_rev and last_cogs else 0.0
        gross_margin = (gross_profit / last_rev * 100.0) if last_rev > 0 else 0.0
        ebitda_margin = (last_ebitda / last_rev * 100.0) if last_rev > 0 else 0.0
        cogs_pct = (last_cogs / last_rev * 100.0) if last_rev > 0 else 0.0
        sga_pct = (last_sga / last_rev * 100.0) if last_rev > 0 else 0.0

        target_ebitda_margin = ebitda_margin + 2.5  # +250 bps target
        uplift_potential = last_rev * 0.025         # +250 bps on revenue

        severity = "high" if ebitda_margin < 12.0 else ("medium" if ebitda_margin < 20.0 else "low")

        report.margin = MarginDiagnostic(
            ebitda_margin=round(ebitda_margin, 2),
            gross_margin=round(gross_margin, 2),
            cogs_pct=round(cogs_pct, 2),
            sga_pct=round(sga_pct, 2),
            uplift_potential=round(uplift_potential, 2),
            target_ebitda_margin=round(target_ebitda_margin, 2),
            severity=severity,
        )

    # ---- 3. ROIC vs WACC Spread -----------------------------------------
    ebit = model_data.get("ebit", model_data.get("is_ebit", []))
    tax_rate = model_data.get("tax_rate", [0.25])
    total_debt = model_data.get("total_debt", model_data.get("bs_total_debt", []))
    total_equity = model_data.get("total_equity", model_data.get("bs_total_equity", []))

    if ebit:
        last_ebit = _safe_last(ebit)
        last_tax = _safe_last(tax_rate, 0.25)
        nopat = last_ebit * (1.0 - last_tax)

        last_debt = _safe_last(total_debt)
        last_equity = _safe_last(total_equity)
        invested_capital = (last_debt + last_equity) if (last_debt + last_equity) > 0 else 1.0

        roic_pct = (nopat / invested_capital * 100.0) if invested_capital > 0 else 0.0
        wacc_pct = wacc * 100.0
        spread = roic_pct - wacc_pct
        value_destruction = spread < 0.0

        if value_destruction:
            realloc = f"Prioritize debt paydown (eliminates {abs(spread):.1f}% negative return drag). Defer low-ROI CapEx until ROIC > WACC."
        else:
            realloc = f"Compounding value: ROIC exceeds WACC by {spread:.1f}%. Reinvest free cash into high-return expansion or share buybacks."

        severity = "high" if value_destruction else ("medium" if spread < 2.5 else "low")

        report.roic = ROICDiagnostic(
            roic_pct=round(roic_pct, 2),
            wacc_pct=round(wacc_pct, 2),
            spread_pct=round(spread, 2),
            value_destruction=value_destruction,
            nopat=round(nopat, 2),
            invested_capital=round(invested_capital, 2),
            optimal_capex_reallocation=realloc,
            severity=severity,
        )

    # ---- Overall Health Score (0–100) ----------------------------------
    score = 100.0
    if report.ccc.severity == "high": score -= 25.0
    elif report.ccc.severity == "medium": score -= 12.0
    if report.margin.severity == "high": score -= 30.0
    elif report.margin.severity == "medium": score -= 15.0
    if report.roic.severity == "high": score -= 30.0
    elif report.roic.severity == "medium": score -= 10.0
    report.overall_health_score = max(0.0, score)

    severities = {
        "Working Capital & CCC Drag": report.ccc.severity,
        "Operating Margin Compression": report.margin.severity,
        "ROIC < WACC Capital Drag": report.roic.severity,
    }
    top = max(severities, key=lambda k: {"high": 2, "medium": 1, "low": 0}[severities[k]])
    report.top_recommendation = f"Primary C-Suite Directive: Address {top}. Overall Health Score: {report.overall_health_score:.0f}/100."

    return report


def diagnose_pain_points(model_or_data: Any, wacc: float = 0.10) -> List[Dict[str, Any]]:
    """
    Runs diagnostic and returns a ranked list of C-Suite pain point dictionaries
    with keys: 'category', 'summary', 'growth_prescription', 'severity', 'metric_value'.
    """
    if isinstance(model_or_data, dict):
        model_data = model_or_data
    else:
        model_data = {}
        cfg = getattr(model_or_data, "config", None)
        hist = getattr(cfg, "historicals", None)
        if hist:
            for k in (
                "revenue", "cogs", "employee_costs", "other_expenses",
                "depreciation", "interest", "tax", "cash", "receivables",
                "inventory", "net_fixed_assets", "payables", "debt",
                "share_capital", "retained_earnings"
            ):
                if hasattr(hist, k):
                    model_data[k] = getattr(hist, k)
        dcf_res = getattr(model_or_data, "dcf_result", None)
        if dcf_res:
            wacc = getattr(dcf_res, "wacc", wacc)
            model_data["enterprise_value"] = getattr(dcf_res, "enterprise_value", 0.0)

    report = diagnose(model_data, wacc=wacc)

    items = [
        {
            "category": "Working Capital & CCC",
            "summary": f"Cash Conversion Cycle is {report.ccc.ccc:.1f} days with {report.ccc.cash_trapped_cr:,.1f} trapped in working capital.",
            "growth_prescription": f"Compress receivable DSO & inventory DIO by 8-10 days to unlock ~{report.ccc.fcf_unlock_pct:.1f}% incremental FCF.",
            "severity": report.ccc.severity,
            "metric_value": report.ccc.ccc,
        },
        {
            "category": "Operating Margins",
            "summary": f"EBITDA margin currently at {report.margin.ebitda_margin:.1f}% (COGS: {report.margin.cogs_pct:.1f}%, SG&A: {report.margin.sga_pct:.1f}%).",
            "growth_prescription": f"Implement procurement discipline to reach target EBITDA margin of {report.margin.target_ebitda_margin:.1f}% (+{report.margin.uplift_potential:,.1f} uplift).",
            "severity": report.margin.severity,
            "metric_value": report.margin.ebitda_margin,
        },
        {
            "category": "Capital Allocation",
            "summary": f"ROIC is {report.roic.roic_pct:.1f}% vs WACC of {report.roic.wacc_pct:.1f}% (Spread: {report.roic.spread_pct:+.1f}%).",
            "growth_prescription": report.roic.optimal_capex_reallocation,
            "severity": report.roic.severity,
            "metric_value": report.roic.roic_pct,
        },
    ]

    severity_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: severity_order.get(x["severity"], 3))
    return items

