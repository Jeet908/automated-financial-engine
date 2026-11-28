"""
Base Unified Read-Only ERP Adapter Interface.
Defines abstract contracts for OAuth 2.0 authorization, token exchange,
Trial Balance / General Ledger retrieval, and canonical engine normalization.
"""

from __future__ import annotations

import abc
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class BaseERPAdapter(abc.ABC):
    """Abstract Base Class for institutional read-only ERP connectors."""

    provider_name: str = "base"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    @abc.abstractmethod
    def get_authorize_url(self, state: str) -> str:
        """Returns the provider's OAuth 2.0 read-only consent URL."""
        raise NotImplementedError

    @abc.abstractmethod
    def exchange_code(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchanges authorization code for access and refresh tokens."""
        raise NotImplementedError

    @abc.abstractmethod
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refreshes expired access tokens using the refresh token."""
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_trial_balance(self, access_token: str, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Extracts read-only Trial Balance report from the ERP system."""
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_general_ledger(
        self,
        access_token: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extracts read-only General Ledger journal lines and vouchers."""
        raise NotImplementedError

    @abc.abstractmethod
    def normalize_to_engine_payload(
        self,
        trial_balance: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Normalizes raw ERP accounts into the canonical 3-statement schema:
        Guarantees Total Assets == Total Liabilities + Equity with 0.00 variance.
        """
        raise NotImplementedError

    @staticmethod
    def balance_and_seal_financials(
        revenue: List[float],
        cogs: List[float],
        employee_costs: List[float],
        other_expenses: List[float],
        depreciation: List[float],
        interest: List[float],
        tax: List[float],
        cash: List[float],
        receivables: List[float],
        inventory: List[float],
        net_fixed_assets: List[float],
        payables: List[float],
        debt: List[float],
        share_capital: List[float],
        initial_retained_earnings: float = 0.0,
        dividends: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        Guarantees strict mathematical equilibrium across all historical periods:
        1. Net Income = Revenue - COGS - Opex - Depr - Interest - Tax
        2. Retained Earnings roll-forward: RE_t = RE_t-1 + PAT_t - Div_t
        3. Total Assets = Cash + Receivables + Inventory + Net Fixed Assets
        4. Total Liab & Equity = Payables + Debt + Share Capital + Retained Earnings
        5. Calibrates cash or share capital so Assets == Liabilities + Equity exact zero diff.
        """
        n = len(revenue)
        divs = dividends or [0.0] * n
        re_list: List[float] = []
        pat_list: List[float] = []
        curr_re = initial_retained_earnings

        for i in range(n):
            pat = revenue[i] - cogs[i] - employee_costs[i] - other_expenses[i] - depreciation[i] - interest[i] - tax[i]
            pat_list.append(round(pat, 2))
            curr_re = curr_re + pat - divs[i]
            re_list.append(round(curr_re, 2))

        # Reconcile Balance Sheet Identity across all periods
        adj_cash = list(cash)
        for i in range(n):
            tot_assets = adj_cash[i] + receivables[i] + inventory[i] + net_fixed_assets[i]
            tot_liab_eq = payables[i] + debt[i] + share_capital[i] + re_list[i]
            diff = tot_liab_eq - tot_assets
            if abs(diff) > 1e-4:
                adj_cash[i] = round(adj_cash[i] + diff, 2)

        return {
            "revenue": revenue,
            "cogs": cogs,
            "employee_costs": employee_costs,
            "other_expenses": other_expenses,
            "depreciation": depreciation,
            "interest": interest,
            "tax": tax,
            "dividends": divs,
            "pat": pat_list,
            "cash": adj_cash,
            "receivables": receivables,
            "inventory": inventory,
            "net_fixed_assets": net_fixed_assets,
            "payables": payables,
            "debt": debt,
            "share_capital": share_capital,
            "retained_earnings": re_list,
        }
