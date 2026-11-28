"""
StandardDetector: heuristics-based detection of accounting standard,
currency/unit, and fiscal-year configuration from a raw DataFrame.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import pandas as pd


# ---------------------------------------------------------------------------
# Keyword catalogs
# ---------------------------------------------------------------------------

# Schedule-III / Ind AS headers (Balance Sheet & P&L line names from Companies Act 2013)
_IND_AS_KEYWORDS = {
    "other equity", "other comprehensive income", "oci",
    "property plant and equipment", "right-of-use", "right of use",
    "lease liability", "ind as", "schedule iii", "schedule-iii",
    "deferred tax liability", "deferred tax asset",
    "other financial liabilities", "other financial assets",
    "non-controlling interest", "minority interest",
    "exceptional items", "revenue from operations",
    "cost of materials consumed", "employee benefit expense",
    "finance costs", "depreciation and amortisation",
    "trade receivables", "trade payables", "sundry creditors", "sundry debtors",
    "tally", "tallyprime", "zoho books", "equity share capital",
}

# Classic Indian GAAP (pre-Ind AS, Companies Act 1956 / AS series)
_INDIAN_GAAP_KEYWORDS = {
    "share capital", "reserves and surplus", "secured loans",
    "unsecured loans", "net block", "capital work-in-progress",
    "preliminary expenses", "miscellaneous expenditure",
    "deferred revenue expenditure", "as 15", "as 22",
    "profit and loss account",  # balance sheet exhibit
}

# IFRS keywords
_IFRS_KEYWORDS = {
    "ifrs", "ias", "other components of equity",
    "finance lease obligation", "investment property",
    "biological assets", "hyperinflationary",
    "functional currency", "translation reserve",
}

# US GAAP keywords
_US_GAAP_KEYWORDS = {
    "us_gaap", "us-gaap", "us gaap", "sec", "edgar", "sec edgar",
    "common stock", "additional paid-in capital", "apic",
    "treasury stock", "accumulated other comprehensive loss",
    "aoci", "gaap", "asc 606", "asc 842",
    "cost of goods sold", "selling general and administrative",
    "sg&a", "diluted eps", "basic eps",
    "10-k", "10-q", "10k", "10q",
}

# Startup / MIS keywords
_STARTUP_KEYWORDS = {
    "arr", "mrr", "gmv", "take rate", "burn rate", "runway",
    "cac", "ltv", "nrr", "net revenue retention",
    "monthly active users", "mau", "dau",
    "unit economics", "cohort",
}

# Currency symbols / patterns
_CURRENCY_PATTERNS = {
    "INR": [r"₹", r"\binr\b", r"\brs\.?\b", r"\brupee"],
    "USD": [r"\$", r"\busd\b", r"\bdollar"],
    "EUR": [r"€", r"\beur\b", r"\beuro"],
    "GBP": [r"£", r"\bgbp\b", r"\bpound"],
}

# Unit patterns → (unit name, multiplier vs base currency)
_UNIT_PATTERNS = [
    (r"\bcrore", "Crores", 1e7),
    (r"\blakh",  "Lakhs",  1e5),
    (r"\bbillion", "Billions", 1e9),
    (r"\bmillion", "Millions", 1e6),
    (r"\bthousand", "Thousands", 1e3),
]

# Month-name → month-number for fiscal year end detection
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _flatten_text(df: pd.DataFrame) -> str:
    """Collapse all header and cell text to a single lower-case string."""
    parts: List[str] = []
    # Include metadata attributes if present (e.g. banner / title text from ERP extracts)
    if hasattr(df, "attrs"):
        for v in df.attrs.values():
            if isinstance(v, str):
                parts.append(v)
            elif isinstance(v, (list, tuple)):
                parts.extend([str(x) for x in v])
    # Column names
    for col in df.columns:
        parts.append(str(col))
    # First column (row labels) + all string cells
    for col in df.columns:
        for val in df[col]:
            if isinstance(val, str):
                parts.append(val)
    return " ".join(parts).lower()


def _score_keywords(text: str, keywords: set) -> int:
    return sum(1 for kw in keywords if kw in text)


class StandardDetector:
    """
    Detects accounting standard, currency/unit, and fiscal-year config
    from a raw pandas DataFrame representing financial statements.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_accounting_standard(self, df: pd.DataFrame) -> str:
        """
        Returns one of: "IND_AS", "INDIAN_GAAP", "IFRS", "US_GAAP", "STARTUP_MIS"
        Uses keyword scoring on all text in the dataframe.
        """
        text = _flatten_text(df)

        scores: Dict[str, int] = {
            "STARTUP_MIS":  _score_keywords(text, _STARTUP_KEYWORDS),
            "IND_AS":       _score_keywords(text, _IND_AS_KEYWORDS),
            "INDIAN_GAAP":  _score_keywords(text, _INDIAN_GAAP_KEYWORDS),
            "IFRS":         _score_keywords(text, _IFRS_KEYWORDS),
            "US_GAAP":      _score_keywords(text, _US_GAAP_KEYWORDS),
        }

        # Startup detection wins outright if any startup KPIs found
        if scores["STARTUP_MIS"] >= 1:
            return "STARTUP_MIS"

        # Explicit standard declaration override
        if "us_gaap" in text or "us gaap" in text or "sec edgar" in text:
            return "US_GAAP"
        if "ind as" in text or "schedule iii" in text or "schedule-iii" in text:
            return "IND_AS"
        if "ifrs" in text or "ias" in text:
            return "IFRS"
        if "indian gaap" in text or "as 15" in text or "as 22" in text:
            return "INDIAN_GAAP"

        best = max(scores, key=lambda k: scores[k])
        if scores[best] == 0:
            # Default: assume Ind AS for Indian context
            return "IND_AS"
        return best

    def detect_currency_unit(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Returns:
            {
                "currency":   "INR" | "USD" | "EUR" | "GBP",
                "unit":       "Thousands" | "Lakhs" | "Crores" | "Millions" | "Billions",
                "multiplier": float   # number of base currency units per reported unit
            }
        """
        text = _flatten_text(df)

        # Detect currency
        currency = "INR"  # default for Indian context
        for curr, patterns in _CURRENCY_PATTERNS.items():
            if any(re.search(p, text, re.IGNORECASE) for p in patterns):
                currency = curr
                break

        # Detect unit
        unit = "Crores"       # sensible Indian default
        multiplier = 1e7
        for pattern, unit_name, mult in _UNIT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                unit = unit_name
                multiplier = mult
                break

        return {"currency": currency, "unit": unit, "multiplier": multiplier}

    def detect_fiscal_year(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Returns:
            {
                "fy_end_month": int,            # e.g. 3 for March (Indian FY)
                "periodicity":  "Annual" | "Quarterly" | "Monthly",
                "columns":      list[str]       # detected period column headers
            }
        """
        columns = [str(c) for c in df.columns]
        col_text = " ".join(columns).lower()

        # Detect periodicity
        if re.search(r"\bq[1-4]\b|quarter", col_text, re.IGNORECASE):
            periodicity = "Quarterly"
        elif re.search(r"\bjan\b|\bfeb\b|\bapr\b|\bjul\b|\boct\b|month", col_text, re.IGNORECASE):
            periodicity = "Monthly"
        else:
            periodicity = "Annual"

        # Detect fiscal year end month from column headers like "FY24", "Mar-24", "Dec-23"
        fy_end_month = 3  # Indian default = March

        # Look for month names in columns
        for col in columns:
            col_lower = col.lower()
            for month_str, month_num in _MONTH_MAP.items():
                if month_str in col_lower:
                    fy_end_month = month_num
                    break

        # US / calendar-year companies typically end in December
        if re.search(r"\bdec\b", col_text):
            fy_end_month = 12
        elif re.search(r"\bmar\b", col_text):
            fy_end_month = 3
        elif re.search(r"\bjun\b", col_text):
            fy_end_month = 6
        elif re.search(r"\bsep\b", col_text):
            fy_end_month = 9

        # Period columns: columns that look like years or FY labels or calendar dates
        date_pattern = re.compile(
            r"(fy\s*\d{2,4}|20\d{2}|19\d{2}|q[1-4]|\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[-/\s]?\d{2,4}|\d{1,2}[-/](mar|dec|jun|sep|\d{1,2})[-/]\d{2,4})",
            re.IGNORECASE
        )
        period_cols = [
            c for c in columns
            if date_pattern.search(c)
        ]
        if not period_cols:
            period_cols = columns[1:]  # assume first column is labels

        return {
            "fy_end_month": fy_end_month,
            "periodicity": periodicity,
            "columns": period_cols,
        }
