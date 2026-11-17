# INVESTMENT COMMITTEE MEMORANDUM

**TO:** Investment Committee & Senior Leadership  
**FROM:** Lead Principal Financial Architect & Quantitative Engineer  
**DATE:** Automated Valuation Engine Run  
**SUBJECT:** Comprehensive Valuation & 3-Statement Model Audit: **Tesla, Inc. (TSLA)**  

---

## 1. Executive Summary & Recommendation

The Automated Financial Modeling & Valuation Engine has completed a 100% zero-touch, rigorous valuation and 3-statement reconciliation of **Tesla, Inc.**. 

* **Implied Fair Value per Share:** **USD 11**
* **Current Market Price:** USD 390
* **Projected Upside / (Downside):** **-97.1%**
* **Implied Enterprise Value:** USD 43.0 billion
* **Implied Equity Value:** USD 44.8 billion
* **Accounting Model Integrity:** **100% VERIFIED** (Assets == Liabilities + Equity with 0.00 discrepancy across all historical and 5 forecast years).
* **Source / Mapping:** Live Yahoo Finance annual statements and quote for Tesla, Inc. (NMS); other assets and liabilities are aggregated to fit the engine's simplified schema.

| Metric | Base DCF | Peer Comps | Sponsor LBO (5-Yr) | Monte Carlo Median | Prob-Weighted Scenario |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Implied Price** | **USD 11** | USD 127 | — | USD 11 | USD 11 |
| **Enterprise Value** | 43.0 | 498.6 | 292.6 | — | — |
| **Key Multiple** | 3.7x EV/EBITDA | 42.6x EV/EBITDA | 2.35x MoIC | — | — |
| **Implied Return** | -97.1% | -67.6% | 18.6% IRR | — | -97.1% |

The LBO column reports sponsor returns and enterprise value, not a per-share valuation.

---

## 2. Key Valuation Methodology & DCF Bridge

The baseline valuation is anchored on an Unlevered Discounted Cash Flow (FCFF) framework discounting five years of explicit cash flows at the company's Weighted Average Cost of Capital (WACC), plus a Gordon Growth perpetual terminal value.

### Cost of Capital (CAPM / WACC) Breakdown
* **Risk-Free Rate ($R_f$):** 4.40% (10-Year Benchmark)
* **Equity Beta:** 1.74
* **Equity Risk Premium (ERP):** 5.50%
* **Cost of Equity ($K_e$):** **13.99%**
* **Pre-Tax Cost of Debt ($K_d$):** 8.50%
* **Marginal Corporate Tax Rate ($t$):** 27.28%
* **After-Tax Cost of Debt ($K_d(1-t)$):** 6.18%
* **Capital Structure:** Debt Weight = 1.0%, Equity Weight = 99.0%
* **Blended WACC:** **13.91%** (Rounds to 13.9%)

### Enterprise Value to Equity Bridge (USD billion)
* **Cumulative PV of Explicit 5-Year FCFF:** 13.6 (31.6% of EV)
* **Terminal Value (Gordon Growth @ 4.0%):** 56.4
* **PV of Terminal Value:** 29.4 (68.4% of EV)
* **Total Enterprise Value (EV):** **43.0**
* **Less: Total Debt (Base Period):** -14.7
* **Add: Cash & Equivalents (Base Period):** +16.5
* **Implied Equity Value:** **44.8**
* **Diluted Shares Outstanding:** 4.0 billion
* **Implied Value Per Share:** **USD 11**

---

## 3. Operational Projections & Three-Statement Linkage

The model features dynamic operational drivers:
* **Revenue Growth:** Tapers from 5.3% in FY26E to 3.6% in FY30E.
* **COGS Margin:** Anchored to the historical average gross margin (80.1% COGS / 19.9% gross margin).
* **Working Capital:** Forecast drivers use DSO 15.2 days, DIO 62.4 days, and DPO 170.6 days.
* **Capital Investments:** Capex averages 9.7% of revenue; depreciation averages 6.9% of opening modeled net block. The modeled net block moves from 104.3 to 119.5 billion by FY30E.
* **Debt Trajectory:** Scheduled repayments lower debt from 14.7 to 0.0 billion by FY30E; final-year interest expense is 0.0 billion.

---

## 4. Sensitivity Matrix: WACC vs. Terminal Growth Rate

The 2-way sensitivity table displays the sensitivity of Fair Value per Share (USD) across cost of capital and terminal growth rates:

| WACC ↓ \ Growth → | 3.0% | 3.5% | 4.0% | 4.5% | 5.0% |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **11.9%** | USD 13 | USD 14 | USD 14 | USD 15 | USD 16 |
| **12.9%** | USD 12 | USD 12 | USD 13 | USD 13 | USD 14 |
| **13.9% (Base)** | USD 11 | USD 11 | USD 11 | USD 12 | USD 12 |
| **14.9%** | USD 10 | USD 10 | USD 10 | USD 11 | USD 11 |
| **15.9%** | USD 9 | USD 9 | USD 9 | USD 10 | USD 10 |

---

## 5. Monte Carlo Stochastic Risk Simulation

A 10,000-run Monte Carlo simulation incorporating normal volatility on WACC (sigma = 75 bps), terminal growth (sigma = 50 bps), and operational cash flows (sigma = 8.0%) reveals:

* **Mean Fair Value:** USD 11
* **Median Fair Value:** USD 11
* **Standard Deviation:** USD 1.2
* **5th Percentile (95% Confidence VaR Lower Bound):** **USD 10**
* **25th Percentile:** USD 11
* **75th Percentile:** USD 12
* **95th Percentile (Bull Ceiling):** **USD 14**
* **Probability of Undervaluation:** **0.0%** of simulation runs exceed the current market price of USD 390.

---

## 6. Accounting Audit & Zero-Plug Invariant Attestation

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

**Conclusion:** The financial model is completely self-balancing, robust against stochastic stress testing, and verified ready for institutional deployment.
