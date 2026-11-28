"""
Custom exceptions and diagnostic warnings for financial modeling and valuation.
"""


class FinancialEngineError(Exception):
    """Base exception for all financial engine errors."""
    pass


class AccountingIdentityViolation(FinancialEngineError):
    """Raised when an essential accounting identity fails (e.g., Balance Sheet discrepancy)."""
    pass


class CashDeficitError(FinancialEngineError):
    """Raised when projected cash balance falls below critical insolvency thresholds."""
    pass


class ValuationDivergenceError(FinancialEngineError):
    """Raised when DCF parameters cause mathematical singularities (e.g. WACC <= terminal growth)."""
    pass


class ModelInputError(FinancialEngineError):
    """Raised when input arrays have inconsistent lengths or invalid data types."""
    pass
