"""
coa_agent.py — Agentic Chart-of-Accounts (CoA) Semantic Mapping Agent.

Resolves non-standard private ERP / Tally / Zoho / QuickBooks / PDF line-item labels
into canonical `NormalizedFinancials` fields with explicit confidence scores,
without ever fabricating or altering numeric values.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd


_CANONICAL_SYNONYMS: Dict[str, Tuple[str, ...]] = {
    "revenue": (
        "sales turnover", "gross sales", "operating income", "subscription revenue",
        "saas revenue", "recurring revenue", "total receipts", "income from operations",
        "revenue from contracts", "fee income", "service revenue", "top line",
    ),
    "cogs": (
        "cost of sales", "cost of services", "direct expenses", "direct cost",
        "subcontracting charges", "raw material consumed", "purchases", "cost of delivery",
        "hosting and infrastructure cost", "manufacturing expenses",
    ),
    "gross_profit": ("gross margin", "gross surplus", "contribution margin"),
    "ebitda": (
        "operating profit before depreciation", "ebitda", "operating cash profit",
        "pbdita", "earnings before interest tax depreciation",
    ),
    "depreciation": (
        "depreciation and amortisation", "depreciation and amortization",
        "depreciation expense", "amortization of intangibles", "d&a", "wear and tear",
    ),
    "ebit": ("operating profit", "operating income", "ebit", "pbit", "profit before interest and tax"),
    "interest": ("finance cost", "interest expense", "borrowing cost", "bank interest", "interest charges"),
    "pbt": ("profit before tax", "earnings before tax", "ebt", "net profit before tax"),
    "tax": ("income tax expense", "provision for taxation", "corporate tax", "current and deferred tax"),
    "pat": (
        "net profit", "net income", "profit after tax", "bottom line",
        "profit for the year", "net surplus", "earnings after tax",
    ),
    "cash": (
        "cash and bank", "cash at bank", "bank balances", "cash on hand",
        "cash and equivalents", "liquid funds", "treasury cash",
    ),
    "receivables": (
        "trade debtors", "sundry debtors", "accounts receivable", "trade receivables",
        "billed receivables", "unbilled revenue receivables", "customer balances",
    ),
    "inventory": ("closing stock", "stock in trade", "finished goods", "work in progress", "inventories"),
    "net_fixed_assets": (
        "fixed assets", "net block", "tangible assets", "property plant and equipment",
        "ppe net", "machinery and equipment", "right of use assets",
    ),
    "other_assets": (
        "other current assets", "other non current assets", "prepaid expenses",
        "loans and advances", "security deposits", "intangible assets",
    ),
    "total_assets": ("total assets", "assets total", "sum of assets", "balance sheet assets"),
    "payables": (
        "trade creditors", "sundry creditors", "accounts payable", "trade payables",
        "vendor payables", "supplier balances",
    ),
    "debt": (
        "total debt", "term loans", "bank borrowings", "working capital loan",
        "secured loans", "unsecured loans", "overdraft", "lease liabilities", "credit facilities",
    ),
    "other_liabilities": (
        "other current liabilities", "accrued expenses", "provisions",
        "statutory dues", "deferred revenue", "unearned revenue", "gst payable",
    ),
    "share_capital": ("equity capital", "paid up share capital", "common stock", "issued capital"),
    "retained_earnings": (
        "reserves and surplus", "accumulated profits", "retained earnings",
        "general reserve", "other equity",
    ),
    "total_equity": ("shareholders equity", "net worth", "owners equity", "total equity", "partners capital"),
    "total_liab_equity": ("total liabilities and equity", "total equity and liabilities", "total liabilities"),
    "cfo": ("cash flow from operating activities", "operating cash flow", "net cash from operations"),
    "cfi": ("cash flow from investing activities", "investing cash flow", "net cash used in investing"),
    "cff": ("cash flow from financing activities", "financing cash flow", "net cash from financing"),
    "capex": ("capital expenditure", "purchase of fixed assets", "additions to ppe", "capex"),
    "dividends": ("dividends paid", "equity dividend", "interim dividend"),
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class CoAMappingItem:
    raw_label: str
    canonical_field: str
    confidence: float
    method: str = "semantic_ontology"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_label": self.raw_label,
            "canonical_field": self.canonical_field,
            "confidence": round(self.confidence, 3),
            "method": self.method,
        }


def _normalize_label(text: str) -> str:
    return " ".join(_TOKEN_RE.findall(text.lower()))


def _parse_numeric(raw: Any) -> Optional[float]:
    if raw is None:
        return None
    s = str(raw).strip()
    if s in ("", "-", "—", "nan", "NaN", "None"):
        return None
    # Handle accounting parentheses e.g. (1,234.50) -> -1234.50
    neg = s.startswith("(") and s.endswith(")")
    cleaned = s.strip("()").replace(",", "").replace("₹", "").replace("$", "").replace("€", "").strip()
    try:
        val = float(cleaned)
        return -val if neg else val
    except (TypeError, ValueError):
        return None


def _score_label_similarity(norm_label: str, candidate: str) -> float:
    if not norm_label or not candidate:
        return 0.0
    if norm_label == candidate:
        return 1.0
    tokens_a = set(norm_label.split())
    tokens_b = set(candidate.split())
    jaccard = len(tokens_a & tokens_b) / max(1, len(tokens_a | tokens_b))
    seq_ratio = difflib.SequenceMatcher(None, norm_label, candidate).ratio()
    return 0.55 * jaccard + 0.45 * seq_ratio


class CoAMappingAgent:
    """
    Semantic Chart-of-Accounts mapper for non-standard private financial statements.
    """

    def __init__(self, min_confidence: float = 0.62) -> None:
        self.min_confidence = min_confidence

    def map_unmatched_rows(
        self,
        df: pd.DataFrame,
        period_cols: List[str],
        already_mapped_fields: Set[str],
    ) -> Tuple[Dict[str, List[Optional[float]]], Dict[str, Any]]:
        """
        Inspect DataFrame rows for labels not yet mapped to canonical fields.
        Returns (mapped_series_by_field, coa_mapping_report).
        """
        if df.empty or len(df.columns) < 2 or not period_cols:
            return {}, {"agent_used": False, "mapped_count": 0, "mappings": [], "unmapped_labels": []}

        label_col = df.columns[0]
        mapped_series: Dict[str, List[Optional[float]]] = {}
        mappings: List[CoAMappingItem] = []
        unmapped_labels: List[str] = []
        claimed_fields = set(already_mapped_fields)

        for _, row in df.iterrows():
            raw_label = str(row.get(label_col, "") or "").strip()
            if not raw_label or raw_label.lower() in ("nan", "none"):
                continue

            norm = _normalize_label(raw_label)
            if not norm:
                continue

            best_field: Optional[str] = None
            best_score = 0.0
            for field_name, synonyms in _CANONICAL_SYNONYMS.items():
                if field_name in claimed_fields:
                    continue
                for syn in synonyms:
                    score = _score_label_similarity(norm, syn)
                    if score > best_score:
                        best_score = score
                        best_field = field_name

            if best_field and best_score >= self.min_confidence:
                vals = [_parse_numeric(row.get(col)) for col in period_cols]
                if any(v is not None for v in vals):
                    mapped_series[best_field] = vals
                    claimed_fields.add(best_field)
                    mappings.append(
                        CoAMappingItem(
                            raw_label=raw_label,
                            canonical_field=best_field,
                            confidence=best_score,
                        )
                    )
                    continue

            unmapped_labels.append(raw_label)

        report = {
            "agent_used": True,
            "mapped_count": len(mappings),
            "mappings": [m.to_dict() for m in mappings],
            "unmapped_labels": unmapped_labels[:25],
        }
        return mapped_series, report
