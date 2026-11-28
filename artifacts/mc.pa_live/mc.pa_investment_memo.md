# INVESTMENT COMMITTEE MEMORANDUM

**TO:** Investment Committee & Senior Leadership  
**FROM:** Lead Principal Financial Architect & Quantitative Engineer  
**DATE:** Automated Valuation Engine Run  
**SUBJECT:** Comprehensive Valuation & 3-Statement Model Audit: **LVMH Moët Hennessy - Louis Vuitton, Société Européenne (MC.PA)**  

---

## 1. Executive Summary & Recommendation

The Automated Financial Modeling & Valuation Engine has completed a 100% zero-touch, rigorous valuation and 3-statement reconciliation of **LVMH Moët Hennessy - Louis Vuitton, Société Européenne**. 

* **Implied Fair Value per Share:** **EUR 587**
* **Current Market Price:** EUR 399
* **Projected Upside / (Downside):** **+47.1%**
* **Implied Enterprise Value:** EUR 316.0 billion
* **Implied Equity Value:** EUR 288.1 billion
* **Accounting Model Integrity:** **100% VERIFIED** (Assets == Liabilities + Equity with 0.00 discrepancy across all historical and 5 forecast years).
* **Source / Mapping:** Live Yahoo Finance annual statements and quote for LVMH Moët Hennessy - Louis Vuitton, Société Européenne (PAR); other assets and liabilities are aggregated to fit the engine's simplified schema.

| Metric | Base DCF | Peer Comps | Sponsor LBO (5-Yr) | Monte Carlo Median | Prob-Weighted Scenario |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Implied Price** | **EUR 587** | EUR 2158 | — | EUR 586 | EUR 595 |
| **Enterprise Value** | 316.0 | 1,086.8 | 637.7 | — | — |
| **Key Multiple** | 12.4x EV/EBITDA | 42.6x EV/EBITDA | 1.59x MoIC | — | — |
| **Implied Return** | +47.1% | +440.7% | 9.8% IRR | — | +49.1% |

The LBO column reports sponsor returns and enterprise value, not a per-share valuation.

---

## 2. Key Valuation Methodology & DCF Bridge

The baseline valuation is anchored on an Unlevered Discounted Cash Flow (FCFF) framework discounting five years of explicit cash flows at the company's Weighted Average Cost of Capital (WACC), plus a Gordon Growth perpetual terminal value.

### Cost of Capital (CAPM / WACC) Breakdown
* **Risk-Free Rate ($R_f$):** 4.40% (10-Year Benchmark)
* **Equity Beta:** 0.90
* **Equity Risk Premium (ERP):** 5.50%
* **Cost of Equity ($K_e$):** **9.33%**
* **Pre-Tax Cost of Debt ($K_d$):** 8.50%
* **Marginal Corporate Tax Rate ($t$):** 30.00%
* **After-Tax Cost of Debt ($K_d(1-t)$):** 5.95%
* **Capital Structure:** Debt Weight = 15.8%, Equity Weight = 84.2%
* **Blended WACC:** **8.79%** (Rounds to 8.8%)

### Enterprise Value to Equity Bridge (EUR billion)
* **Cumulative PV of Explicit 5-Year FCFF:** 68.2 (21.6% of EV)
* **Terminal Value (Gordon Growth @ 4.0%):** 377.6
* **PV of Terminal Value:** 247.8 (78.4% of EV)
* **Total Enterprise Value (EV):** **316.0**
* **Less: Total Debt (Base Period):** -36.7
* **Add: Cash & Equivalents (Base Period):** +8.8
* **Implied Equity Value:** **288.1**
* **Diluted Shares Outstanding:** 0.5 billion
* **Implied Value Per Share:** **EUR 587**

---

## 3. Operational Projections & Three-Statement Linkage

The model features dynamic operational drivers:
* **Revenue Growth:** Tapers from 3.8% in FY26E to 2.6% in FY30E.
* **COGS Margin:** Anchored to the historical average gross margin (32.4% COGS / 67.6% gross margin).
* **Working Capital:** Forecast drivers use DSO 19.9 days, DIO 305.5 days, and DPO 545.7 days.
* **Capital Investments:** Capex averages 7.0% of revenue; depreciation averages 7.2% of opening modeled net block. The modeled net block moves from 106.3 to 100.3 billion by FY30E.
* **Debt Trajectory:** Scheduled repayments lower debt from 36.7 to 0.0 billion by FY30E; final-year interest expense is 0.1 billion.

---

## 4. Sensitivity Matrix: WACC vs. Terminal Growth Rate

The 2-way sensitivity table displays the sensitivity of Fair Value per Share (EUR) across cost of capital and terminal growth rates:

| WACC ↓ \ Growth → | 3.0% | 3.5% | 4.0% | 4.5% | 5.0% |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **6.8%** | EUR 783 | EUR 892 | EUR 1040 | EUR 1253 | EUR 1584 |
| **7.8%** | EUR 610 | EUR 673 | EUR 754 | EUR 859 | EUR 1002 |
| **8.8% (Base)** | EUR 496 | EUR 537 | EUR 587 | EUR 649 | EUR 726 |
| **9.8%** | EUR 416 | EUR 444 | EUR 478 | EUR 518 | EUR 566 |
| **10.8%** | EUR 356 | EUR 377 | EUR 401 | EUR 428 | EUR 460 |

---

## 5. Monte Carlo Stochastic Risk Simulation

A 10,000-run Monte Carlo simulation incorporating normal volatility on WACC (sigma = 75 bps), terminal growth (sigma = 50 bps), and operational cash flows (sigma = 8.0%) reveals:

* **Mean Fair Value:** EUR 611
* **Median Fair Value:** EUR 586
* **Standard Deviation:** EUR 142.0
* **5th Percentile (95% Confidence VaR Lower Bound):** **EUR 434**
* **25th Percentile:** EUR 515
* **75th Percentile:** EUR 678
* **95th Percentile (Bull Ceiling):** **EUR 871**
* **Probability of Undervaluation:** **98.4%** of simulation runs exceed the current market price of EUR 399.

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
