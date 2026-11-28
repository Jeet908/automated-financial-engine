# QUANTITATIVE VALUATION SENSITIVITY & MACROECONOMIC STRESS TEST

**PREPARED BY:** Lead Autonomous Principal Financial Architect & Full-Stack Quantitative Engineer  
**BENCHMARK TARGET:** Kaveri Foods Ltd (`KAVERI`)  
**DATE:** November 15, 2026  

---

## 1. Executive Summary: Assumption Perturbation Impact

This stress-testing framework isolates the sensitivities of the valuation engine to macroeconomic shocks, capital structure variations, and operational inflection points.

```
+---------------------------------------------------------------------------------------------------+
| BASE CASE DCF FAIR VALUE: Rs 252 | CURRENT MARKET PRICE: Rs 210 | IMPLIED BASE UPSIDE: +19.8%      |
+---------------------------------------------------------------------------------------------------+
|  SCENARIO                     WACC      TERM GROWTH   EBITDA MARG   FV/SHARE   DELTA vs BASE     |
|---------------------------------------------------------------------------------------------------|
|  Base Case                   11.59%        5.00%         20.4%       Rs 252        —              |
|  Scenario A: Stagflation     13.56%        4.00%         18.9%       Rs 177      -29.8%           |
|  Scenario B: Capex Surge     11.59%        5.00%         20.4%       Rs 239       -5.2%           |
|  Scenario C: Blue-Sky Opt    11.10%        5.50%         22.4%       Rs 324      +28.6%           |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. In-Depth Scenario Analysis

### Scenario A: Macro Stagflation & Rate Hike Shock
* **Macro Driver:** Central bank policy rate hikes (+100 bps) and persistent input cost inflation.
* **WACC Parameters:**
  * Risk-Free Rate ($R_f$): $6.50\% \to \mathbf{7.50\%}$
  * Pre-Tax Cost of Debt ($K_d$): $9.00\% \to \mathbf{10.50\%}$
  * Beta ($\beta$): $0.90 \to \mathbf{1.05}$
  * Cost of Equity ($K_e$): $12.80\% \to \mathbf{14.85\%}$
  * Blended WACC: $11.59\% \to \mathbf{13.56\%}$ (+197 bps)
* **Operational Shift:**
  * Gross Margin compresses -150 bps due to packaging/raw food inflation.
  * Terminal growth compresses to **4.00%** (-100 bps).
* **Valuation Impact:**
  * **Enterprise Value:** Rs 1,768.2 Cr (down from Rs 2,516.4 Cr)
  * **Implied Equity Value:** Rs 1,797.7 Cr
  * **Fair Value Per Share:** **Rs 177**
  * **Market Verdict:** Current trading price of Rs 210 represents a **15.7% premium (Overvalued)**.

---

### Scenario B: Capex Super-Cycle & Aggressive Capacity Expansion
* **Strategic Driver:** Management undertakes a greenfield plant expansion to double capacity.
* **Capex Intensity:** Capex as % of Revenue increases from $5.00\% \to \mathbf{9.00\%}$ (+400 bps).
* **Financing:** Scheduled debt repayment is paused; total debt held at Rs 240 Cr.
* **FCFF Mechanics:**
  * Reinvestment rate surges; explicit 5-year FCFF is reduced from Rs 638.5 Cr to **Rs 421.0 Cr** (-34.1%).
  * Post-FY30 normalized cash flows generate higher return on invested capital.
* **Valuation Impact:**
  * **Enterprise Value:** Rs 2,385.0 Cr
  * **Fair Value Per Share:** **Rs 239** (-5.2% vs Base)
  * **Market Verdict:** Even during peak capex drag, fair value exceeds current market price by **+13.8%**.

---

### Scenario C: Blue-Sky Margin Expansion & Working Capital Optimization
* **Strategic Driver:** Product mix shifts toward high-margin premium packaged snacks, alongside supply chain digitization.
* **Operational Gains:**
  * Gross Margin expands +200 bps to **44.4%**.
  * EBITDA Margin reaches **22.4%** (+200 bps).
  * Receivable Days improve from $30 \to \mathbf{24\text{ days}}$ (-6 days DSO).
  * Inventory Days improve from $45 \to \mathbf{38\text{ days}}$ (-7 days DIO).
  * Working Capital efficiency releases **Rs 45.2 Cr** of incremental cash flow.
* **WACC & Terminal Adjustments:**
  * Risk-Free Rate softens to 6.00%; WACC moderates to **11.10%**.
  * Terminal Growth expands to **5.50%** (+50 bps).
* **Valuation Impact:**
  * **Enterprise Value:** Rs 3,240.0 Cr (+28.8% vs Base)
  * **Implied Equity Value:** Rs 3,269.5 Cr
  * **Fair Value Per Share:** **Rs 324** (+28.6% vs Base)
  * **Market Verdict:** **+54.3% Upside** relative to market price of Rs 210.

---

## 3. Two-Dimensional Parameter Cross-Elasticity

The table below illustrates the cross-elasticity of Implied Share Price (Rs) to simultaneous shifts in **WACC** ($\pm 200\text{ bps}$) and **EBITDA Margin** ($\pm 200\text{ bps}$):

| WACC \ EBITDA Margin | 18.4% (-200 bps) | 19.4% (-100 bps) | **20.4% (Base)** | 21.4% (+100 bps) | 22.4% (+200 bps) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **9.59% (-200 bps)** | Rs 304 | Rs 326 | Rs 348 | Rs 370 | Rs 392 |
| **10.59% (-100 bps)**| Rs 255 | Rs 273 | Rs 292 | Rs 310 | Rs 329 |
| **11.59% (Base)**    | Rs 220 | Rs 236 | **Rs 252** | Rs 268 | Rs 284 |
| **12.59% (+100 bps)**| Rs 193 | Rs 207 | Rs 221 | Rs 235 | Rs 249 |
| **13.59% (+200 bps)**| Rs 172 | Rs 184 | Rs 196 | Rs 208 | Rs 221 |

---

## 4. Architectural Summary

1. **WACC is the Primary Value Deflator:** A $\pm 100\text{ bps}$ change in WACC induces a $\mp 12.3\%$ change in enterprise value.
2. **Terminal Growth Asymmetry:** Growth rate sensitivity increases non-linearly as $g \to WACC$ due to Gordon Growth denominator compression ($WACC - g$).
3. **Working Capital Convexity:** Shortening working capital cycle days directly enhances equity value with zero capital expenditure cost.
