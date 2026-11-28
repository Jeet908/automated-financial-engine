"""
Reporting generators: HTML Dashboard, Executive Memo, and Audit Report.
"""

from financial_engine.reporting.html_dashboard import HTMLDashboardGenerator
from financial_engine.reporting.executive_memo import ExecutiveMemoGenerator
from financial_engine.reporting.audit_report import AuditReportGenerator
from financial_engine.reporting.pain_points import diagnose, diagnose_pain_points

__all__ = [
    "HTMLDashboardGenerator",
    "ExecutiveMemoGenerator",
    "AuditReportGenerator",
    "diagnose",
    "diagnose_pain_points",
]
