"""
Standalone Python Test Runner.
Runs all unit and integration test suites without requiring pytest CLI.
"""

import sys
import traceback
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from tests.test_accounting_identities import (
    test_kaveri_foods_accounting_identities,
    test_saas_growth_accounting_identities,
    test_industrial_corp_accounting_identities,
)
from tests.test_kaveri_benchmark import test_kaveri_foods_benchmark_values
from tests.test_dcf_valuation import (
    test_wacc_calculation,
    test_hamada_relevering,
    test_valuation_divergence_guard,
)
from tests.test_simulation import (
    test_sensitivity_dimensions_and_monotonicity,
    test_monte_carlo_distribution,
)
from tests.test_excel_generation import test_excel_generation
from tests.test_cli import test_cli_pipeline_execution
from tests.test_advanced_metrics import (
    test_roic_and_eva_computation,
    test_dupont_5way_reconciliation,
    test_football_field_bands,
)


def main():
    test_suite = [
        ("Kaveri Foods Accounting Identities", test_kaveri_foods_accounting_identities),
        ("SaaS Growth Accounting Identities", test_saas_growth_accounting_identities),
        ("Industrial Corp Accounting Identities", test_industrial_corp_accounting_identities),
        ("Kaveri Foods 89-Step Benchmark Verification", test_kaveri_foods_benchmark_values),
        ("WACC & CAPM Cost of Capital Calculation", test_wacc_calculation),
        ("Hamada Relevering Equation", test_hamada_relevering),
        ("Valuation Divergence Singularity Guard", test_valuation_divergence_guard),
        ("2-Way Sensitivity Dimensions & Monotonicity", test_sensitivity_dimensions_and_monotonicity),
        ("Monte Carlo Stochastic Distribution & VaR", test_monte_carlo_distribution),
        ("Institutional Live-Formula Excel Workbook", lambda: test_excel_generation(ROOT_DIR / "artifacts")),
        ("End-to-End CLI Pipeline & Artifact Generation", lambda: test_cli_pipeline_execution(ROOT_DIR / "artifacts")),
        ("ROIC & Economic Value Added (EVA) Engine", test_roic_and_eva_computation),
        ("DuPont 5-Way ROE Decomposition Reconciliation", test_dupont_5way_reconciliation),
        ("Valuation Football Field Range Generator", test_football_field_bands),
    ]

    print("=" * 70)
    print("RUNNING AUTOMATED FINANCIAL MODELING ENGINE TEST SUITE")
    print("=" * 70)

    passed = 0
    failed = 0

    for name, test_fn in test_suite:
        try:
            test_fn()
            print(f" [PASS] {name}")
            passed += 1
        except Exception as e:
            print(f" [FAIL] {name}")
            print(f"        Error: {e}")
            traceback.print_exc()
            failed += 1

    print("=" * 70)
    print(f"TEST RESULTS: {passed} PASSED, {failed} FAILED (TOTAL: {len(test_suite)})")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
