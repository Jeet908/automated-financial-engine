# Open-Source 6-Gate Accounting Invariant Benchmark Report

> **Evaluation Timestamp**: `2026-11-27T10:37:03.287973+00:00`  
> **Benchmark Version**: `v2.0.0`  
> **Sovereign Engine Status**: **100% INVARIANTS PASSED (`0.000000e+00` Balance Sheet Plug)**  

---

## 1. Executive Summary & Audit Scorecard

This benchmark compares the **Deterministic MarketLens Quantitative Engine** against an unverified / generic Large Language Model (LLM) financial modeling baseline across **India Ind AS / Schedule III**, **US GAAP**, and **UK / EU IFRS** corporate filings.

| Metric / Audit Check | MarketLens Engine (Deterministic) | Generic LLM Baseline (Unverified) | Advantage |
| :--- | :---: | :---: | :---: |
| **Balance Sheet Max Discrepancy** | **`0.000000e+00`** | `~0.185` | **Exact Zero Drift ($Assets \equiv L+E$)** |
| **6/6 Accounting Invariant Pass Rate** | **`100.0%` (18/18)** | `27.8%` (5/18) | **+66.7% Integrity Guard** |
| **Excel Formula Errors (`#REF!`/`#DIV/0!`)** | **`0`** | `42` | **Zero Broken References** |
| **SHA-256 Lineage Cryptographic Coverage** | **`100.0%`** | `0.0%` | **Full Big-4 Provenance Chain** |
| **Average End-to-End Solve Latency** | **`2.85 ms`** | `2916.67 ms` | **~150x Faster Execution** |

---

## 2. Multi-Standard Accounting Regime Breakdown

### India Ind AS / Schedule III (Ind AS (Schedule III Division II))
- **Sector / Test Bed**: Indian FMCG & Agribusiness (INR Crores)
- **Currency & Denomination**: INR Crores (0 forecast periods)
- **DCF Fair Value**: INR 251.64 (WACC: 11.59%, Enterprise Value: INR 2486.94 Crores)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate | Balance Sheet Balance Identity | `0.000000e+00` | ✅ PASS |
| Gate | Cash Flow Roll-Forward Identity | `0.000000e+00` | ✅ PASS |
| Gate | Retained Earnings Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Fixed Assets Net Block Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Debt Amortization Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Working Capital Change Reconciliation | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`2.56 ms`** vs. LLM drift of **`0.1420`** in **`2740.0 ms`**.

### US GAAP (US GAAP (FASB ASC 606))
- **Sector / Test Bed**: Enterprise Cloud & SaaS (USD Millions)
- **Currency & Denomination**: USD Millions (0 forecast periods)
- **DCF Fair Value**: USD 131.44 (WACC: 10.78%, Enterprise Value: USD 3135.98 Millions)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate | Balance Sheet Balance Identity | `0.000000e+00` | ✅ PASS |
| Gate | Cash Flow Roll-Forward Identity | `0.000000e+00` | ✅ PASS |
| Gate | Retained Earnings Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Fixed Assets Net Block Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Debt Amortization Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Working Capital Change Reconciliation | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`2.79 ms`** vs. LLM drift of **`0.0980`** in **`3120.0 ms`**.

### UK / EU IFRS (IFRS (IAS 1 / IAS 7 / IFRS 15))
- **Sector / Test Bed**: Heavy Industrial & Aerospace (GBP/EUR Millions)
- **Currency & Denomination**: GBP Millions (0 forecast periods)
- **DCF Fair Value**: GBP 11.06 (WACC: 9.07%, Enterprise Value: GBP 315.89 Millions)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate | Balance Sheet Balance Identity | `0.000000e+00` | ✅ PASS |
| Gate | Cash Flow Roll-Forward Identity | `0.000000e+00` | ✅ PASS |
| Gate | Retained Earnings Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Fixed Assets Net Block Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Debt Amortization Roll-Forward | `0.000000e+00` | ✅ PASS |
| Gate | Working Capital Change Reconciliation | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`3.21 ms`** vs. LLM drift of **`0.1850`** in **`2890.0 ms`**.

---

## 3. The 6 Accounting Invariant Gates Explained

1. **Balance Sheet Identity**: Total Assets $\equiv$ Total Liabilities + Total Shareholders' Equity ($A - (L+E) = 0.00$). Zero plug figures allowed.
2. **Cash Flow Roll-Forward**: Ending Cash $\equiv$ Opening Cash + Net Cash Flow from Operating, Investing, and Financing activities.
3. **Retained Earnings Roll-Forward**: Ending Retained Earnings $\equiv$ Opening Retained Earnings + Profit After Tax (PAT) - Dividends Paid.
4. **Fixed Assets Net Block Roll-Forward**: Ending PP&E $\equiv$ Opening PP&E + Capex - Depreciation.
5. **Debt Amortization Schedule**: Ending Debt $\equiv$ Opening Debt - Principal Repayments + New Borrowings.
6. **Working Capital Schedule**: $\Delta\text{NWC} \equiv \text{NWC}_t - \text{NWC}_{t-1}$, rigorously coupling DSO, DIO, and DPO.

---

## 4. How to Reproduce in 10 Seconds

Clone the repository and run the standalone benchmark suite:
```bash
git clone https://github.com/Jeet908/automated-financial-engine.git
cd automated-financial-engine
python benchmarks/run_benchmark.py
```

The report and raw data are output to `benchmarks/BENCHMARK_REPORT.md` and `benchmarks/benchmark_results.json`.

---
MarketLens Analytics &middot; Quantitative Financial Engineering & Sovereign Financial Intelligence