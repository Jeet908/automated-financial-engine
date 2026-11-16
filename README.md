# Automated Financial Modeling & Valuation Engine (100% Zero-Touch)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Accounting Invariants: 100% Passed](https://img.shields.io/badge/Accounting%20Invariants-100%25%20Passed-brightgreen.svg)]()
[![Balance Sheet Plug: 0.00](https://img.shields.io/badge/Balance%20Sheet%20Plug-0.000-brightgreen.svg)]()
[![Model Quality: Institutional Grade](https://img.shields.io/badge/Model%20Quality-Wall%20Street%20Standard-blue.svg)]()

> **An autonomous, production-ready quantitative financial engineering engine that designs, builds, stress-tests, audits, and packages full 3-statement financial models, supporting schedules, multi-method valuations (DCF, Comps, LBO), 2D sensitivity heatmaps, and 10,000-iteration Monte Carlo simulations with 100% zero manual touch.**

---

## 1. Executive Summary & Capabilities

The **Automated Financial Modeling & Valuation Engine** eliminates manual Excel errors and financial modeling drift by programmatically constructing fully dynamic, audit-ready corporate models. 

### Core Capabilities:
* **Self-Balancing 3-Statement Architecture:** Fully coupled Income Statement, Balance Sheet, and Cash Flow Statement. Total Assets identically equal Total Liabilities and Equity ($Assets - L\&E = 0.00$) across all historical and projected periods with **zero plug figures**.
* **Dynamic Supporting Schedules:**
  * **Working Capital Schedule:** Day-driver forecasting (DSO, DIO, DPO), accounts receivable, inventory, accounts payable, Net Working Capital (NWC), and $\Delta\text{NWC}$.
  * **Fixed Assets Schedule (PP&E Net Block):** Capex and depreciation roll-forwards ($\text{Closing} = \text{Opening} + \text{Capex} - \text{Depreciation}$).
  * **Debt & Financing Schedule:** Scheduled debt amortization, average debt balance tracking, and interest expense calculation.
  * **Equity & Retained Earnings Schedule:** Share capital stability and retained earnings roll-forward ($\text{Closing RE} = \text{Opening RE} + \text{PAT} - \text{Dividends}$).
* **Multi-Method Institutional Valuation Suite:**
  * **Unlevered DCF (FCFF):** NOPAT, tax adjustments, capex, working capital drag, and terminal value modeling via Gordon Growth perpetuity and Exit Multiple (EV/EBITDA).
  * **CAPM & WACC Calculator:** Cost of equity ($K_e = R_f + \beta \times \text{ERP}$), after-tax cost of debt ($K_d(1-t)$), Hamada levering/unlevering, and capital structure weighting.
  * **Enterprise to Equity Value Bridge:** Dynamic bridge incorporating cash, debt, and per-share equity value.
  * **Comparable Company Analysis (Comps):** Peer multiple percentiles (Min, 25th, Median, Mean, 75th, Max) for EV/EBITDA, P/E, and EV/Sales.
  * **Private Equity LBO Screening:** 5-year sponsor returns, debt paydown cash sweep, exit equity value, MoIC, and IRR.
* **Risk & Stochastic Simulation:**
  * **2-Way Sensitivity Matrix:** 5x5 dynamic grid of WACC vs. Terminal Growth Rate with center-case alignment.
  * **Scenario Manager:** Parameterized Bull, Base, and Bear cases with probability-weighted expected valuation.
  * **Monte Carlo Simulation:** 10,000 stochastic iterations perturbing WACC, growth, and cash flow trajectories to compute standard deviation, confidence intervals, 95% Value at Risk (VaR), and Probability of Undervaluation.
* **Multi-Format Institutional Packaging:**
  * **Live-Formula Excel Workbook (`.xlsx`):** Institutional Wall Street formatting, blue inputs, black formulas, green cross-sheet links, double accounting borders, and 3-color conditional formatting heatmaps.
  * **Interactive Standalone HTML5 Dashboard (`dashboard.html`):** Dark/light financial UI with statement viewers, waterfall charts, interactive heatmap, and scenario toggles.
  * **Investment Committee Memorandum (`investment_memo.md`):** Comprehensive executive tear-sheet.
  * **Machine-Readable JSON & Audit Certificates:** Structured outputs for downstream APIs and quantitative trading pipelines.

---

## 2. Benchmark Verification: Kaveri Foods Ltd

The engine is benchmarked and verified against the canonical 89-step quantitative financial modeling specification:

| Metric / Checkpoint | Expected Benchmark | Engine Output | Status |
| :--- | :---: | :---: | :---: |
| **Historical Revenue (FY23 / FY25)** | 1,000.0 / 1,243.2 Cr | 1,000.0 / 1,243.2 Cr | ✅ **VERIFIED** |
| **Historical Net Profit (FY25)** | 144.1 Cr | 144.1 Cr | ✅ **VERIFIED** |
| **Projected Revenue (FY26 / FY30)** | 1,392.4 / 2,001.4 Cr | 1,392.4 / 2,001.4 Cr | ✅ **VERIFIED** |
| **Projected EBITDA (FY30)** | 407.6 Cr | 407.6 Cr | ✅ **VERIFIED** |
| **Projected EBIT (FY30)** | 348.8 Cr | 348.8 Cr | ✅ **VERIFIED** |
| **Projected Net Profit (FY30)** | 254.0 Cr | 254.0 Cr | ✅ **VERIFIED** |
| **Projected Total Assets (FY30)** | 1,691.8 Cr | 1,691.8 Cr | ✅ **VERIFIED** |
| **Balance Sheet Discrepancy (All Years)** | **0.00 Cr** | **0.00 Cr** | ✅ **PERFECT BALANCE** |
| **WACC (Discount Rate)** | **11.6%** (11.5869%) | **11.6%** | ✅ **VERIFIED** |
| **PV of Terminal Value** | 1,877.9 Cr | 1,877.9 Cr | ✅ **VERIFIED** |
| **Enterprise Value** | 2,516.4 Cr | 2,516.4 Cr | ✅ **VERIFIED** |
| **Fair Value Per Share** | **Rs 252** | **Rs 252** | ✅ **VERIFIED** |
| **Sensitivity Center Cell (F44)** | **Rs 252** | **Rs 252** | ✅ **VERIFIED** |
| **Sensitivity Corner Cell (D42)** | **Rs 307** | **Rs 307** | ✅ **VERIFIED** |

---

## 3. Quick Start (Zero-Touch One-Liner)

Run the entire financial modeling, valuation, simulation, and packaging pipeline with a single command:

```bash
python run_engine.py
```

All deliverables are automatically written to `artifacts/`:
* `artifacts/kaveri_financial_model.xlsx`: Live-formula Excel workbook.
* `artifacts/kaveri_dashboard.html`: Interactive web dashboard.
* `artifacts/kaveri_investment_memo.md`: Executive memorandum.
* `artifacts/kaveri_valuation_output.json`: Structured quantitative payload.
* `artifacts/kaveri_audit_certificate.json`: Audit invariant certificate.

---

## 4. Command-Line Interface (CLI)

```bash
# Run with a pre-configured corporate profile (kaveri_foods, saas_growth, industrial_corp)
python -m financial_engine --company saas_growth

# Run with a custom corporate JSON dataset
python -m financial_engine --config path/to/my_company.json --output-dir my_artifacts

# Run with custom Monte Carlo iteration count
python -m financial_engine --company kaveri_foods --mc-iterations 25000

# Run in headless/quiet mode for automation scripts
python -m financial_engine --company industrial_corp --quiet
```

---

## 5. Python SDK & API Usage

```python
from financial_engine import FinancialEngine

# Load template and solve 100% autonomously
engine = FinancialEngine.from_template("kaveri_foods")
model = engine.solve(run_mc=True, mc_iterations=10000)

# Access valuation metrics
print(f"Fair Value:       Rs {model.value_per_share:.2f}")
print(f"Enterprise Value: Rs {model.enterprise_value:,.2f} Cr")
print(f"WACC:             {model.wacc * 100:.2f}%")
print(f"Is Balanced:      {model.is_balanced}")

# Access Monte Carlo statistics
mc = model.monte_carlo
print(f"Median Price:     Rs {mc.median_price:.2f}")
print(f"95% VaR:          Rs {mc.pct_5:.2f}")
print(f"Prob Undervalued: {mc.prob_undervalued:.1f}%")
```

---

## 6. Repository Architecture

```
C:\Users\HP\Downloads\Finance\
├── pyproject.toml                     # Modern package build specification
├── setup.py                           # Setuptools package configuration
├── requirements.txt                   # Dependency manifests
├── run_engine.py                      # One-click zero-touch runner script
├── financial_engine/
│   ├── __init__.py                    # Public API exports
│   ├── cli.py                         # Rich command-line interface
│   ├── engine.py                      # High-level engine orchestrator
│   ├── core/
│   │   ├── types.py                   # Strongly-typed financial dataclasses
│   │   ├── accounting.py              # Structural accounting identity verifier
│   │   ├── config.py                  # Model configuration serializer/deserializer
│   │   └── exceptions.py              # Domain error hierarchy
│   ├── statements/
│   │   ├── income_statement.py        # Revenue down to PAT and margin ratios
│   │   ├── balance_sheet.py           # Self-balancing balance sheet (zero plug)
│   │   └── cash_flow.py               # Indirect CFO, CFI, CFF, and cash loop
│   ├── schedules/
│   │   ├── working_capital.py         # Days drivers (DSO, DIO, DPO) & NWC roll
│   │   ├── fixed_assets.py            # Capex & Net Block roll-forward
│   │   ├── debt.py                    # Debt amortization & average interest
│   │   └── equity.py                  # Retained earnings roll-forward
│   ├── valuation/
│   │   ├── wacc.py                    # CAPM Ke, after-tax Kd, Hamada formula
│   │   ├── dcf.py                     # Unlevered FCFF, Gordon TV, Exit Multiple
│   │   ├── comps.py                   # Trading multiples percentiles
│   │   ├── lbo.py                     # PE sponsor returns, MoIC, and IRR
│   │   └── advanced_metrics.py        # ROIC, EVA, 5-way DuPont, and Football Field
│   ├── simulation/
│   │   ├── sensitivity.py             # 2-way sensitivity matrix generator
│   │   ├── scenarios.py               # Bull, Base, Bear scenario manager
│   │   └── monte_carlo.py             # 10,000-run stochastic simulation
│   ├── excel/
│   │   ├── styles.py                  # Wall Street palette & number formats
│   │   └── builder.py                 # Formula-driven openpyxl workbook builder
│   ├── reporting/
│   │   ├── html_dashboard.py          # Standalone responsive web dashboard
│   │   ├── executive_memo.py          # Investment committee memorandum
│   │   └── audit_report.py            # Accounting verification attestation
│   └── data/
│       ├── kaveri_foods.json          # Benchmark packaged foods model
│       ├── saas_growth.json           # High-growth B2B enterprise SaaS model
│       ├── industrial_corp.json       # Capital-intensive machinery model
│       └── aethel_biopharma.json      # Specialty biopharma & oncology therapeutics
├── tests/
│   ├── test_accounting_identities.py  # Zero-plug balance sheet tests
│   ├── test_kaveri_benchmark.py       # 89-step numerical benchmark check
│   ├── test_dcf_valuation.py          # WACC, CAPM, and DCF tests
│   ├── test_simulation.py             # Sensitivity and Monte Carlo tests
│   ├── test_excel_generation.py       # Live-formula syntax tests
│   ├── test_cli.py                    # End-to-end integration tests
│   ├── test_advanced_metrics.py       # ROIC, DuPont 5-way, and Football Field tests
│   └── run_tests.py                   # Standalone test runner
├── docs/
│   ├── ARCHITECTURE.md                # System design & component interaction
│   ├── METHODOLOGY.md                 # Quantitative valuation & financial formulas
│   └── USER_GUIDE.md                  # Comprehensive user operations manual
└── artifacts/
    ├── kaveri_financial_model.xlsx    # Generated Excel workbook with formulas
    ├── kaveri_dashboard.html          # Generated interactive web dashboard
    ├── kaveri_investment_memo.md      # Generated investment committee memo
    ├── kaveri_audit_certificate.json  # Generated invariant certificate
    ├── kaveri_audit_report.md         # Generated audit report
    └── kaveri_valuation_output.json   # Generated structured JSON payload
```

---

## 7. Accounting Invariant Attestation

Every model generated by this engine is programmatically subjected to six invariant verification gates:

```
============================================================
FINANCIAL MODEL ACCOUNTING INTEGRITY AUDIT CERTIFICATE
============================================================
Overall Status: PASSED
------------------------------------------------------------
✓ [PASS] Balance Sheet Balance Identity      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
✓ [PASS] Cash Flow Roll-Forward Identity     Max Err: 0.000000e+00 (Tol: 1.000000e-04)
✓ [PASS] Retained Earnings Roll-Forward      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
✓ [PASS] Fixed Assets Net Block Roll-Forward Max Err: 0.000000e+00 (Tol: 1.000000e-04)
✓ [PASS] Debt Amortization Roll-Forward      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
✓ [PASS] Working Capital Change Reconciliation Max Err: 0.000000e+00 (Tol: 1.000000e-04)
============================================================
```

---

## 8. License

Distributed under the MIT License. See `LICENSE` for more information.
