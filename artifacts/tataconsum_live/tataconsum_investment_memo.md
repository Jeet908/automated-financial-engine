# INVESTMENT COMMITTEE MEMORANDUM

**TO:** Investment Committee & Senior Leadership  
**FROM:** Lead Principal Financial Architect & Quantitative Engineer  
**DATE:** Automated Valuation Engine Run  
**SUBJECT:** Comprehensive Valuation & 3-Statement Model Audit: **Tata Consumer Products Limited (TATACONSUM)**  

---

## 1. Executive Summary & Recommendation

The Automated Financial Modeling & Valuation Engine has completed a 100% zero-touch, rigorous valuation and 3-statement reconciliation of **Tata Consumer Products Limited**. 

* **Implied Fair Value per Share:** **INR 828**
* **Current Market Price:** INR 1118
* **Projected Upside / (Downside):** **-25.9%**
* **Implied Enterprise Value:** INR 81,742.0 crore
* **Implied Equity Value:** INR 81,969.0 crore
* **Accounting Model Integrity:** **100% VERIFIED** (Assets == Liabilities + Equity with 0.00 discrepancy across all historical and 5 forecast years).
* **Source / Mapping:** Live Yahoo Finance annual statements and quote for Tata Consumer Products Limited (NSE); other assets and liabilities are aggregated to fit the engine's simplified schema.

| Metric | Base DCF | Peer Comps | Sponsor LBO (5-Yr) | Monte Carlo Median | Prob-Weighted Scenario |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Implied Price** | **INR 828** | INR 1226 | — | INR 828 | INR 845 |
| **Enterprise Value** | 81,742.0 | 121,063.7 | 73,873.5 | — | — |
| **Key Multiple** | 28.8x EV/EBITDA | 42.6x EV/EBITDA | 2.72x MoIC | — | — |
| **Implied Return** | -25.9% | +9.7% | 22.2% IRR | — | -24.4% |

The LBO column reports sponsor returns and enterprise value, not a per-share valuation.

---

## 2. Key Valuation Methodology & DCF Bridge

The baseline valuation is anchored on an Unlevered Discounted Cash Flow (FCFF) framework discounting five years of explicit cash flows at the company's Weighted Average Cost of Capital (WACC), plus a Gordon Growth perpetual terminal value.

### Cost of Capital (CAPM / WACC) Breakdown
* **Risk-Free Rate ($R_f$):** 6.80% (10-Year Benchmark)
* **Equity Beta:** 0.34
* **Equity Risk Premium (ERP):** 6.50%
* **Cost of Equity ($K_e$):** **8.98%**
* **Pre-Tax Cost of Debt ($K_d$):** 8.50%
* **Marginal Corporate Tax Rate ($t$):** 25.76%
* **After-Tax Cost of Debt ($K_d(1-t)$):** 6.31%
* **Capital Structure:** Debt Weight = 2.5%, Equity Weight = 97.5%
* **Blended WACC:** **8.92%** (Rounds to 8.9%)

### Enterprise Value to Equity Bridge (INR crore)
* **Cumulative PV of Explicit 5-Year FCFF:** 11,355.9 (13.9% of EV)
* **Terminal Value (Gordon Growth @ 5.5%):** 107,888.7
* **PV of Terminal Value:** 70,386.1 (86.1% of EV)
* **Total Enterprise Value (EV):** **81,742.0**
* **Less: Total Debt (Base Period):** -2,819.5
* **Add: Cash & Equivalents (Base Period):** +3,046.6
* **Implied Equity Value:** **81,969.0**
* **Diluted Shares Outstanding:** 99.0 crore
* **Implied Value Per Share:** **INR 828**

---

## 3. Operational Projections & Three-Statement Linkage

The model features dynamic operational drivers:
* **Revenue Growth:** Tapers from 13.2% in FY26E to 9.0% in FY30E.
* **COGS Margin:** Anchored to the historical average gross margin (59.6% COGS / 40.4% gross margin).
* **Working Capital:** Forecast drivers use DSO 20.4 days, DIO 116.1 days, and DPO 256.4 days.
* **Capital Investments:** Capex averages 2.3% of revenue; depreciation averages 2.5% of opening modeled net block. The modeled net block moves from 26,731.3 to 26,700.8 crore by FY30E.
* **Debt Trajectory:** Scheduled repayments lower debt from 2,819.5 to 0.0 crore by FY30E; final-year interest expense is 13.7 crore.

---

## 4. Sensitivity Matrix: WACC vs. Terminal Growth Rate

The 2-way sensitivity table displays the sensitivity of Fair Value per Share (INR) across cost of capital and terminal growth rates:

| WACC ↓ \ Growth → | 4.5% | 5.0% | 5.5% | 6.0% | 6.5% |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **6.9%** | INR 1216 | INR 1508 | INR 2005 | INR 3044 | INR 6571 |
| **7.9%** | INR 858 | INR 989 | INR 1173 | INR 1454 | INR 1933 |
| **8.9% (Base)** | INR 662 | INR 735 | INR 828 | INR 954 | INR 1132 |
| **9.9%** | INR 538 | INR 584 | INR 640 | INR 709 | INR 800 |
| **10.9%** | INR 453 | INR 484 | INR 521 | INR 564 | INR 618 |

---

## 5. Monte Carlo Stochastic Risk Simulation

A 10,000-run Monte Carlo simulation incorporating normal volatility on WACC (sigma = 75 bps), terminal growth (sigma = 50 bps), and operational cash flows (sigma = 8.0%) reveals:

* **Mean Fair Value:** INR 899
* **Median Fair Value:** INR 828
* **Standard Deviation:** INR 308.6
* **5th Percentile (95% Confidence VaR Lower Bound):** **INR 577**
* **25th Percentile:** INR 703
* **75th Percentile:** INR 1002
* **95th Percentile (Bull Ceiling):** **INR 1458**
* **Probability of Undervaluation:** **16.4%** of simulation runs exceed the current market price of INR 1118.

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
