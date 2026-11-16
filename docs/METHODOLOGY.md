# QUANTITATIVE METHODOLOGY & FINANCIAL VALUATION FRAMEWORK

## 1. Three-Statement Dynamic Linkage Mechanics

The engine solves the three primary financial statements in an exact, non-circular sequence that guarantees identical balance sheet equality ($\text{Assets} \equiv \text{Liabilities} + \text{Equity}$) with **zero plug error**:

### A. Income Statement Dynamics
1. **Revenue Forecasting:**  
   $$\text{Revenue}_t = \text{Revenue}_{t-1} \times (1 + g_t)$$
2. **COGS Driver:**  
   $$\text{COGS}_t = \text{Revenue}_t \times \text{COGS}\%_t$$  
   *(If not explicitly provided, $\text{COGS}\% = 1 - \frac{1}{N}\sum_{i=1}^N \frac{\text{Gross Profit}_i}{\text{Revenue}_i}$)*
3. **EBITDA:**  
   $$\text{EBITDA}_t = \text{Gross Profit}_t - \text{Employee Costs}_t - \text{Other Operating Expenses}_t$$
4. **Operating Profit (EBIT):**  
   $$\text{EBIT}_t = \text{EBITDA}_t - \text{Depreciation}_t$$  
   *(Depreciation flows in dynamically from the Fixed Assets Schedule)*
5. **Profit Before Tax (PBT):**  
   $$\text{PBT}_t = \text{EBIT}_t - \text{Interest}_t$$  
   *(Interest expense flows in dynamically from the Debt Schedule)*
6. **Net Profit (PAT):**  
   $$\text{PAT}_t = \text{PBT}_t \times (1 - t_t)$$

---

## 2. Supporting Schedules

### A. Working Capital Schedule
* **Receivable Days (DSO):** $\text{DSO} = \frac{\text{Accounts Receivable}}{\text{Revenue}} \times 365$
* **Inventory Days (DIO):** $\text{DIO} = \frac{\text{Inventory}}{\text{COGS}} \times 365$
* **Payable Days (DPO):** $\text{DPO} = \frac{\text{Accounts Payable}}{\text{COGS}} \times 365$
* **Forecast Balances:**
  $$\text{AR}_t = \frac{\text{DSO}_t}{365} \times \text{Revenue}_t, \quad \text{Inv}_t = \frac{\text{DIO}_t}{365} \times \text{COGS}_t, \quad \text{AP}_t = \frac{\text{DPO}_t}{365} \times \text{COGS}_t$$
* **Net Working Capital (NWC):**  
  $$\text{NWC}_t = \text{AR}_t + \text{Inv}_t - \text{AP}_t$$
* **Change in NWC ($\Delta\text{NWC}$):**  
  $$\Delta\text{NWC}_t = \text{NWC}_t - \text{NWC}_{t-1}$$

### B. Fixed Assets Schedule (PP&E Net Block)
$$\text{Opening Net Block}_t = \text{Closing Net Block}_{t-1}$$
$$\text{Capex}_t = \text{Revenue}_t \times \text{Capex}\%_t$$
$$\text{Depreciation}_t = \text{Opening Net Block}_t \times \text{Depr}\%_t$$
$$\text{Closing Net Block}_t = \text{Opening Net Block}_t + \text{Capex}_t - \text{Depreciation}_t$$

### C. Debt Schedule
$$\text{Opening Debt}_t = \text{Closing Debt}_{t-1}$$
$$\text{Closing Debt}_t = \max(0, \text{Opening Debt}_t - \text{Repayment}_t)$$
$$\text{Average Debt}_t = \frac{\text{Opening Debt}_t + \text{Closing Debt}_t}{2}$$
$$\text{Interest Expense}_t = \text{Average Debt}_t \times \text{Interest Rate}_t$$

### D. Cash Flow Reconciliation & Balance Sheet Closure
* **Cash Flow from Operations (CFO):** $\text{CFO}_t = \text{PAT}_t + \text{Depreciation}_t - \Delta\text{NWC}_t$
* **Cash Flow from Investing (CFI):** $\text{CFI}_t = -\text{Capex}_t$
* **Cash Flow from Financing (CFF):** $\text{CFF}_t = -\text{Debt Repayment}_t - \text{Dividends}_t$
* **Net Cash Change:** $\Delta\text{Cash}_t = \text{CFO}_t + \text{CFI}_t + \text{CFF}_t$
* **Closing Cash:** $\text{Cash}_t = \text{Cash}_{t-1} + \Delta\text{Cash}_t$

Closing cash feeds directly into Balance Sheet row 5. Retained Earnings increments by $(\text{PAT}_t - \text{Dividends}_t)$. Because every rupee of net cash generation and working capital movement is mirrored on both sides of the balance sheet, the balance check is identically zero across every period.

---

## 3. Valuation Methodology

### A. Cost of Capital (CAPM / WACC)
* **Cost of Equity:**  
  $$K_e = R_f + \beta_L \times \text{ERP}$$
* **After-Tax Cost of Debt:**  
  $$K_{d,\text{after}} = K_{d,\text{pre}} \times (1 - t)$$
* **WACC:**  
  $$\text{WACC} = \left(\frac{E}{V}\right) K_e + \left(\frac{D}{V}\right) K_{d,\text{after}}$$

### B. Unlevered Free Cash Flow (FCFF)
$$\text{NOPAT}_t = \text{EBIT}_t \times (1 - t_t)$$
$$\text{FCFF}_t = \text{NOPAT}_t + \text{Depreciation}_t - \text{Capex}_t - \Delta\text{NWC}_t$$

### C. Discounting & Terminal Value
$$\text{PV}(\text{FCFF}) = \sum_{t=1}^N \frac{\text{FCFF}_t}{(1 + \text{WACC})^t}$$
$$\text{Terminal Value (Gordon Growth)} = \frac{\text{FCFF}_N \times (1 + g)}{\text{WACC} - g}$$
$$\text{PV}(\text{Terminal Value}) = \frac{\text{Terminal Value}}{(1 + \text{WACC})^N}$$
$$\text{Enterprise Value (EV)} = \text{PV}(\text{FCFF}) + \text{PV}(\text{Terminal Value})$$

### D. Enterprise Value to Equity Value Bridge
$$\text{Equity Value} = \text{EV} - \text{Debt}_{\text{base}} + \text{Cash}_{\text{base}} - \text{Minority Interest} - \text{Preferred Stock}$$
$$\text{Fair Value Per Share} = \frac{\text{Equity Value}}{\text{Diluted Shares Outstanding}}$$

---

## 4. Sensitivity & Monte Carlo Simulation

### A. 2-Way Sensitivity Table
Computes exact analytical share price variations across a $5 \times 5$ grid of $\text{WACC} \in [\text{WACC}-2\%, \text{WACC}+2\%]$ and $g \in [g-1.0\%, g+1.0\%]$.

### B. Monte Carlo Stochastic Modeling
Performs 10,000 simulations drawing parameter perturbations:
* $\text{WACC} \sim \mathcal{N}(\mu_{\text{WACC}}, 0.75\%)$
* $g \sim \mathcal{N}(\mu_g, 0.50\%)$
* $\text{FCFF Shock} \sim \mathcal{N}(1.0, 8.0\%)$

Calculates empirical distribution statistics: Mean, Median, Standard Deviation, 5th Percentile (95% Value at Risk), 95th Percentile, and the Probability of Undervaluation relative to market quote.
