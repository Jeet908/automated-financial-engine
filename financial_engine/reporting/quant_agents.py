"""
quant_agents.py — Hybrid Agentic Post-Solve Quant Reviewer & IC Thesis Synthesizer.

Design Principle:
  Deterministic math (`FinancialEngine` / `AccountingVerifier`) remains 100% invariant.
  These agents inspect solved outputs to:
    1. Critique quantitative anomalies (low-beta WACC, terminal value concentration,
       WACC-TGR floor proximity, working capital / payables drift, Tier-3 fallback, ROIC < WACC).
    2. Synthesize company-specific Investment Committee (IC) thesis pillars grounded
       strictly in the solved financial metrics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class QuantAnomaly:
    code: str
    severity: str  # "HIGH" | "MEDIUM" | "LOW"
    title: str
    metric: str
    recommendation: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "metric": self.metric,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class QuantReviewReport:
    status: str  # "clean" | "attention" | "critical"
    anomalies: Tuple[QuantAnomaly, ...] = field(default_factory=tuple)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "anomaly_count": len(self.anomalies),
            "anomalies": [a.to_dict() for a in self.anomalies],
            "summary": self.summary,
        }


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        f = float(val)
        return default if (f != f) else f  # NaN guard
    except (TypeError, ValueError):
        return default


def _extract_latest_margin_pct(base_scenario: Dict[str, Any]) -> Tuple[float, float]:
    """Return (latest_ebitda_margin_pct, latest_gross_margin_pct) from base scenario."""
    inc = base_scenario.get("income_statement", {}) if isinstance(base_scenario, dict) else {}
    rev_map = inc.get("revenue", {})
    ebitda_map = inc.get("ebitda", {})
    gp_map = inc.get("gross_profit", {})

    if not isinstance(rev_map, dict) or not rev_map:
        return 0.0, 0.0

    periods = list(rev_map.keys())
    last_p = periods[-1]
    rev = _safe_float(rev_map.get(last_p), 0.0)
    if rev <= 0:
        return 0.0, 0.0

    ebitda = _safe_float(ebitda_map.get(last_p), 0.0) if isinstance(ebitda_map, dict) else 0.0
    gp = _safe_float(gp_map.get(last_p), 0.0) if isinstance(gp_map, dict) else 0.0
    return (ebitda / rev) * 100.0, (gp / rev) * 100.0


def review_quant_anomalies(
    engine_output: Dict[str, Any],
    meta: Optional[Dict[str, Any]] = None,
    pain_points: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Post-solve Quant Reviewer Agent.
    Audits solved DCF, WACC, working capital, and provenance metadata for IC-relevant anomalies.
    """
    meta = meta or {}
    base = engine_output.get("Base", engine_output.get("base", {})) if isinstance(engine_output, dict) else {}
    dcf_base = base.get("dcf", base.get("dcf_results", {})) if isinstance(base, dict) else {}
    pp = pain_points or base.get("pain_points") or {}

    anomalies: List[QuantAnomaly] = []

    wacc = _safe_float(base.get("wacc", dcf_base.get("wacc", 0.0)), 0.0)
    if wacc > 1.0:
        wacc /= 100.0
    beta = _safe_float(dcf_base.get("beta", 1.0), 1.0)
    tgr = _safe_float(dcf_base.get("terminal_growth_rate", 0.025), 0.025)
    if tgr > 1.0:
        tgr /= 100.0

    ev = _safe_float(dcf_base.get("enterprise_value", 0.0), 0.0)
    pv_tv = _safe_float(dcf_base.get("pv_tv", 0.0), 0.0)
    tv_share = (pv_tv / ev) if ev > 0 else 0.0

    # 1. Low-Beta / Low-WACC Check
    if 0.0 < wacc < 0.065 or (0.0 < beta < 0.65):
        anomalies.append(
            QuantAnomaly(
                code="LOW_BETA_WACC",
                severity="HIGH" if wacc < 0.058 else "MEDIUM",
                title="Low Cost of Capital Sensitivity",
                metric=f"WACC {wacc:.2%} (Beta {beta:.2f})",
                recommendation="Defensive beta compresses discount rate; stress-test valuation at sector-median unlevered beta.",
            )
        )

    # 2. Terminal Value Concentration Check
    if tv_share > 0.75:
        anomalies.append(
            QuantAnomaly(
                code="TV_CONCENTRATION",
                severity="HIGH" if tv_share >= 0.85 else "MEDIUM",
                title="Terminal Value Concentration",
                metric=f"PV(TV) = {tv_share:.1%} of Enterprise Value",
                recommendation="Over 75% of EV resides in perpetuity; validate exit multiple cross-check and steady-state ROIC.",
            )
        )

    # 3. WACC - TGR Spread Floor Check
    if wacc > 0.0 and (wacc - tgr) <= 0.015:
        anomalies.append(
            QuantAnomaly(
                code="WACC_TGR_SPREAD_NARROW",
                severity="HIGH",
                title="Narrow WACC–TGR Perpetuity Spread",
                metric=f"Spread = {(wacc - tgr):.2%} (WACC {wacc:.2%} vs. TGR {tgr:.2%})",
                recommendation="Perpetuity denominator is narrow; upper-right sensitivity cells may hit N/A floor.",
            )
        )

    # 4. Working Capital / Payables Classification Drift
    ccc_info = pp.get("ccc", {}) if isinstance(pp, dict) else {}
    dpo = _safe_float(ccc_info.get("dpo"), 0.0)
    ccc_days = _safe_float(ccc_info.get("ccc_days"), 0.0)
    if dpo > 120.0 or ccc_days < -60.0:
        anomalies.append(
            QuantAnomaly(
                code="WC_PAYABLES_DRIFT",
                severity="MEDIUM",
                title="Elevated Payables / Negative CCC Signal",
                metric=f"DPO {dpo:.1f}d | CCC {ccc_days:.1f}d",
                recommendation="Verify reported_accounts_payable excludes accrued/other current liabilities.",
            )
        )

    # 5. ROIC vs WACC Value Destruction Check
    roic_info = pp.get("roic", {}) if isinstance(pp, dict) else {}
    if roic_info.get("value_destruction") is True:
        roic_pct = _safe_float(roic_info.get("roic_pct"), 0.0)
        wacc_pct = _safe_float(roic_info.get("wacc_pct"), wacc * 100.0)
        anomalies.append(
            QuantAnomaly(
                code="NEGATIVE_ROIC_SPREAD",
                severity="HIGH",
                title="Negative ROIC–WACC Economic Spread",
                metric=f"ROIC {roic_pct:.1f}% vs. WACC {wacc_pct:.1f}%",
                recommendation="Incremental capital earns below cost of capital; prioritize working capital release over capex.",
            )
        )

    # 6. Tier-3 / Fallback Data Granularity Check
    data_tier = str(meta.get("data_tier", "")).lower()
    if meta.get("fallback_used") or "tier_3" in data_tier or "tier 3" in data_tier:
        anomalies.append(
            QuantAnomaly(
                code="TIER3_DATA_FALLBACK",
                severity="LOW",
                title="Tier-3 / Fallback Data Granularity",
                metric=f"Source Tier: {meta.get('data_tier', 'Fallback')}",
                recommendation="Cross-check extracted historicals against primary statutory filings before IC sign-off.",
            )
        )

    has_high = any(a.severity == "HIGH" for a in anomalies)
    status = "critical" if has_high and len(anomalies) >= 2 else ("attention" if anomalies else "clean")
    summary = (
        "All quantitative diagnostics within institutional guardrails."
        if not anomalies
        else f"Flagged {len(anomalies)} quantitative review item(s): " + "; ".join(a.title for a in anomalies[:3]) + "."
    )
    return QuantReviewReport(status=status, anomalies=tuple(anomalies), summary=summary).to_dict()


def generate_ic_thesis(
    engine_output: Dict[str, Any],
    meta: Dict[str, Any],
    dcf_base: Dict[str, Any],
    dcf_bull: Dict[str, Any],
    dcf_bear: Dict[str, Any],
    cagr: float,
    pain_points: Optional[Dict[str, Any]] = None,
    quant_review: Optional[Dict[str, Any]] = None,
) -> List[Tuple[str, List[str], str]]:
    """
    IC Thesis Agent.
    Synthesizes 4 company-specific Investment Committee pillars strictly grounded in solved metrics.
    Returns list of (title, bullets, accent_key) where accent_key in {'blue', 'emerald', 'amber', 'rose'}.
    """
    base = engine_output.get("Base", engine_output.get("base", {})) if isinstance(engine_output, dict) else {}
    pp = pain_points or base.get("pain_points") or {}
    q_rev = quant_review or review_quant_anomalies(engine_output, meta, pp)

    name = meta.get("name", "Enterprise")
    curr = meta.get("currency", "INR")
    std = meta.get("display_standard", "Ind AS / Indian GAAP")

    ev_base = _safe_float(dcf_base.get("enterprise_value"), 0.0)
    ev_bear = _safe_float(dcf_bear.get("enterprise_value"), 0.0)
    ev_bull = _safe_float(dcf_bull.get("enterprise_value"), 0.0)
    p_base = _safe_float(dcf_base.get("price_per_share"), 0.0)
    nd = _safe_float(dcf_base.get("net_debt"), 0.0)
    pv_fcf = sum(_safe_float(x) for x in (dcf_base.get("pv_ufcfs") or []))
    pv_tv = _safe_float(dcf_base.get("pv_tv"), 0.0)
    tv_share = (pv_tv / ev_base * 100.0) if ev_base > 0 else 0.0
    wacc = _safe_float(base.get("wacc", dcf_base.get("wacc", 0.10)), 0.10)
    if wacc > 1.0:
        wacc /= 100.0

    # Latest revenue & margins
    inc = base.get("income_statement", {}) if isinstance(base, dict) else {}
    rev_map = inc.get("revenue", {}) if isinstance(inc, dict) else {}
    last_rev = _safe_float(list(rev_map.values())[-1], 0.0) if isinstance(rev_map, dict) and rev_map else 0.0
    ebitda_m, gross_m = _extract_latest_margin_pct(base)

    margin_pp = pp.get("margin", {}) if isinstance(pp, dict) else {}
    if margin_pp.get("ebitda_margin"):
        ebitda_m = _safe_float(margin_pp.get("ebitda_margin"), ebitda_m)
    if margin_pp.get("gross_margin"):
        gross_m = _safe_float(margin_pp.get("gross_margin"), gross_m)
    sga_pct = _safe_float(margin_pp.get("sga_pct"), 0.0)

    ccc_pp = pp.get("ccc", {}) if isinstance(pp, dict) else {}
    ccc_days = _safe_float(ccc_pp.get("ccc_days"), 0.0)
    dso = _safe_float(ccc_pp.get("dso"), 0.0)
    dpo = _safe_float(ccc_pp.get("dpo"), 0.0)

    roic_pp = pp.get("roic", {}) if isinstance(pp, dict) else {}
    roic_pct = _safe_float(roic_pp.get("roic_pct"), 0.0)
    spread_pct = _safe_float(roic_pp.get("spread_pct"), 0.0)

    cmp_val = _safe_float(meta.get("current_market_price"), 0.0)
    upside_str = (
        f"{((p_base / cmp_val) - 1.0) * 100.0:+.1f}% vs. market ({curr} {cmp_val:,.2f})"
        if cmp_val > 0 and p_base > 0
        else f"Base Target {curr} {p_base:,.2f}/sh"
    )

    balance_sheet_note = (
        f"Net cash position of {curr} {abs(nd):,.1f} strengthens downside resilience."
        if nd < 0
        else f"Net debt of {curr} {nd:,.1f} bridges EV to implied equity value."
    )

    anomalies = q_rev.get("anomalies", [])
    top_risk = (
        f"{anomalies[0]['title']} ({anomalies[0]['metric']})."
        if anomalies
        else "No critical quant anomalies flagged across WACC, TV share, or working capital."
    )

    return [
        (
            "Growth & Scale Trajectory",
            [
                f"{name} models a {cagr * 100.0:.1f}% 5-year revenue CAGR under {std}.",
                f"Terminal-horizon revenue reaches {curr} {last_rev:,.1f} across the forecast." if last_rev > 0 else "Revenue baseline calibrated from audited historical statements.",
                f"Scenario EV spans {curr} {ev_bear:,.1f} (Bear) to {curr} {ev_bull:,.1f} (Bull).",
            ],
            "blue",
        ),
        (
            "Operating Margin & Leverage",
            [
                f"Gross margin anchors at {gross_m:.1f}% with EBITDA margin at {ebitda_m:.1f}%." if gross_m > 0 else f"Operating EBITDA margin stands at {ebitda_m:.1f}%.",
                f"SG&A intensity tracks at {sga_pct:.1f}% of revenue." if sga_pct > 0 else "Fixed-cost operating leverage modeled consistently across scenarios.",
                f"ROIC of {roic_pct:.1f}% yields a {spread_pct:+.1f}% spread over WACC." if roic_pct > 0 else f"Discount rate anchored at {wacc:.2%} CAPM WACC.",
            ],
            "emerald",
        ),
        (
            "Cash Conversion & Capital",
            [
                f"Cumulative PV of discrete UFCFs contributes {curr} {pv_fcf:,.1f} ({100.0 - tv_share:.1f}% of EV)." if ev_base > 0 else "Unlevered FCFs modeled from 3-statement working capital schedule.",
                f"Cash Conversion Cycle is {ccc_days:.1f} days (DSO {dso:.0f}d, DPO {dpo:.0f}d)." if (dso > 0 or dpo > 0) else "Working capital days normalized from historical balance sheet ratios.",
                balance_sheet_note,
            ],
            "amber",
        ),
        (
            "Valuation & Quant Guardrails",
            [
                f"Intrinsic DCF implies {upside_str} at {wacc:.2%} WACC.",
                f"Terminal Value accounts for {tv_share:.1f}% of Base Enterprise Value." if ev_base > 0 else "Terminal value calibrated via Gordon Growth perpetuity.",
                f"Quant Review: {top_risk}",
            ],
            "rose",
        ),
    ]
