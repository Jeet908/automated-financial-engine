# Open-Source 6-Gate Accounting Invariant Benchmark Report

> **Evaluation Standard**: Ind AS (Schedule III) &middot; US GAAP (FASB ASC) &middot; IFRS (IASB)  
> **Benchmark Command**: `python benchmarks/run_benchmark.py`  
> **Sovereign Engine Status**: **100% INVARIANTS PASSED (`0.000000e+00` Balance Sheet Plug)**  

---

## 1. Executive Summary & Audit Scorecard

This benchmark evaluates the **Deterministic MarketLens Quantitative Engine** against an unverified / generic Large Language Model (LLM) financial modeling baseline across **India Ind AS / Schedule III**, **US GAAP**, and **UK / EU IFRS** corporate filings.

While LLMs generate syntactically plausible financial narratives, their floating-point calculations drift across projection periods, violating core double-entry accounting axioms. The MarketLens engine guarantees exact algebraic balance with zero plug figures.

| Metric / Audit Check | MarketLens Engine (Deterministic) | Generic LLM Baseline (Unverified) | Advantage |
| :--- | :---: | :---: | :---: |
| **Balance Sheet Max Discrepancy** | **`0.000000e+00`** | `~0.1850` | **Exact Zero Drift ($Assets \equiv L+E$)** |
| **6/6 Accounting Invariant Pass Rate** | **`100.0%` (18/18)** | `27.8%` (5/18) | **+72.2% Integrity Guard** |
| **Excel Formula Errors (`#REF!`/`#DIV/0!`)** | **`0`** | `42` | **Zero Broken References** |
| **SHA-256 Lineage Cryptographic Coverage** | **`100.0%`** | `0.0%` | **Full Big-4 Provenance Chain** |
| **Average End-to-End Solve Latency** | **`14.85 ms`** | `2,916.67 ms` | **~196x Faster Execution** |

---

## 2. Multi-Standard Accounting Regime Breakdown

### India Ind AS / Schedule III (Ind AS Division II)
- **Sector / Test Bed**: Indian FMCG & Agribusiness (`kaveri_foods`)
- **Currency & Denomination**: INR Crores (8 periods evaluated: FY23A - FY30E)
- **DCF Fair Value**: Rs 252.07 (WACC: 11.59%, Enterprise Value: Rs 2,486.9 Cr)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate 1 | Balance Sheet Balance Identity ($Assets \equiv L+E$) | `0.000000e+00` | ✅ PASS |
| Gate 2 | Cash Flow Roll-Forward Identity ($\Delta\text{Cash} \equiv \text{Close} - \text{Open}$) | `0.000000e+00` | ✅ PASS |
| Gate 3 | Retained Earnings Roll-Forward ($\text{RE}_t \equiv \text{RE}_{t-1} + \text{PAT} - \text{Div}$) | `0.000000e+00` | ✅ PASS |
| Gate 4 | Fixed Assets Net Block Roll-Forward ($\text{NB}_t \equiv \text{NB}_{t-1} + \text{Capex} - \text{Depr}$) | `0.000000e+00` | ✅ PASS |
| Gate 5 | Debt Amortization Schedule ($\text{Debt}_t \equiv \text{Debt}_{t-1} - \text{Repay}$) | `0.000000e+00` | ✅ PASS |
| Gate 6 | Working Capital Schedule ($\Delta\text{NWC} \equiv \text{NWC}_t - \text{NWC}_{t-1}$) | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`14.20 ms`** vs. LLM drift of **`0.1420`** in **`2,740.0 ms`**.

---

### US GAAP (FASB ASC 606 / Regulation S-X)
- **Sector / Test Bed**: Enterprise Cloud & SaaS (`saas_growth`)
- **Currency & Denomination**: USD Millions (8 periods evaluated: FY23A - FY30E)
- **DCF Fair Value**: $48.75 (WACC: 9.25%, Enterprise Value: $3,150.0 M)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate 1 | Balance Sheet Balance Identity ($Assets \equiv L+E$) | `0.000000e+00` | ✅ PASS |
| Gate 2 | Cash Flow Roll-Forward Identity ($\Delta\text{Cash} \equiv \text{Close} - \text{Open}$) | `0.000000e+00` | ✅ PASS |
| Gate 3 | Retained Earnings Roll-Forward ($\text{RE}_t \equiv \text{RE}_{t-1} + \text{PAT} - \text{Div}$) | `0.000000e+00` | ✅ PASS |
| Gate 4 | Fixed Assets Net Block Roll-Forward ($\text{NB}_t \equiv \text{NB}_{t-1} + \text{Capex} - \text{Depr}$) | `0.000000e+00` | ✅ PASS |
| Gate 5 | Debt Amortization Schedule ($\text{Debt}_t \equiv \text{Debt}_{t-1} - \text{Repay}$) | `0.000000e+00` | ✅ PASS |
| Gate 6 | Working Capital Schedule ($\Delta\text{NWC} \equiv \text{NWC}_t - \text{NWC}_{t-1}$) | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`15.10 ms`** vs. LLM drift of **`0.0980`** in **`3,120.0 ms`**.

---

### UK / EU IFRS (IAS 1 / IAS 7 / ESEF iXBRL)
- **Sector / Test Bed**: Heavy Industrial & Aerospace (`industrial_corp`)
- **Currency & Denomination**: GBP Millions (8 periods evaluated: FY23A - FY30E)
- **DCF Fair Value**: £112.40 (WACC: 8.75%, Enterprise Value: £4,820.0 M)

| Invariant Gate | Check Name | Discrepancy | Result |
| :---: | :--- | :---: | :---: |
| Gate 1 | Balance Sheet Balance Identity ($Assets \equiv L+E$) | `0.000000e+00` | ✅ PASS |
| Gate 2 | Cash Flow Roll-Forward Identity ($\Delta\text{Cash} \equiv \text{Close} - \text{Open}$) | `0.000000e+00` | ✅ PASS |
| Gate 3 | Retained Earnings Roll-Forward ($\text{RE}_t \equiv \text{RE}_{t-1} + \text{PAT} - \text{Div}$) | `0.000000e+00` | ✅ PASS |
| Gate 4 | Fixed Assets Net Block Roll-Forward ($\text{NB}_t \equiv \text{NB}_{t-1} + \text{Capex} - \text{Depr}$) | `0.000000e+00` | ✅ PASS |
| Gate 5 | Debt Amortization Schedule ($\text{Debt}_t \equiv \text{Debt}_{t-1} - \text{Repay}$) | `0.000000e+00` | ✅ PASS |
| Gate 6 | Working Capital Schedule ($\Delta\text{NWC} \equiv \text{NWC}_t - \text{NWC}_{t-1}$) | `0.000000e+00` | ✅ PASS |

**Regime Comparison**: MarketLens solved with **`0.000000e+00`** error in **`15.25 ms`** vs. LLM drift of **`0.1850`** in **`2,890.0 ms`**.

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
