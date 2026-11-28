"""
DataNormalizer: maps raw financial DataFrame rows to a canonical
NormalizedFinancials Pydantic model, regardless of accounting standard.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pandas as pd
from pydantic import BaseModel, Field

from src.ingestion.coa_agent import CoAMappingAgent


# ---------------------------------------------------------------------------
# Pydantic output model
# ---------------------------------------------------------------------------

class NormalizedFinancials(BaseModel):
    """Canonical representation of financial statements after normalization."""

    # --- Detection metadata ---
    standard: str = ""
    currency: str = "INR"
    unit: str = "Crores"
    multiplier: float = 1e7
    fiscal_year_end: int = 3
    periods: List[str] = Field(default_factory=list)

    # --- Income Statement ---
    revenue: List[Optional[float]] = Field(default_factory=list)
    cogs: List[Optional[float]] = Field(default_factory=list)
    gross_profit: List[Optional[float]] = Field(default_factory=list)
    ebitda: List[Optional[float]] = Field(default_factory=list)
    depreciation: List[Optional[float]] = Field(default_factory=list)
    ebit: List[Optional[float]] = Field(default_factory=list)
    interest: List[Optional[float]] = Field(default_factory=list)
    pbt: List[Optional[float]] = Field(default_factory=list)
    tax: List[Optional[float]] = Field(default_factory=list)
    pat: List[Optional[float]] = Field(default_factory=list)

    # --- Balance Sheet: Assets ---
    cash: List[Optional[float]] = Field(default_factory=list)
    receivables: List[Optional[float]] = Field(default_factory=list)
    inventory: List[Optional[float]] = Field(default_factory=list)
    net_fixed_assets: List[Optional[float]] = Field(default_factory=list)
    other_assets: List[Optional[float]] = Field(default_factory=list)
    total_assets: List[Optional[float]] = Field(default_factory=list)

    # --- Balance Sheet: Liabilities & Equity ---
    payables: List[Optional[float]] = Field(default_factory=list)
    debt: List[Optional[float]] = Field(default_factory=list)
    other_liabilities: List[Optional[float]] = Field(default_factory=list)
    share_capital: List[Optional[float]] = Field(default_factory=list)
    retained_earnings: List[Optional[float]] = Field(default_factory=list)
    total_equity: List[Optional[float]] = Field(default_factory=list)
    total_liab_equity: List[Optional[float]] = Field(default_factory=list)

    # --- Cash Flow Statement ---
    cfo: List[Optional[float]] = Field(default_factory=list)
    cfi: List[Optional[float]] = Field(default_factory=list)
    cff: List[Optional[float]] = Field(default_factory=list)
    net_change_in_cash: List[Optional[float]] = Field(default_factory=list)
    opening_cash: List[Optional[float]] = Field(default_factory=list)
    closing_cash: List[Optional[float]] = Field(default_factory=list)

    # --- Other items ---
    dividends: List[Optional[float]] = Field(default_factory=list)
    capex: List[Optional[float]] = Field(default_factory=list)

    # --- Classification flag ---
    is_startup: bool = False

    # --- Accounting standard adjustment flags (pass-through metadata) ---
    lease_standard: str = ""       # e.g. "IND_AS_116", "IFRS_16", "ASC_842"
    revenue_standard: str = ""     # e.g. "IND_AS_115", "IFRS_15", "ASC_606"
    lease_adjustment_applied: bool = False
    revenue_adjustment_applied: bool = False
    coa_mapping_report: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Row-label matching helpers
# ---------------------------------------------------------------------------

# Maps canonical field names → lists of regex patterns that match row labels
_ROW_PATTERNS: Dict[str, List[str]] = {
    # Income Statement
    "revenue":        [r"revenue from operations", r"gross turnover", r"total revenue",
                       r"operating revenue", r"sales accounts", r"revenue", r"net sales",
                       r"total income", r"net revenue", r"turnover", r"gmv", r"arr", r"mrr"],
    "cogs":           [r"cost of materials consumed", r"purchase of stock-in-trade",
                       r"changes in inventories", r"cost of (goods|revenue|sales)",
                       r"material cost", r"cost of material", r"\bcogs\b", r"direct cost"],
    "gross_profit":   [r"gross profit", r"gross margin"],
    "ebitda":         [r"\bebitda\b", r"operating profit before", r"operating profit before depreciation"],
    "depreciation":   [r"depreciation (and|&) amortis", r"depreciation (and|&) amortiz",
                       r"depreciation", r"amortis", r"amortiz", r"\bda\b"],
    "ebit":           [r"\bebit\b", r"operating profit", r"profit from operations", r"operating income"],
    "interest":       [r"finance costs?", r"interest (expense|cost|paid)", r"borrowing cost", r"interest on"],
    "pbt":            [r"profit before exceptional items (and|&) tax", r"profit before tax",
                       r"\bpbt\b", r"income before tax"],
    "tax":            [r"tax expenses?", r"provision for tax", r"\btax\b", r"income tax",
                       r"current tax", r"deferred tax"],
    "pat":            [r"profit for the (year|period)", r"profit / \(loss\) for the period",
                       r"profit after tax", r"\bpat\b", r"net (profit|income|loss)", r"net earnings"],

    # Balance Sheet – Assets
    "cash":           [r"cash and bank balances?", r"cash and cash equiv", r"balances with banks",
                       r"bank balance", r"\bcash\b"],
    "receivables":    [r"trade receivables?", r"accounts receiv", r"sundry debtors?", r"debtors"],
    "inventory":      [r"inventories", r"\binventor", r"stock-in-trade", r"\bstock\b"],
    "net_fixed_assets": [r"property, plant and equipment", r"property plant", r"net (fixed asset|block|property)",
                          r"ppe", r"tangible asset", r"fixed assets?"],
    "other_assets":   [r"other.*asset", r"other non-current", r"other current",
                       r"loans and advances", r"other financial asset", r"capital work-in-progress",
                       r"cwip", r"intangible"],
    "total_assets":   [r"total (non-current and current )?assets?"],

    # Balance Sheet – L&E
    "payables":       [r"trade payables?", r"accounts payable", r"sundry creditors?", r"creditors"],
    "debt":           [r"borrowings?", r"long-term borrowings?", r"short-term borrowings?",
                       r"\bdebt\b", r"loan", r"secured loan", r"unsecured loan", r"term loan",
                       r"finance lease", r"debt obligations?"],
    "other_liabilities": [r"other.*liabilit", r"other non-current", r"other current",
                           r"provisions", r"deferred liabilit", r"deferred tax liabilit"],
    "share_capital":  [r"equity share capital", r"share capital", r"common stock", r"paid.up capital"],
    "retained_earnings": [r"other equity", r"reserves and surplus", r"retained earning",
                           r"profit and loss (account|reserve)", r"accumulated (profit|deficit|other)"],
    "total_equity":   [r"total equity", r"shareholders.? funds", r"shareholders.? equity",
                       r"stockholders.? equity", r"net worth"],
    "total_liab_equity": [r"total equity and liabilities", r"total liabilities and equity",
                          r"total (liabilit|equity and liabilit|liab)"],

    # Cash Flow
    "cfo":            [r"(cash|net cash).*(operat)", r"operating activities"],
    "cfi":            [r"(cash|net cash).*(invest)", r"investing activities"],
    "cff":            [r"(cash|net cash).*(financ)", r"financing activities"],
    "net_change_in_cash": [r"net (change|increase|decrease) in cash",
                            r"net cash (increase|decrease|generated|used)"],
    "opening_cash":   [r"opening (cash|balance)", r"cash at (beginning|start)"],
    "closing_cash":   [r"closing (cash|balance)", r"cash at (end|close)"],

    # Other
    "dividends":      [r"dividend"],
    "capex":          [r"capex", r"capital expenditure", r"purchase of (ppe|fixed asset|property)"],
}


def _match_row(label: str, patterns: List[str]) -> bool:
    label_lower = label.lower().strip()
    return any(re.search(p, label_lower) for p in patterns)


def _extract_series(df: pd.DataFrame, field: str, period_cols: List[str]) -> List[Optional[float]]:
    """
    Scan DataFrame rows for the first row whose first-column label matches
    the field's patterns, then return numeric values for each period column.
    """
    patterns = _ROW_PATTERNS.get(field, [])
    if not patterns:
        return [None] * len(period_cols)

    label_col = df.columns[0]
    for _, row in df.iterrows():
        label = str(row.get(label_col, ""))
        if _match_row(label, patterns):
            vals: List[Optional[float]] = []
            for col in period_cols:
                raw = row.get(col)
                try:
                    vals.append(float(raw) if raw is not None and str(raw).strip() not in ("", "-", "nan") else None)
                except (ValueError, TypeError):
                    vals.append(None)
            return vals

    return [None] * len(period_cols)


def _derive_lease_standard(standard: str) -> str:
    mapping = {
        "IND_AS": "IND_AS_116",
        "IFRS":   "IFRS_16",
        "US_GAAP": "ASC_842",
        "INDIAN_GAAP": "AS_19",
        "STARTUP_MIS": "IND_AS_116",
    }
    return mapping.get(standard, "IND_AS_116")


def _derive_revenue_standard(standard: str) -> str:
    mapping = {
        "IND_AS": "IND_AS_115",
        "IFRS":   "IFRS_15",
        "US_GAAP": "ASC_606",
        "INDIAN_GAAP": "AS_9",
        "STARTUP_MIS": "IND_AS_115",
    }
    return mapping.get(standard, "IND_AS_115")


# ---------------------------------------------------------------------------
# Main normalizer
# ---------------------------------------------------------------------------

class DataNormalizer:
    """
    Converts a raw financial DataFrame + detection results into a
    NormalizedFinancials Pydantic instance with canonical field names.
    """

    def normalize(
        self,
        raw_df: pd.DataFrame,
        detection_result: Dict[str, Any],
    ) -> NormalizedFinancials:
        """
        Parameters
        ----------
        raw_df : pd.DataFrame
            Raw table with row labels in the first column and period
            values in subsequent columns.
        detection_result : dict
            Merged output from StandardDetector methods:
            {standard, currency, unit, multiplier, fy_end_month,
             periodicity, columns}

        Returns
        -------
        NormalizedFinancials
        """
        standard      = detection_result.get("standard", "IND_AS")
        currency      = detection_result.get("currency", "INR")
        unit          = detection_result.get("unit", "Crores")
        multiplier    = detection_result.get("multiplier", 1e7)
        fy_end_month  = detection_result.get("fy_end_month", 3)
        period_cols   = detection_result.get("columns", [])
        is_startup    = standard == "STARTUP_MIS"

        if not period_cols:
            # Fallback: treat all columns except the first as period columns
            period_cols = [str(c) for c in raw_df.columns[1:]]

        # --- Extract all canonical series (regex first, then Agentic CoA fallback) ---
        raw_series: Dict[str, List[Optional[float]]] = {
            field_name: _extract_series(raw_df, field_name, period_cols)
            for field_name in _ROW_PATTERNS
        }
        already_mapped = {
            f for f, vals in raw_series.items() if any(v is not None for v in vals)
        }
        agent_series, coa_report = CoAMappingAgent().map_unmatched_rows(
            raw_df, period_cols, already_mapped
        )
        for field_name, vals in agent_series.items():
            raw_series[field_name] = vals

        def get(field: str) -> List[Optional[float]]:
            return raw_series.get(field, [None] * len(period_cols))

        revenue       = get("revenue")
        cogs          = get("cogs")
        gross_profit  = get("gross_profit")
        ebitda        = get("ebitda")
        depreciation  = get("depreciation")
        ebit          = get("ebit")
        interest      = get("interest")
        pbt           = get("pbt")
        tax           = get("tax")
        pat           = get("pat")

        # Derive gross_profit if missing
        if all(v is None for v in gross_profit):
            gross_profit = [
                (r - c) if (r is not None and c is not None) else None
                for r, c in zip(revenue, cogs)
            ]

        # Derive ebitda if missing
        if all(v is None for v in ebitda):
            ebitda = [
                (e + d) if (e is not None and d is not None) else None
                for e, d in zip(ebit, depreciation)
            ]

        # Derive ebit if missing
        if all(v is None for v in ebit):
            ebit = [
                (e - d) if (e is not None and d is not None) else None
                for e, d in zip(ebitda, depreciation)
            ]

        cash              = get("cash")
        receivables       = get("receivables")
        inventory         = get("inventory")
        net_fixed_assets  = get("net_fixed_assets")
        other_assets      = get("other_assets")
        total_assets      = get("total_assets")
        payables          = get("payables")
        debt              = get("debt")
        other_liabilities = get("other_liabilities")
        share_capital     = get("share_capital")
        retained_earnings = get("retained_earnings")
        total_equity      = get("total_equity")
        total_liab_equity = get("total_liab_equity")

        cfo               = get("cfo")
        cfi               = get("cfi")
        cff               = get("cff")
        net_change_in_cash = get("net_change_in_cash")
        opening_cash      = get("opening_cash")
        closing_cash      = get("closing_cash")

        dividends         = get("dividends")
        capex             = get("capex")

        # --- Automatic Balance Sheet Invariant Reconciliation ---
        # Ensures other_assets and other_liabilities balance with reported total_assets / total_liab_equity
        for i in range(len(period_cols)):
            ta = total_assets[i] if i < len(total_assets) else None
            c = cash[i] if i < len(cash) else 0.0
            r = receivables[i] if i < len(receivables) else 0.0
            inv = inventory[i] if i < len(inventory) else 0.0
            nf = net_fixed_assets[i] if i < len(net_fixed_assets) else 0.0
            oa = other_assets[i] if i < len(other_assets) else None

            non_other_assets = (c or 0.0) + (r or 0.0) + (inv or 0.0) + (nf or 0.0)
            if ta is not None and (oa is None or abs((non_other_assets + (oa or 0.0)) - ta) > 1e-2):
                other_assets[i] = round(ta - non_other_assets, 2)

            tle = total_liab_equity[i] if i < len(total_liab_equity) else (ta if ta is not None else None)
            p = payables[i] if i < len(payables) else 0.0
            d = debt[i] if i < len(debt) else 0.0
            sc = share_capital[i] if i < len(share_capital) else 0.0
            re = retained_earnings[i] if i < len(retained_earnings) else 0.0
            ol = other_liabilities[i] if i < len(other_liabilities) else None

            non_other_liab = (p or 0.0) + (d or 0.0) + (sc or 0.0) + (re or 0.0)
            if tle is not None and (ol is None or abs((non_other_liab + (ol or 0.0)) - tle) > 1e-2):
                other_liabilities[i] = round(tle - non_other_liab, 2)

        return NormalizedFinancials(
            standard=standard,
            currency=currency,
            unit=unit,
            multiplier=multiplier,
            fiscal_year_end=fy_end_month,
            periods=[str(c) for c in period_cols],
            revenue=revenue,
            cogs=cogs,
            gross_profit=gross_profit,
            ebitda=ebitda,
            depreciation=depreciation,
            ebit=ebit,
            interest=interest,
            pbt=pbt,
            tax=tax,
            pat=pat,
            cash=cash,
            receivables=receivables,
            inventory=inventory,
            net_fixed_assets=net_fixed_assets,
            other_assets=other_assets,
            total_assets=total_assets,
            payables=payables,
            debt=debt,
            other_liabilities=other_liabilities,
            share_capital=share_capital,
            retained_earnings=retained_earnings,
            total_equity=total_equity,
            total_liab_equity=total_liab_equity,
            cfo=cfo,
            cfi=cfi,
            cff=cff,
            net_change_in_cash=net_change_in_cash,
            opening_cash=opening_cash,
            closing_cash=closing_cash,
            dividends=dividends,
            capex=capex,
            is_startup=is_startup,
            lease_standard=_derive_lease_standard(standard),
            revenue_standard=_derive_revenue_standard(standard),
            lease_adjustment_applied=False,    # pass-through flag
            revenue_adjustment_applied=False,  # pass-through flag
            coa_mapping_report=coa_report,
        )
