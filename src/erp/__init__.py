"""
Read-Only ERP Connectors package.
Supports Xero, QuickBooks Online, Zoho Books, Oracle NetSuite, and TallyPrime.
"""

from typing import Dict, Type

from src.erp.base import BaseERPAdapter
from src.erp.netsuite_adapter import NetSuiteAdapter
from src.erp.quickbooks_adapter import QuickBooksAdapter
from src.erp.tally_adapter import TallyAdapter
from src.erp.xero_adapter import XeroAdapter
from src.erp.zoho_adapter import ZohoBooksAdapter

ERP_ADAPTERS: Dict[str, Type[BaseERPAdapter]] = {
    "xero": XeroAdapter,
    "quickbooks": QuickBooksAdapter,
    "zoho": ZohoBooksAdapter,
    "netsuite": NetSuiteAdapter,
    "tally": TallyAdapter,
}

__all__ = [
    "BaseERPAdapter",
    "XeroAdapter",
    "QuickBooksAdapter",
    "ZohoBooksAdapter",
    "NetSuiteAdapter",
    "TallyAdapter",
    "ERP_ADAPTERS",
]
