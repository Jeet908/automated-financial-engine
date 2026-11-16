"""
Strict benchmark test against Kaveri Foods tutor specification (SKILL.md).
"""

import pytest
from financial_engine.engine import FinancialEngine


def test_kaveri_foods_benchmark_values():
    engine = FinancialEngine.from_template("kaveri_foods")
    model = engine.solve(run_mc=False)

    is_stmt = model.income_statement
    bs_stmt = model.balance_sheet
    dcf = model.dcf_result
    sens = model.sensitivity

    # 1. Historical IS checks (Module 1)
    assert round(is_stmt.revenue[0], 1) == 1000.0
    assert round(is_stmt.revenue[2], 1) == 1243.2
    assert round(is_stmt.cogs[2], 1) == 716.1
    assert round(is_stmt.gross_profit[2], 1) == 527.1  # Step 1.4: IS!E7 = 527.1
    assert round(is_stmt.ebitda[2], 1) == 258.6        # Step 1.5: IS!E10 = 258.6
    assert round(is_stmt.ebit[2], 1) == 215.6          # Step 1.6: IS!E12 = 215.6
    assert round(is_stmt.pbt[2], 1) == 192.6           # Step 1.7: IS!E14 = 192.6
    assert round(is_stmt.pat[2], 1) == 144.1           # Step 1.8: IS!E16 = 144.1

    # 2. Historical BS checks (Module 1)
    assert round(bs_stmt.net_fixed_assets[2], 1) == 465.0  # Step 1.9: BS!E8 = 465.0
    assert round(bs_stmt.total_assets[2], 1) == 985.9       # Step 1.10: BS!E9 = 985.9
    assert round(bs_stmt.retained_earnings[2], 1) == 578.2  # Step 1.11: BS!E14 = 578.2
    assert round(bs_stmt.total_liabilities_equity[2], 1) == 985.9  # Step 1.12: BS!E15 = 985.9
    assert round(bs_stmt.balance_check[2], 1) == 0.0        # Step 1.13: BS!E17 = 0.0

    # 3. Projected IS checks (Module 4 & 8)
    # Revenue FY26 (Step 4.1) & FY30 (Step 4.2)
    assert round(is_stmt.revenue[3], 1) == 1392.4
    assert round(is_stmt.revenue[7], 1) == 2001.4
    # COGS FY30 (Step 4.3)
    assert round(is_stmt.cogs[7], 1) == 1161.5
    # Gross Profit FY30 (Step 4.4)
    assert round(is_stmt.gross_profit[7], 1) == 839.9
    # Employee costs FY30 (Step 4.5)
    assert round(is_stmt.employee_costs[7], 1) == 194.1
    # Other expenses FY30 (Step 4.6)
    assert round(is_stmt.other_expenses[7], 1) == 238.2
    # EBITDA FY30 (Step 4.7)
    assert round(is_stmt.ebitda[7], 1) == 407.6
    # EBIT FY30 (Step 8.1)
    assert round(is_stmt.ebit[7], 1) == 348.8
    # PBT FY30 (Step 8.2)
    assert round(is_stmt.pbt[7], 1) == 339.4
    # Tax FY30 (Step 8.3)
    assert round(is_stmt.tax[7], 1) == 85.4
    # Net Profit FY30 (Step 8.4)
    assert round(is_stmt.pat[7], 1) == 254.0

    # 4. Projected Schedules checks (Module 5, 6, 7)
    # Receivables FY30 (Step 5.3)
    assert round(model.working_capital.receivables[7], 1) == 246.7
    # Inventory FY30 (Step 5.4)
    assert round(model.working_capital.inventory[7], 1) == 159.1
    # Payables FY30 (Step 5.5)
    assert round(model.working_capital.payables[7], 1) == 190.9
    # NWC FY30 (Step 5.6)
    assert round(model.working_capital.net_working_capital[7], 1) == 214.9
    # Capex FY30 (Step 6.3)
    assert round(model.fixed_assets.capex[-1], 1) == 100.1
    # Depreciation FY30 (Step 6.4)
    assert round(model.fixed_assets.depreciation[-1], 1) == 58.8
    # Closing Net Block FY30 (Step 6.5)
    assert round(model.fixed_assets.closing_net_block[-1], 1) == 628.9
    # Closing Debt FY30 (Step 7.4)
    assert round(model.debt_schedule.closing_debt[-1], 1) == 90.0
    # Interest FY30 (Step 7.5)
    assert round(model.debt_schedule.interest_expense[-1], 1) == 9.4

    # 5. Projected Cash Flow checks (Module 9)
    # CFO FY30 (Step 9.4)
    assert round(model.cash_flow.cash_from_operations[-1], 1) == 296.8
    # CFI FY30 (Step 9.5)
    assert round(model.cash_flow.cash_from_investing[-1], 1) == -100.1
    # Net Change in Cash FY30 (Step 9.8)
    assert round(model.cash_flow.net_change_in_cash[-1], 1) == 103.2
    # Closing Cash FY26 (Step 9.9) & FY30 (Step 10.1)
    assert round(model.cash_flow.closing_cash[0], 1) == 322.2
    assert round(model.cash_flow.closing_cash[-1], 1) == 657.1

    # 6. Projected Balance Sheet checks (Module 10)
    assert round(bs_stmt.cash[7], 1) == 657.1
    assert round(bs_stmt.total_assets[7], 1) == 1691.8      # Step 10.3: BS!J9 = 1,691.8
    assert round(bs_stmt.retained_earnings[7], 1) == 1360.9 # Step 10.6: BS!J14 = 1,360.9
    assert round(bs_stmt.total_liabilities_equity[7], 1) == 1691.8
    for chk in bs_stmt.balance_check:
        assert abs(chk) < 1e-4                              # Step 10.7: BS!J17 = 0.0

    # 7. DCF Valuation checks (Module 11)
    # FCFF FY30 (Step 11.3)
    assert round(dcf.fcff[-1], 1) == 203.8
    # Cost of Equity (Step 11.4)
    assert round(dcf.wacc_details.cost_of_equity * 100, 1) == 12.8
    # WACC (Step 11.5)
    assert round(dcf.wacc * 100, 1) == 11.6
    # Discount factor FY30 (Step 11.6)
    assert round(dcf.discount_factors[-1], 3) == 0.578
    # PV of FCFF FY30 (Step 11.7)
    assert round(dcf.pv_fcff[-1], 1) == 117.8
    # PV of Terminal Value (Step 11.8)
    assert round(dcf.pv_terminal_value_gordon, 1) == 1877.9
    # Enterprise Value (Step 11.9)
    assert round(dcf.enterprise_value, 1) == 2516.4
    # Value per share (Step 11.10)
    assert round(dcf.value_per_share) == 252

    # 8. Sensitivity Matrix checks (Module 12)
    # Center cell F44 (Step 12.2)
    assert round(sens.center_value) == 252
    # Top-left corner cell D42 (Step 12.1)
    assert round(sens.matrix[0][0]) == 307
