"""
Accounting identity verifier and model audit certificate generator.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from financial_engine.core.exceptions import AccountingIdentityViolation


@dataclass
class AuditCheckItem:
    name: str
    passed: bool
    max_discrepancy: float
    tolerance: float
    details: str


@dataclass
class AuditCertificate:
    is_valid: bool
    checks: List[AuditCheckItem] = field(default_factory=list)
    overall_status: str = "PASSED"

    def summary(self) -> str:
        lines = [
            "=" * 60,
            "FINANCIAL MODEL ACCOUNTING INTEGRITY AUDIT CERTIFICATE",
            "=" * 60,
            f"Overall Status: {self.overall_status}",
            "-" * 60,
        ]
        for c in self.checks:
            mark = "✓ [PASS]" if c.passed else "✗ [FAIL]"
            lines.append(f"{mark} {c.name:<35} Max Err: {c.max_discrepancy:.6e} (Tol: {c.tolerance:.6e})")
            if not c.passed:
                lines.append(f"     Details: {c.details}")
        lines.append("=" * 60)
        return "\n".join(lines)


class AccountingVerifier:
    """Verifies all structural accounting identities across all years."""

    def __init__(self, tolerance: float = 1e-4):
        self.tolerance = tolerance

    def verify_all(self, model_data: Dict[str, Any]) -> AuditCertificate:
        checks: List[AuditCheckItem] = []

        # 1. Balance Sheet Identity: Total Assets == Total Liabilities + Equity
        assets = model_data.get("bs_total_assets", [])
        liab_equity = model_data.get("bs_total_liab_equity", [])
        bs_diffs = [abs(a - le) for a, le in zip(assets, liab_equity)]
        max_bs_err = max(bs_diffs) if bs_diffs else 0.0
        bs_pass = max_bs_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Balance Sheet Balance Identity",
            passed=bs_pass,
            max_discrepancy=max_bs_err,
            tolerance=self.tolerance,
            details=f"Max difference {max_bs_err} across {len(assets)} periods"
        ))

        # 2. Cash Reconciliation: Ending Cash - Opening Cash == Net Change in Cash
        opening_cash = model_data.get("cf_opening_cash", [])
        closing_cash = model_data.get("cf_closing_cash", [])
        net_cf = model_data.get("cf_net_change", [])
        cf_diffs = []
        for i in range(len(net_cf)):
            expected_close = opening_cash[i] + net_cf[i]
            cf_diffs.append(abs(closing_cash[i] - expected_close))
        max_cf_err = max(cf_diffs) if cf_diffs else 0.0
        cf_pass = max_cf_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Cash Flow Roll-Forward Identity",
            passed=cf_pass,
            max_discrepancy=max_cf_err,
            tolerance=self.tolerance,
            details=f"Max cash roll error {max_cf_err}"
        ))

        # 3. Retained Earnings Roll-Forward: Closing RE == Opening RE + PAT - Dividends
        re_open = model_data.get("re_opening", [])
        re_close = model_data.get("re_closing", [])
        pat = model_data.get("pat", [])
        dividends = model_data.get("dividends", [])
        re_diffs = []
        for i in range(len(re_close)):
            expected_re = re_open[i] + pat[i] - dividends[i]
            re_diffs.append(abs(re_close[i] - expected_re))
        max_re_err = max(re_diffs) if re_diffs else 0.0
        re_pass = max_re_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Retained Earnings Roll-Forward",
            passed=re_pass,
            max_discrepancy=max_re_err,
            tolerance=self.tolerance,
            details=f"Max retained earnings discrepancy {max_re_err}"
        ))

        # 4. Net Fixed Assets Roll-Forward: Closing NB == Opening NB + Capex - Depr
        nb_open = model_data.get("nb_opening", [])
        nb_close = model_data.get("nb_closing", [])
        capex = model_data.get("capex", [])
        depr = model_data.get("depreciation", [])
        fa_diffs = []
        for i in range(len(nb_close)):
            expected_nb = nb_open[i] + capex[i] - depr[i]
            fa_diffs.append(abs(nb_close[i] - expected_nb))
        max_fa_err = max(fa_diffs) if fa_diffs else 0.0
        fa_pass = max_fa_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Fixed Assets Net Block Roll-Forward",
            passed=fa_pass,
            max_discrepancy=max_fa_err,
            tolerance=self.tolerance,
            details=f"Max fixed assets roll error {max_fa_err}"
        ))

        # 5. Debt Roll-Forward: Closing Debt == Opening Debt - Repayment
        debt_open = model_data.get("debt_opening", [])
        debt_close = model_data.get("debt_closing", [])
        repayment = model_data.get("debt_repayment", [])
        debt_diffs = []
        for i in range(len(debt_close)):
            expected_debt = debt_open[i] - repayment[i]
            debt_diffs.append(abs(debt_close[i] - expected_debt))
        max_debt_err = max(debt_diffs) if debt_diffs else 0.0
        debt_pass = max_debt_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Debt Amortization Roll-Forward",
            passed=debt_pass,
            max_discrepancy=max_debt_err,
            tolerance=self.tolerance,
            details=f"Max debt roll discrepancy {max_debt_err}"
        ))

        # 6. Working Capital Roll-Forward: Change in NWC == NWC_t - NWC_t-1
        nwc = model_data.get("nwc", [])
        delta_nwc = model_data.get("delta_nwc", [])
        nwc_diffs = []
        # delta_nwc is defined for indices 1 to len(nwc)-1
        for i in range(1, len(nwc)):
            if i - 1 < len(delta_nwc):
                diff = abs((nwc[i] - nwc[i - 1]) - delta_nwc[i - 1])
                nwc_diffs.append(diff)
        max_nwc_err = max(nwc_diffs) if nwc_diffs else 0.0
        nwc_pass = max_nwc_err <= self.tolerance
        checks.append(AuditCheckItem(
            name="Working Capital Change Reconciliation",
            passed=nwc_pass,
            max_discrepancy=max_nwc_err,
            tolerance=self.tolerance,
            details=f"Max NWC change discrepancy {max_nwc_err}"
        ))

        all_passed = all(c.passed for c in checks)
        return AuditCertificate(
            is_valid=all_passed,
            checks=checks,
            overall_status="PASSED" if all_passed else "FAILED"
        )
