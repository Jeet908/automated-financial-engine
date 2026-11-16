"""
Unit and integration tests for strict accounting identities across all templates.
"""

import pytest
from financial_engine.engine import FinancialEngine


def test_kaveri_foods_accounting_identities():
    engine = FinancialEngine.from_template("kaveri_foods")
    model = engine.solve(run_mc=False)
    cert = model.audit_certificate

    assert cert.is_valid, f"Accounting identities failed: {cert.summary()}"
    assert cert.overall_status == "PASSED"

    # Verify balance sheet identity in every single period
    for diff in model.balance_sheet.balance_check:
        assert abs(diff) < 1e-4, f"Balance sheet discrepancy: {diff}"

    # Verify all checks in audit certificate passed
    for check in cert.checks:
        assert check.passed, f"Check {check.name} failed: {check.details}"


def test_saas_growth_accounting_identities():
    engine = FinancialEngine.from_template("saas_growth")
    model = engine.solve(run_mc=False)
    cert = model.audit_certificate

    assert cert.is_valid, f"SaaS model accounting failed: {cert.summary()}"
    for diff in model.balance_sheet.balance_check:
        assert abs(diff) < 1e-4, f"Balance discrepancy in SaaS: {diff}"


def test_industrial_corp_accounting_identities():
    engine = FinancialEngine.from_template("industrial_corp")
    model = engine.solve(run_mc=False)
    cert = model.audit_certificate

    assert cert.is_valid, f"Industrial model accounting failed: {cert.summary()}"
    for diff in model.balance_sheet.balance_check:
        assert abs(diff) < 1e-4, f"Balance discrepancy in Industrial: {diff}"
