"""
DuPont 5-Way ROE Decomposition Engine.
Decomposes Return on Equity (ROE) into 5 core multiplicative drivers:
ROE = Operating Margin * Asset Turnover * Leverage Factor * Interest Burden * Tax Burden
Mathematical Invariant:
(EBIT / Revenue) * (Revenue / Total Assets) * (Total Assets / Total Equity) * (EBT / EBIT) * (Net Income / EBT) == (Net Income / Total Equity)
"""

from __future__ import annotations

from typing import Any, Dict, List


def compute_dupont_decomposition(model: Any) -> Dict[str, Any]:
    """
    Computes DuPont 5-Way Decomposition across historical and projected horizons.
    Asserts mathematically that the product of the 5 factors equals ROE within 1e-6.
    """
    cfg = model.config
    years = list(cfg.metadata.historical_years) + list(cfg.metadata.projection_years)
    inc = model.income_statement
    bs = model.balance_sheet

    periods_data: List[Dict[str, Any]] = []
    prior_factors = None

    for i, year in enumerate(years):
        rev = float(inc.revenue[i]) if i < len(inc.revenue) else 0.0
        ebit = float(inc.ebit[i]) if i < len(inc.ebit) else 0.0
        ebt = float(inc.pbt[i]) if i < len(inc.pbt) else 0.0
        net_inc = float(inc.pat[i]) if i < len(inc.pat) else 0.0

        assets = float(bs.total_assets[i]) if i < len(bs.total_assets) else 0.0
        sc = float(bs.share_capital[i]) if i < len(bs.share_capital) else 0.0
        re = float(bs.retained_earnings[i]) if i < len(bs.retained_earnings) else 0.0
        equity = sc + re

        # Factor 1: Operating Margin = EBIT / Revenue
        op_margin = (ebit / rev) if rev > 0 else 0.0

        # Factor 2: Asset Turnover = Revenue / Total Assets
        asset_turnover = (rev / assets) if assets > 0 else 0.0

        # Factor 3: Leverage Factor (Equity Multiplier) = Total Assets / Total Equity
        leverage_factor = (assets / equity) if equity > 0 else 0.0

        # Factor 4: Interest Burden = EBT / EBIT
        interest_burden = (ebt / ebit) if ebit != 0 else 1.0

        # Factor 5: Tax Burden = Net Income / EBT
        tax_burden = (net_inc / ebt) if ebt != 0 else 1.0

        # Resulting ROE = Net Income / Total Equity
        roe = (net_inc / equity) if equity > 0 else 0.0

        # Factor product
        product = op_margin * asset_turnover * leverage_factor * interest_burden * tax_burden
        discrepancy = abs(product - roe)
        identity_verified = discrepancy < 1e-6

        # YoY basis point changes (1 bp = 0.0001, so 100 bps = 1.00%)
        if prior_factors:
            yoy_op_margin = round((op_margin - prior_factors["op_margin"]) * 10000, 1)
            yoy_asset_turnover = round((asset_turnover - prior_factors["asset_turnover"]) * 10000, 1)
            yoy_leverage = round((leverage_factor - prior_factors["leverage_factor"]) * 10000, 1)
            yoy_interest = round((interest_burden - prior_factors["interest_burden"]) * 10000, 1)
            yoy_tax = round((tax_burden - prior_factors["tax_burden"]) * 10000, 1)
            yoy_roe = round((roe - prior_factors["roe"]) * 10000, 1)
        else:
            yoy_op_margin = 0.0
            yoy_asset_turnover = 0.0
            yoy_leverage = 0.0
            yoy_interest = 0.0
            yoy_tax = 0.0
            yoy_roe = 0.0

        prior_factors = {
            "op_margin": op_margin,
            "asset_turnover": asset_turnover,
            "leverage_factor": leverage_factor,
            "interest_burden": interest_burden,
            "tax_burden": tax_burden,
            "roe": roe,
        }

        periods_data.append({
            "year": year,
            "is_projection": year.endswith("E"),
            "operating_margin": {
                "ratio": round(op_margin, 6),
                "pct": round(op_margin * 100, 2),
                "numerator": round(ebit, 2),
                "denominator": round(rev, 2),
                "numerator_label": "EBIT",
                "denominator_label": "Revenue",
                "yoy_bps": yoy_op_margin,
            },
            "asset_turnover": {
                "ratio": round(asset_turnover, 6),
                "multiple": round(asset_turnover, 3),
                "numerator": round(rev, 2),
                "denominator": round(assets, 2),
                "numerator_label": "Revenue",
                "denominator_label": "Total Assets",
                "yoy_bps": yoy_asset_turnover,
            },
            "leverage_factor": {
                "ratio": round(leverage_factor, 6),
                "multiple": round(leverage_factor, 3),
                "numerator": round(assets, 2),
                "denominator": round(equity, 2),
                "numerator_label": "Total Assets",
                "denominator_label": "Total Equity",
                "yoy_bps": yoy_leverage,
            },
            "interest_burden": {
                "ratio": round(interest_burden, 6),
                "pct": round(interest_burden * 100, 2),
                "is_drag": interest_burden < 1.0,
                "numerator": round(ebt, 2),
                "denominator": round(ebit, 2),
                "numerator_label": "EBT",
                "denominator_label": "EBIT",
                "yoy_bps": yoy_interest,
            },
            "tax_burden": {
                "ratio": round(tax_burden, 6),
                "pct": round(tax_burden * 100, 2),
                "is_drag": tax_burden < 1.0,
                "numerator": round(net_inc, 2),
                "denominator": round(ebt, 2),
                "numerator_label": "Net Income",
                "denominator_label": "EBT",
                "yoy_bps": yoy_tax,
            },
            "roe": {
                "ratio": round(roe, 6),
                "pct": round(roe * 100, 2),
                "numerator": round(net_inc, 2),
                "denominator": round(equity, 2),
                "numerator_label": "Net Income",
                "denominator_label": "Total Equity",
                "yoy_bps": yoy_roe,
            },
            "identity_verified": identity_verified,
            "max_discrepancy": discrepancy,
        })

    return {
        "years": years,
        "periods": periods_data,
        "active_year_default": years[0] if years else "FY25A",
        "formula": "Operating Margin * Asset Turnover * Leverage Factor * Interest Burden * Tax Burden == ROE",
        "all_identities_verified": all(p["identity_verified"] for p in periods_data),
    }
