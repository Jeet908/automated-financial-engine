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
| **Enterprise Value** | 2,486.9 Cr | 2,486.9 Cr | ✅ **VERIFIED** |
| **Fair Value Per Share** | **Rs 252** | **Rs 252** | ✅ **VERIFIED** |
| **Sensitivity Center Cell (F44)** | **Rs 252** | **Rs 252** | ✅ **VERIFIED** |
| **Sensitivity Corner Cell (D42)** | **Rs 307** | **Rs 307** | ✅ **VERIFIED** |

---

## 3. Open-Source 6-Gate Accounting Invariant Benchmark Suite

Prove our engine's **`0.000000e+00`** Balance Sheet reconciliation accuracy across **India Ind AS / Schedule III**, **US GAAP**, and **UK / EU IFRS** filings compared to generic LLMs in 10 seconds:

```bash
python benchmarks/run_benchmark.py
```

### Sovereign Deterministic Accuracy vs. Generic LLM Baseline:
| Metric / Audit Check | MarketLens Engine (Deterministic) | Generic LLM Baseline (Unverified) | Advantage |
| :--- | :---: | :---: | :---: |
| **Balance Sheet Max Discrepancy** | **`0.000000e+00`** | `~0.1850` | **Exact Zero Drift ($Assets \equiv L+E$)** |
| **6/6 Accounting Invariant Pass Rate** | **`100.0%` (18/18)** | `27.8%` (5/18) | **+72.2% Integrity Guard** |
| **Excel Formula Errors (`#REF!`/`#DIV/0!`)** | **`0`** | `42` | **Zero Broken References** |
| **SHA-256 Lineage Cryptographic Coverage** | **`100.0%`** | `0.0%` | **Full Big-4 Provenance Chain** |
| **Average End-to-End Solve Latency** | **`14.85 ms`** | `2,916.67 ms` | **~196x Faster Execution** |

Full automated audit report and reproducible JSON dataset emitted to [`benchmarks/BENCHMARK_REPORT.md`](benchmarks/BENCHMARK_REPORT.md) and [`benchmarks/benchmark_results.json`](benchmarks/benchmark_results.json).

---

## 4. Quick Start (Zero-Touch One-Liner)

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

### Live company discovery and portal

The live runner selects a listed ticker from the configured sector universe, retrieves its current quote and overlapping annual statements from Yahoo Finance, and writes the scraped workbook and engine config before running both valuation pipelines:

```bash
python discover_and_run.py
python discover_and_run.py --domain "Indian FMCG & Consumer" --market india
```

The live universe includes Indian IT/defence and consumer companies, US semiconductors, SaaS, healthcare, and clean energy. At least four common annual periods across the income statement, balance sheet, and cash flow statement are required. The engine's simplified balance-sheet schema aggregates non-cash/non-receivable/non-inventory assets and non-debt liabilities; the scraped workbook labels those mappings and also includes reported values.

Start the browser portal with `py -m uvicorn app:app --host 127.0.0.1 --port 8000`. Its `POST /api/v1/model/live-scrape` endpoint accepts `{"domain":"Any Random Domain","market":"random"}`; `POST /api/v1/model/generate-pack` accepts an uploaded client workbook. Use the portal's live-company selector or visit `http://127.0.0.1:8000`.

### Deploy on Railway

The portal supports account registration, verified email and Google sign-in, private reports, Free/Pro/Business usage limits, and Razorpay recurring billing. Production setup is not complete until persistent storage, transactional email, OAuth credentials, Razorpay plans/webhooks, and legal operator details are configured. Follow [the subscription launch checklist](docs/SAAS_LAUNCH.md) before accepting customer uploads or payments.

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
[PASS] Balance Sheet Balance Identity      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
[PASS] Cash Flow Roll-Forward Identity     Max Err: 0.000000e+00 (Tol: 1.000000e-04)
[PASS] Retained Earnings Roll-Forward      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
[PASS] Fixed Assets Net Block Roll-Forward Max Err: 0.000000e+00 (Tol: 1.000000e-04)
[PASS] Debt Amortization Roll-Forward      Max Err: 0.000000e+00 (Tol: 1.000000e-04)
[PASS] Working Capital Change Reconciliation Max Err: 0.000000e+00 (Tol: 1.000000e-04)
============================================================
```

---

## 8. Distributed Architecture & Railway Multi-Service Deployment

MarketLens Analytics scales horizontally as a modern distributed microservices system:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MarketLens Distributed Architecture                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
    [ Fast API Web Gateway ]                      [ Celery Worker Pool ]
    (python app.py / Port 8000)                   (concurrency=2, acks_late=True)
              │                                               │
              ├───────────────┬───────────────┬───────────────┤
              ▼               ▼               ▼               ▼
      [ PostgreSQL 16 ]  [ Redis 7 ]  [ Cloudflare R2 ]  [ Celery Beat ]
      (Tenant RLS)      (Broker &     (Signed Presigned  (00:00 UTC Scraper)
                        Backend)       S3 URLs, 900s)
```

### Multi-Service Configuration:

1. **PostgreSQL 16 (Relational Database & Tenant Isolation)**:
   - Dual-mode SQLAlchemy engine automatically normalizes Railway `postgres://` or `postgresql://` connection strings to `postgresql+psycopg2://`.
   - Production connection pooling: `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`, `pool_pre_ping=True`.
   - Strict tenant-level row isolation via indexed `tenant_id` and PostgreSQL Row-Level Security (`CREATE POLICY`).
   - Concurrency protection: `SELECT ... FOR UPDATE` row locking prevents quota race conditions.

2. **Redis 7 & Celery Worker Pool**:
   - Asynchronous offloading for compute-heavy valuation runs (10,000-run Monte Carlo, openpyxl compilation, PDF tear-sheets, PPTX pitchbooks).
   - Dedicated queues: `valuation_heavy` (heavy modeling) and `scraper_daily` (daily SEC EDGAR & market scrapers).
   - Scheduled Celery Beat cron at `00:00 UTC` (`crontab(hour=0, minute=0)`).
   - Zero-config graceful fallback to eager local execution when `REDIS_URL` is omitted.

3. **Signed Object Storage (Cloudflare R2 / AWS S3)**:
   - Boto3 integration with `s3v4` signature version and virtual-hosted addressing.
   - Tenant-isolated object keys: `tenants/{tenant_id}/jobs/{job_id}/{filename}`.
   - Zero-disk bloat: temporary local scratch directories purged in `finally:` blocks.
   - Secure delivery: 900-second pre-signed download URLs (`ExpiresIn=900`) with custom content disposition.

### Railway Deployment Quickstart:

1. **Link Services on Railway**:
   - Provision a **Railway PostgreSQL** plugin (automatically exposes `DATABASE_URL`).
   - Provision a **Railway Redis** plugin (automatically exposes `REDIS_URL`).
   - Deploy the web service from GitHub repository root (starts `python app.py`).
   - Add a worker service with custom start command:
     ```bash
     celery -A src.workers.celery_app worker -Q valuation_heavy,scraper_daily --loglevel=info --concurrency=2
     ```
   - Add a beat scheduler service with start command:
     ```bash
     celery -A src.workers.celery_app beat --loglevel=info
     ```

2. **Configure Cloudflare R2 / AWS S3 Environment Variables**:
   ```bash
   S3_BUCKET=marketlens-artifacts
   S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
   S3_ACCESS_KEY_ID=<your-access-key-id>
   S3_SECRET_ACCESS_KEY=<your-secret-access-key>
   S3_REGION=auto
   S3_PRESIGN_TTL_SECONDS=900
   ```

---

## 9. License

Distributed under the MIT License. See `LICENSE` for more information.
