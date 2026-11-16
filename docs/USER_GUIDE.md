# ZERO-TOUCH USER GUIDE & OPERATIONS MANUAL

## 1. Quick Start (Zero-Touch One-Liner)

To run the complete automated financial modeling, valuation, simulation, and packaging pipeline with zero manual configuration, execute from the workspace root:

```bash
python run_engine.py
```

This single command automatically:
1. Loads the benchmark Kaveri Foods corporate profile.
2. Solves the 3-statement financial model across all historical and 5 projection periods.
3. Audits all 6 core accounting identities (Balance Sheet, Cash Flow, Retained Earnings, Fixed Assets, Debt, Working Capital).
4. Solves DCF valuation, CAPM WACC, Trading Multiples, and Sponsor LBO screening.
5. Runs 2D sensitivity analysis and 10,000 Monte Carlo stochastic simulation iterations.
6. Generates institutional deliverables in the `artifacts/` folder:
   - `kaveri_financial_model.xlsx`: Live-formula Excel model with 3-color heatmap.
   - `kaveri_dashboard.html`: Standalone interactive responsive web dashboard.
   - `kaveri_investment_memo.md`: Investment committee executive memo.
   - `kaveri_valuation_output.json`: Structured quantitative payload.
   - `kaveri_audit_certificate.json`: Invariant audit verification certificate.

---

## 2. Command-Line Interface (CLI)

The engine provides a feature-rich CLI for programmatic integration:

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

### CLI Flag Reference
| Flag | Type | Default | Description |
| :--- | :---: | :---: | :--- |
| `--company` | string | `kaveri_foods` | Built-in template name (`kaveri_foods`, `saas_growth`, `industrial_corp`) |
| `--config` | string | `None` | Path to custom input JSON file |
| `--output-dir` | string | `artifacts` | Destination folder for all output deliverables |
| `--mc-iterations`| int | `10000` | Number of stochastic simulation iterations |
| `--no-excel` | flag | `False` | Disables Excel workbook generation |
| `--no-html` | flag | `False` | Disables interactive HTML dashboard generation |
| `--quiet` | flag | `False` | Suppresses terminal banner and output |

---

## 3. Python SDK & Programmatic Usage

You can embed the engine directly into Python quant workflows or web APIs:

```python
from financial_engine import FinancialEngine, ModelConfiguration

# Load template and solve
engine = FinancialEngine.from_template("kaveri_foods")
model = engine.solve(run_mc=True, mc_iterations=10000)

# Access valuation results
print(f"Fair Value Per Share: {model.value_per_share:.2f}")
print(f"Enterprise Value:     {model.enterprise_value:,.2f}")
print(f"WACC:                 {model.wacc * 100:.2f}%")
print(f"Balance Sheet Check:  {model.is_balanced}")

# Access detailed financial line items
fy30_revenue = model.income_statement.revenue[-1]
fy30_ebitda  = model.income_statement.ebitda[-1]
fy30_pat     = model.income_statement.pat[-1]

# Access Monte Carlo risk metrics
mc = model.monte_carlo
print(f"VaR (95% Confidence): {mc.pct_5:.2f}")
print(f"Prob of Undervalued:  {mc.prob_undervalued:.1f}%")
```

---

## 4. Custom Configuration JSON Format

To model any arbitrary company, create a JSON file with the following schema:

```json
{
  "metadata": {
    "name": "Acme Global Corp",
    "ticker": "ACME",
    "industry": "Industrial Technology",
    "currency": "USD",
    "currency_unit": "USD million",
    "shares_unit": "million",
    "historical_years": ["FY23A", "FY24A", "FY25A"],
    "projection_years": ["FY26E", "FY27E", "FY28E", "FY29E", "FY30E"]
  },
  "historicals": {
    "revenue": [500.0, 560.0, 630.0],
    "cogs": [300.0, 336.0, 378.0],
    "employee_costs": [60.0, 67.0, 75.0],
    "other_expenses": [45.0, 50.0, 56.0],
    "depreciation": [25.0, 28.0, 31.0],
    "interest": [12.0, 10.0, 8.0],
    "tax": [14.5, 17.0, 20.5],
    "dividends": [10.0, 12.0, 14.0],
    "cash": [40.0, 50.0, 65.0],
    "receivables": [65.0, 72.0, 80.0],
    "inventory": [45.0, 50.0, 55.0],
    "net_fixed_assets": [250.0, 270.0, 290.0],
    "payables": [50.0, 55.0, 60.0],
    "debt": [150.0, 130.0, 110.0],
    "share_capital": [80.0, 80.0, 80.0],
    "retained_earnings": [120.0, 177.0, 240.0]
  },
  "assumptions": {
    "revenue_growth": [0.10, 0.09, 0.08, 0.07, 0.06],
    "cogs_pct_revenue": [0.60, 0.60, 0.60, 0.60, 0.60],
    "employee_pct_revenue": [0.12, 0.12, 0.12, 0.12, 0.12],
    "other_opex_pct_revenue": [0.09, 0.09, 0.09, 0.09, 0.09],
    "receivable_days": [46.0, 46.0, 46.0, 46.0, 46.0],
    "inventory_days": [53.0, 53.0, 53.0, 53.0, 53.0],
    "payable_days": [58.0, 58.0, 58.0, 58.0, 58.0],
    "capex_pct_revenue": [0.05, 0.05, 0.05, 0.05, 0.05],
    "depreciation_pct_opening_nb": [0.10, 0.10, 0.10, 0.10, 0.10],
    "interest_rate": [0.07, 0.07, 0.07, 0.07, 0.07],
    "debt_repayment": [20.0, 20.0, 20.0, 20.0, 20.0],
    "tax_rate": [0.25, 0.25, 0.25, 0.25, 0.25],
    "dividend_payout": [0.25, 0.25, 0.25, 0.25, 0.25]
  },
  "valuation_inputs": {
    "risk_free_rate": 0.045,
    "beta": 1.05,
    "equity_risk_premium": 0.055,
    "pretax_cost_of_debt": 0.070,
    "debt_weight": 0.25,
    "terminal_growth_rate": 0.030,
    "shares_outstanding": 12.0,
    "exit_multiple_ev_ebitda": 9.0,
    "current_market_price": 42.0
  }
}
```
