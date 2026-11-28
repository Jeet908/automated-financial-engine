# MarketLens Analytics — Automated Financial Modeling & Valuation Engine

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Accounting Invariants: 100% Passed](https://img.shields.io/badge/Accounting%20Invariants-100%25%20Passed-brightgreen.svg)]()
[![Balance Sheet Plug: 0.00](https://img.shields.io/badge/Balance%20Sheet%20Plug-0.000-brightgreen.svg)]()
[![Model Quality: Institutional Grade](https://img.shields.io/badge/Model%20Quality-Wall%20Street%20Standard-blue.svg)]()

> **An autonomous, production-ready quantitative financial engineering platform that builds, stress-tests, audits, and packages full 3-statement financial models, multi-method valuations (DCF, Trading Comps, LBO), 2D sensitivity heatmaps, 5-Way DuPont ROE waterfalls, C-Suite operational diagnostics, and 10,000-iteration Monte Carlo simulations with zero manual plugs.**

---

## 1. Executive Summary & Core Capabilities

MarketLens Analytics eliminates manual spreadsheet errors and modeling drift by programmatically constructing audit-ready institutional models across **US GAAP (ASC 606 / 842)**, **India Ind AS / Schedule III**, and **UK / EU IFRS**.

* **Self-Balancing 3-Statement Architecture:** Fully coupled Income Statement, Balance Sheet, and Cash Flow Statement. Total Assets identically equal Total Liabilities & Equity ($Assets - L\&E = 0.00$) across all historical and projected periods with **zero plug figures**.
* **Dynamic Top-100 Global Universe (11 GICS Sectors):** Tracks a 122-company contender pool (`SEED_TOP_100_CHAMPIONS` + `EXTRA_CONTENDER_CHAMPIONS`), ranks dynamically by FX-normalized market capitalization (`[:100]`), and supports sector filtering, typeahead search, and company-level selection (`#domain-selector` + `#company-selector`).
* **3-Tier Data Provenance Chain:**
  1. **Tier 1 (Live):** Yahoo Finance annual statements & live quotes cached to `inputs/live_cache/<TICKER>.json`.
  2. **Tier 2 (Cached Archive):** Serves the last verified real extraction if live feeds rate-limit.
  3. **Tier 3 (Sector-Calibrated Benchmark Model):** Scales a sector template to target `market_cap_usd` and explicitly tags `data_source`.
* **Multi-Method Institutional Valuation Suite:**
  * **Unlevered DCF (FCFF):** NOPAT, D&A, CapEx, $\Delta\text{NWC}$, Gordon Growth & Exit Multiple terminal values, and Enterprise-to-Equity Value bridge.
  * **CAPM & WACC:** $K_e = R_f + \beta \times \text{ERP}$, after-tax $K_d(1-t)$, and target capital structure weighting.
  * **Trading Comps & LBO Screening:** Sector-aware peer multiples (EV/EBITDA, P/E, EV/Sales) and 5-year PE sponsor returns (IRR, MoIC).
  * **5-Way DuPont ROE & C-Suite Pain Points:** Operational DSO/DIO/DPO/CCC diagnostics (prioritizing `reported_accounts_payable` when available), EBITDA margin bridge, and ROIC-vs-WACC spread.
* **Risk & Stochastic Simulation:** Interactive 5×5 WACC vs. Terminal Growth sensitivity heatmap (rendering `N/A` where `WACC <= TGR`), Bull/Base/Bear scenarios, and 10,000-path Monte Carlo simulation with 95% Parametric VaR.
* **Synchronized Institutional Deliverables (`.xlsx`, `.pdf`, `.pptx`, `.zip`):**
  * **Live-Formula Excel Workbook (`.xlsx`):** Wall Street color coding, `CHOOSE` scenario switches, cross-sheet formulas, and `FormulaChecker` scan (`0` `#REF!` / `#DIV/0!` / `#VALUE!` / `#NAME?`).
  * **2-Page Vector PDF Tear Sheet (`.pdf`)** & **8-Slide Executive Pitchbook (`.pptx`)** synchronized from the identical `FinancialModel` state.
  * **4-Stage SHA-256 Merkle Provenance Ledger:** Tamper-evident audit certificates verifiable via `/api/v1/audit/verify/{job_id}` and `/api/v1/audit/verify-hash`.

---

## 2. Benchmark & Invariant Verification

Every model passes **6 mathematical accounting invariant gates** (`Max Err: 0.000000e+00`):

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

Run the multi-regime benchmark suite across India Ind AS, US GAAP, and UK/EU IFRS:

```bash
python benchmarks/run_benchmark.py
```

Outputs are written to [`benchmarks/BENCHMARK_REPORT.md`](benchmarks/BENCHMARK_REPORT.md) and [`benchmarks/benchmark_results.json`](benchmarks/benchmark_results.json).

---

## 3. Quick Start & CLI

### Web Portal (Editorial Light UI + API)
```bash
py -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000` to run live Top-100 valuations (`POST /api/v1/model/live-scrape`), upload private `.xlsx` / `.csv` / `.json` / `.pdf` files (`POST /api/v1/model/generate-pack`), stream SSE progress (`/api/v1/jobs/{job_id}/stream`), and download executive packs.

### CLI & Live Discovery Runners
```bash
# 1. One-click canonical benchmark run
python run_engine.py

# 2. Live sector/ticker discovery + full pack generation
python discover_and_run.py
python discover_and_run.py --domain "Information Technology" --market global

# 3. Direct template or custom JSON execution
python -m financial_engine --company saas_growth
python -m financial_engine --config path/to/my_company.json --output-dir my_artifacts
python -m financial_engine --company kaveri_foods --mc-iterations 25000 --quiet
```

### Python SDK
```python
from financial_engine import FinancialEngine

engine = FinancialEngine.from_template("kaveri_foods")
model = engine.solve(run_mc=True, mc_iterations=10000)

print(f"Fair Value:       {model.value_per_share:.2f}")
print(f"Enterprise Value: {model.enterprise_value:,.2f}")
print(f"WACC:             {model.wacc * 100:.2f}%")
print(f"Is Balanced:      {model.is_balanced}")
```

---

## 4. Repository Architecture

```text
automated-financial-engine/
├── app.py                             # FastAPI portal gateway, security headers, TTL purger & market APIs
├── discover_and_run.py                # Autonomous live web scraping & dual-engine execution pipeline
├── run_engine.py                      # One-click canonical runner script
├── pyproject.toml / setup.py          # Package build & dependency configuration
├── requirements.txt                   # Production & testing dependencies (incl. cryptography, redis, celery)
├── financial_engine/                  # Core quantitative 3-statement, DCF, Comps, LBO & Monte Carlo engine
│   ├── engine.py                      # FinancialEngine orchestrator & FinancialModel
│   ├── core/                          # Types, AccountingVerifier, config & exceptions
│   ├── statements/                    # IncomeStatement, BalanceSheet, CashFlowStatement
│   ├── schedules/                     # WorkingCapital, FixedAssets, Debt & Equity schedules
│   ├── valuation/                     # WACC, DCF, Comps, LBO & advanced metrics
│   ├── simulation/                    # SensitivityMatrix, Scenarios & 10,000-path Monte Carlo
│   ├── reporting/                     # PainPoints diagnostics, DuPont, executive memo & HTML dashboard
│   └── excel/                         # Formula-driven openpyxl workbook builder
├── src/
│   ├── cli.py                         # UniversalIngester + ModelOrchestrator CLI entrypoint
│   ├── ingestion/                     # MarketUniverseManager (Top-100 GICS) & LiveWebScraper
│   ├── exporters/                     # Adapter, WorkbookCompiler, FormulaChecker & ExecutivePackCompiler (PDF/PPTX/ZIP)
│   ├── portal/                        # Auth, SAML 2.0 SSO, Stripe/Razorpay billing, Scoped VaaS API keys, Jobs & Static UI
│   ├── workers/                       # Celery app & distributed tasks (valuation_heavy, scraper_daily)
│   ├── storage/                       # Cloudflare R2 / AWS S3 presigned artifact delivery
│   ├── mesh/                          # Regulatory & sector benchmark multiples
│   └── observability/                 # OpenTelemetry & SLA tracking
├── benchmarks/                        # Multi-regime 6-gate benchmark runner & reports
├── docs/                              # Architecture, Methodology, User Guide & SaaS Launch Checklist
└── tests/                             # Full pytest suite (accounting, parity, SSE, audit ledger, billing, SSO, VaaS)
```

---

## 5. Production SaaS, Security & Railway Deployment

MarketLens Analytics supports multi-tenant SaaS operations and horizontal scaling:

* **Authentication & Enterprise SSO:** Email/password with verification, Google OAuth, 1-run frictionless guest mode, and tenant-isolated **SAML 2.0 SSO** (`cryptography` XML signature verification).
* **Billing & Tier Gating:** Multi-currency (`USD`, `INR`, `EUR`, `GBP`) via **Stripe** and **Razorpay** across `Free` (`$0`), `Pro` (`$499/mo`), `Business` (`$1,499/mo`), and `Enterprise` (`$4,999/mo`).
* **Scoped VaaS API Keys:** `ml_live_...` SHA-256 hashed keys with per-minute sliding-window rate limiting backed by **Redis** (`REDIS_URL`) with automatic in-memory fallback.
* **Data Retention & Encryption at Rest:** Tenant job workspaces under `DATA_DIR/accounts/<user_id>/jobs/<job_id>` are automatically purged on a configurable **24-hour TTL** (`JOB_RETENTION_HOURS=24`), while SHA-256 Merkle audit ledger records remain verifiable in the database. OAuth/ERP tokens are encrypted at rest with `Fernet` (`TOKEN_ENCRYPTION_KEY`).
* **Database & Workers:** Supports PostgreSQL 16 (`DATABASE_URL`) with automatic SQLite fallback (`_ensure_sqlite_columns` auto-migration) and Celery/Redis workers (`valuation_heavy`, `scraper_daily`) with FastAPI `BackgroundTasks` fallback.

See [`docs/SAAS_LAUNCH.md`](docs/SAAS_LAUNCH.md) for the full Railway production environment checklist before accepting customer traffic or payments.

---

## 6. Testing

Run the full test suite:

```bash
py -m pytest
```

---

## 7. License

Distributed under the MIT License. See `LICENSE` for more information.
