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
    test_pain_points_diagnostic,
    test_regional_accounting_rulebook,
    test_saas_plan_catalog,
)
from tests.test_distributed_architecture import (
    test_postgresql_engine_normalization_and_pooling,
    test_strict_tenant_row_isolation,
    test_concurrent_reserve_job_locking,
    test_celery_daily_benchmark_refresh_task,
    test_s3_tenant_object_key_and_presigned_url,
)
from tests.test_audit_ledger_and_otel import (
    test_canonical_source_fact_determinism,
    test_merkle_tree_root_determinism_and_tamper_detection,
    test_four_stage_provenance_chain_integrity,
    test_audit_ledger_database_persistence_and_query_isolation,
    test_public_audit_verification_endpoints,
    test_excel_deliverable_provenance_tab_embedding,
    test_opentelemetry_observability_and_schema_drift,
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
        ("C-Suite Operational Pain Points & Alpha Diagnostic", test_pain_points_diagnostic),
        ("Regional Accounting Rulebook Jurisdiction Detector", test_regional_accounting_rulebook),
        ("Multi-Currency SaaS Plan Catalog & 14-Day Trial", test_saas_plan_catalog),
        ("PostgreSQL Connection Pooling & URL Normalization", test_postgresql_engine_normalization_and_pooling),
        ("Strict Tenant-Level Row Isolation & Query Scoping", test_strict_tenant_row_isolation),
        ("Concurrent reserve_job() Row-Level Quota Locking", test_concurrent_reserve_job_locking),
        ("Celery Worker Pool & Scheduled 00:00 UTC Beat Task", test_celery_daily_benchmark_refresh_task),
        ("Signed S3/R2 Object Storage & 900s Presigned URLs", test_s3_tenant_object_key_and_presigned_url),
        ("Deterministic SourceFact Fingerprinting & Invariant Hashing", test_canonical_source_fact_determinism),
        ("SHA-256 Merkle Root & Discrepancy Tamper-Detection", test_merkle_tree_root_determinism_and_tamper_detection),
        ("4-Stage Cryptographic Provenance Chain & Gate Checks", test_four_stage_provenance_chain_integrity),
        ("Audit Ledger Database Persistence & Strict Tenant Isolation", test_audit_ledger_database_persistence_and_query_isolation),
        ("Public Audit Verification API Endpoints (/verify & /verify-hash)", test_public_audit_verification_endpoints),
        ("Excel Deliverable Provenance Tab (09_Audit_&_Lineage_Ledger)", test_excel_deliverable_provenance_tab_embedding),
        ("OpenTelemetry Observability, SLA Monitoring & Schema Drift", test_opentelemetry_observability_and_schema_drift),
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
