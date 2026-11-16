"""
High-level FinancialEngine orchestrator and FinancialModel representation.
Coordinates 3-statement modeling, supporting schedules, valuation, and simulation.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from pathlib import Path

from financial_engine.core.types import (
    ModelConfiguration,
    CompanyMetadata,
    ScenarioType,
)
from financial_engine.core.accounting import AccountingVerifier, AuditCertificate
from financial_engine.schedules.working_capital import (
    WorkingCapitalSchedule,
    build_working_capital_schedule,
)
from financial_engine.schedules.fixed_assets import (
    FixedAssetsSchedule,
    build_fixed_assets_schedule,
)
from financial_engine.schedules.debt import (
    DebtSchedule,
    build_debt_schedule,
)
from financial_engine.schedules.equity import (
    EquitySchedule,
    build_equity_schedule,
)
from financial_engine.statements.income_statement import (
    IncomeStatement,
    build_income_statement,
)
from financial_engine.statements.cash_flow import (
    CashFlowStatement,
    build_cash_flow_statement,
)
from financial_engine.statements.balance_sheet import (
    BalanceSheet,
    build_balance_sheet,
)
from financial_engine.valuation.dcf import DCFResult, run_dcf_valuation
from financial_engine.valuation.wacc import calculate_wacc, WACCResult
from financial_engine.valuation.comps import CompsResult, run_comps_analysis
from financial_engine.valuation.lbo import LBOResult, run_lbo_screening
from financial_engine.simulation.sensitivity import (
    SensitivityMatrix,
    build_wacc_growth_sensitivity,
)
from financial_engine.simulation.scenarios import (
    ScenarioSummary,
    ScenarioOutcome,
    create_scenario_configurations,
)
from financial_engine.simulation.monte_carlo import (
    MonteCarloStats,
    run_monte_carlo_simulation,
)


@dataclass
class FinancialModel:
    """Fully linked, institutional 3-statement and valuation model."""
    config: ModelConfiguration
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement
    working_capital: WorkingCapitalSchedule
    fixed_assets: FixedAssetsSchedule
    debt_schedule: DebtSchedule
    equity_schedule: EquitySchedule
    dcf_result: DCFResult
    comps_result: CompsResult
    lbo_result: LBOResult
    sensitivity: SensitivityMatrix
    scenarios: ScenarioSummary
    monte_carlo: MonteCarloStats
    audit_certificate: AuditCertificate

    @property
    def is_balanced(self) -> bool:
        return self.audit_certificate.is_valid

    @property
    def value_per_share(self) -> float:
        return self.dcf_result.value_per_share

    @property
    def enterprise_value(self) -> float:
        return self.dcf_result.enterprise_value

    @property
    def equity_value(self) -> float:
        return self.dcf_result.equity_value

    @property
    def wacc(self) -> float:
        return self.dcf_result.wacc


class FinancialEngine:
    """Production-ready Autonomous Financial Modeling & Valuation Engine."""

    def __init__(self, config: Optional[ModelConfiguration] = None):
        self.config = config or ModelConfiguration()

    @classmethod
    def from_template(cls, template_name: str = "kaveri_foods") -> "FinancialEngine":
        """Loads a predefined corporate configuration template."""
        data_dir = Path(__file__).parent / "data"
        template_file = data_dir / f"{template_name}.json"
        if template_file.exists():
            config = ModelConfiguration.from_json_file(str(template_file))
        else:
            # Default to standard Kaveri Foods baseline
            config = ModelConfiguration()
        return cls(config)

    @classmethod
    def from_json(cls, json_path: str) -> "FinancialEngine":
        """Loads a model configuration from a JSON file."""
        config = ModelConfiguration.from_json_file(json_path)
        return cls(config)

    def solve(self, run_mc: bool = True, mc_iterations: int = 10000) -> FinancialModel:
        """
        Solves the complete 3-statement model, supporting schedules,
        valuation, and simulation pipeline with zero human intervention.
        """
        cfg = self.config
        hist = cfg.historicals
        assump = cfg.assumptions
        val_in = cfg.valuation_inputs
        n_proj = len(assump.revenue_growth)

        # 1. Project Revenues
        proj_rev: List[float] = []
        curr_r = hist.revenue[-1]
        for g in assump.revenue_growth:
            curr_r = curr_r * (1.0 + g)
            proj_rev.append(curr_r)

        # 2. Determine COGS % assumption
        if assump.cogs_pct_revenue is not None:
            cogs_pct_list = assump.cogs_pct_revenue
        else:
            hist_gm = [(hist.revenue[i] - hist.cogs[i]) / hist.revenue[i] for i in range(len(hist.revenue))]
            avg_gm = sum(hist_gm) / len(hist_gm)
            cogs_pct_list = [1.0 - avg_gm] * n_proj

        proj_cogs = [proj_rev[i] * cogs_pct_list[i] for i in range(n_proj)]

        # 3. Build Fixed Assets Schedule
        fixed_assets = build_fixed_assets_schedule(
            hist_net_block=hist.net_fixed_assets,
            proj_revenue=proj_rev,
            proj_capex_pct=assump.capex_pct_revenue,
            proj_depr_pct=assump.depreciation_pct_opening_nb,
        )

        # 4. Build Debt Schedule
        debt_sched = build_debt_schedule(
            hist_debt=hist.debt,
            proj_repayment=assump.debt_repayment,
            proj_interest_rate=assump.interest_rate,
        )

        # 5. Build Working Capital Schedule
        working_cap = build_working_capital_schedule(
            hist_revenue=hist.revenue,
            hist_cogs=hist.cogs,
            hist_ar=hist.receivables,
            hist_inv=hist.inventory,
            hist_ap=hist.payables,
            proj_revenue=proj_rev,
            proj_cogs=proj_cogs,
            proj_dso=assump.receivable_days,
            proj_dio=assump.inventory_days,
            proj_dpo=assump.payable_days,
        )

        # Extract projected ΔNWC (the last n_proj elements of change_in_nwc)
        proj_delta_nwc = working_cap.change_in_nwc[-n_proj:]

        # 6. Build Income Statement
        income_stmt = build_income_statement(
            historicals=hist,
            assumptions=assump,
            sched_depreciation=fixed_assets.depreciation,
            sched_interest=debt_sched.interest_expense,
        )

        proj_pat = income_stmt.pat[-n_proj:]
        proj_ebit = income_stmt.ebit[-n_proj:]
        proj_ebitda = income_stmt.ebitda[-n_proj:]
        proj_dividends = income_stmt.dividends[-n_proj:]

        # 7. Build Cash Flow Statement
        cash_flow = build_cash_flow_statement(
            base_cash=hist.cash[-1],
            proj_net_profit=proj_pat,
            proj_depreciation=fixed_assets.depreciation,
            proj_delta_nwc=proj_delta_nwc,
            proj_capex=fixed_assets.capex,
            proj_debt_repayment=debt_sched.repayment,
            proj_dividends=proj_dividends,
        )

        # 8. Build Equity Schedule
        equity_sched = build_equity_schedule(
            hist_share_capital=hist.share_capital,
            hist_retained_earnings=hist.retained_earnings,
            proj_net_profit=proj_pat,
            proj_dividends=proj_dividends,
        )

        # 9. Build Balance Sheet
        # Extract projection items from schedules
        proj_ar = working_cap.receivables[-n_proj:]
        proj_inv = working_cap.inventory[-n_proj:]
        proj_ap = working_cap.payables[-n_proj:]
        proj_nb = fixed_assets.closing_net_block
        proj_debt = debt_sched.closing_debt
        proj_cash = cash_flow.closing_cash

        balance_sheet = build_balance_sheet(
            historicals=hist,
            proj_cash=proj_cash,
            proj_receivables=proj_ar,
            proj_inventory=proj_inv,
            proj_net_fixed_assets=proj_nb,
            proj_payables=proj_ap,
            proj_debt=proj_debt,
            proj_share_capital=equity_sched.share_capital,
            proj_retained_earnings=equity_sched.closing_retained_earnings,
        )

        # 10. Accounting Verification Audit
        audit_data = {
            "bs_total_assets": balance_sheet.total_assets,
            "bs_total_liab_equity": balance_sheet.total_liabilities_equity,
            "cf_opening_cash": cash_flow.opening_cash,
            "cf_closing_cash": cash_flow.closing_cash,
            "cf_net_change": cash_flow.net_change_in_cash,
            "re_opening": equity_sched.opening_retained_earnings,
            "re_closing": equity_sched.closing_retained_earnings,
            "pat": proj_pat,
            "dividends": proj_dividends,
            "nb_opening": fixed_assets.opening_net_block,
            "nb_closing": fixed_assets.closing_net_block,
            "capex": fixed_assets.capex,
            "depreciation": fixed_assets.depreciation,
            "debt_opening": debt_sched.opening_debt,
            "debt_closing": debt_sched.closing_debt,
            "debt_repayment": debt_sched.repayment,
            "nwc": working_cap.net_working_capital,
            "delta_nwc": working_cap.change_in_nwc,
        }
        verifier = AccountingVerifier()
        audit_cert = verifier.verify_all(audit_data)

        # 11. Run DCF Valuation
        marginal_tax = assump.tax_rate[-1]
        dcf_res = run_dcf_valuation(
            proj_ebit=proj_ebit,
            proj_ebitda=proj_ebitda,
            proj_depreciation=fixed_assets.depreciation,
            proj_capex=fixed_assets.capex,
            proj_delta_nwc=proj_delta_nwc,
            base_debt=hist.debt[-1],
            base_cash=hist.cash[-1],
            marginal_tax_rate=marginal_tax,
            inputs=val_in,
        )

        # 12. Run Comps Analysis
        target_ebitda_base = hist.revenue[-1] - hist.cogs[-1] - hist.employee_costs[-1] - hist.other_expenses[-1]
        target_pat_base = hist.revenue[-1] - hist.cogs[-1] - hist.employee_costs[-1] - hist.other_expenses[-1] - hist.depreciation[-1] - hist.interest[-1] - hist.tax[-1]
        comps_res = run_comps_analysis(
            target_ebitda=target_ebitda_base,
            target_net_income=target_pat_base,
            target_revenue=hist.revenue[-1],
            target_net_debt=hist.debt[-1] - hist.cash[-1],
            shares_outstanding=val_in.shares_outstanding,
        )

        # 13. Run LBO Screening
        fcff_5yr_sum = sum(dcf_res.fcff)
        lbo_res = run_lbo_screening(
            base_ebitda=target_ebitda_base,
            exit_ebitda=proj_ebitda[-1],
            fcff_cash_generated=fcff_5yr_sum,
            entry_multiple=val_in.exit_multiple_ev_ebitda,
            exit_multiple=val_in.exit_multiple_ev_ebitda,
        )

        # 14. Run 2D Sensitivity Analysis (WACC vs Terminal Growth)
        sensitivity = build_wacc_growth_sensitivity(
            fcff_list=dcf_res.fcff,
            base_debt=hist.debt[-1],
            base_cash=hist.cash[-1],
            shares_outstanding=val_in.shares_outstanding,
            center_wacc=dcf_res.wacc,
            center_growth=val_in.terminal_growth_rate,
        )

        # 15. Run Scenario Manager
        scenario_configs = create_scenario_configurations(cfg)
        scenario_outcomes: List[ScenarioOutcome] = []
        weights = {ScenarioType.BULL: 0.25, ScenarioType.BASE: 0.50, ScenarioType.BEAR: 0.25}

        for sc_type, sc_cfg in scenario_configs.items():
            if sc_type == ScenarioType.BASE:
                scenario_outcomes.append(ScenarioOutcome(
                    scenario_type=sc_type,
                    probability=weights[sc_type],
                    enterprise_value=dcf_res.enterprise_value,
                    equity_value=dcf_res.equity_value,
                    value_per_share=dcf_res.value_per_share,
                    revenue_cagr=(proj_rev[-1] / hist.revenue[-1]) ** (1.0 / n_proj) - 1.0,
                    terminal_ebitda=proj_ebitda[-1],
                    wacc=dcf_res.wacc,
                ))
            else:
                # Solve sub-model for Bull / Bear
                sub_engine = FinancialEngine(sc_cfg)
                sub_model = sub_engine.solve(run_mc=False)
                sub_rev = sub_model.income_statement.revenue[-n_proj:]
                scenario_outcomes.append(ScenarioOutcome(
                    scenario_type=sc_type,
                    probability=weights[sc_type],
                    enterprise_value=sub_model.enterprise_value,
                    equity_value=sub_model.equity_value,
                    value_per_share=sub_model.value_per_share,
                    revenue_cagr=(sub_rev[-1] / hist.revenue[-1]) ** (1.0 / n_proj) - 1.0,
                    terminal_ebitda=sub_model.income_statement.ebitda[-1],
                    wacc=sub_model.wacc,
                ))

        expected_share_price = sum(sc.probability * sc.value_per_share for sc in scenario_outcomes)
        bull_sc = next(sc for sc in scenario_outcomes if sc.scenario_type == ScenarioType.BULL)
        bear_sc = next(sc for sc in scenario_outcomes if sc.scenario_type == ScenarioType.BEAR)
        base_val = dcf_res.value_per_share
        bull_up = ((bull_sc.value_per_share / base_val) - 1.0) * 100.0 if base_val > 0 else 0.0
        bear_down = ((bear_sc.value_per_share / base_val) - 1.0) * 100.0 if base_val > 0 else 0.0

        scenario_summary = ScenarioSummary(
            scenarios=scenario_outcomes,
            expected_value_per_share=expected_share_price,
            bull_upside_pct=bull_up,
            bear_downside_pct=bear_down,
        )

        # 16. Run Monte Carlo Simulation
        if run_mc:
            monte_carlo = run_monte_carlo_simulation(
                base_ebitda=target_ebitda_base,
                fcff_base_list=dcf_res.fcff,
                base_debt=hist.debt[-1],
                base_cash=hist.cash[-1],
                shares_outstanding=val_in.shares_outstanding,
                base_wacc=dcf_res.wacc,
                base_growth=val_in.terminal_growth_rate,
                current_market_price=val_in.current_market_price,
                iterations=mc_iterations,
            )
        else:
            monte_carlo = MonteCarloStats(
                iterations=0,
                mean_price=dcf_res.value_per_share,
                median_price=dcf_res.value_per_share,
                std_dev=0.0,
                min_price=dcf_res.value_per_share,
                max_price=dcf_res.value_per_share,
                pct_5=dcf_res.value_per_share * 0.8,
                pct_10=dcf_res.value_per_share * 0.85,
                pct_25=dcf_res.value_per_share * 0.92,
                pct_75=dcf_res.value_per_share * 1.08,
                pct_90=dcf_res.value_per_share * 1.15,
                pct_95=dcf_res.value_per_share * 1.20,
                prob_undervalued=50.0,
            )

        return FinancialModel(
            config=cfg,
            income_statement=income_stmt,
            balance_sheet=balance_sheet,
            cash_flow=cash_flow,
            working_capital=working_cap,
            fixed_assets=fixed_assets,
            debt_schedule=debt_sched,
            equity_schedule=equity_sched,
            dcf_result=dcf_res,
            comps_result=comps_res,
            lbo_result=lbo_res,
            sensitivity=sensitivity,
            scenarios=scenario_summary,
            monte_carlo=monte_carlo,
            audit_certificate=audit_cert,
        )
