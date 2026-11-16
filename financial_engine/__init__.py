"""
Automated Financial Modeling & Valuation Engine.
A production-ready, 100% zero-touch quantitative financial modeling framework.
"""

from financial_engine.core.types import (
    Currency,
    ScenarioType,
    TerminalValueMethod,
    CompanyMetadata,
    HistoricalFinancials,
    ProjectionAssumptions,
    ValuationInputs,
)
from financial_engine.core.config import ModelConfiguration
from financial_engine.core.accounting import AccountingVerifier, AuditCertificate
from financial_engine.engine import FinancialEngine, FinancialModel
from financial_engine.cli import run_pipeline

__version__ = "1.0.0"
__author__ = "Principal Financial Architect & Quantitative Engineer"

__all__ = [
    "Currency",
    "ScenarioType",
    "TerminalValueMethod",
    "CompanyMetadata",
    "HistoricalFinancials",
    "ProjectionAssumptions",
    "ValuationInputs",
    "ModelConfiguration",
    "AccountingVerifier",
    "AuditCertificate",
    "FinancialEngine",
    "FinancialModel",
    "run_pipeline",
]
