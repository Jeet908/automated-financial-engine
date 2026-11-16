"""
startup.py — StartupMetrics: SaaS / startup-specific KPIs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class StartupOutput:
    arr: float = 0.0
    mrr: float = 0.0
    arr_growth: float = 0.0           # YoY ARR growth rate
    net_dollar_retention: float = 0.0  # NDR
    cac: float = 0.0
    ltv: float = 0.0
    ltv_cac_ratio: float = 0.0
    burn_rate: float = 0.0            # monthly cash burn
    runway_months: float = 0.0
    burn_multiple: float = 0.0        # burn / net_new_arr


class StartupMetrics:
    """Computes startup / SaaS KPIs from raw metric data."""

    def compute(self, data: dict) -> StartupOutput:
        """
        data keys (all optional with sensible defaults):
          arr_series      : list[float]  — ARR each period
          mrr_series      : list[float]  — MRR each period
          cash_balance    : float
          monthly_burn    : float
          sales_marketing_spend : float
          new_customers   : int
          churned_arr     : float
          expansion_arr   : float
          gross_margin    : float  (0–1)
          churn_rate      : float  (monthly, 0–1)
          net_new_arr     : float
        """
        arr_series = data.get("arr_series", [])
        mrr_series = data.get("mrr_series", [])

        # ARR / MRR
        arr = arr_series[-1] if arr_series else data.get("arr", 0.0)
        mrr = mrr_series[-1] if mrr_series else data.get("mrr", arr / 12.0 if arr else 0.0)

        # ARR growth
        if len(arr_series) >= 2 and arr_series[-2] > 0:
            arr_growth = (arr_series[-1] / arr_series[-2]) - 1.0
        else:
            arr_growth = data.get("arr_growth", 0.0)

        # NDR = (starting ARR + expansion - churn) / starting ARR
        starting_arr = arr_series[-2] if len(arr_series) >= 2 else data.get("starting_arr", arr)
        expansion_arr = data.get("expansion_arr", 0.0)
        churned_arr = data.get("churned_arr", 0.0)
        if starting_arr > 0:
            ndr = (starting_arr + expansion_arr - churned_arr) / starting_arr
        else:
            ndr = data.get("net_dollar_retention", 1.0)

        # CAC = sales & marketing spend / new customers
        sm_spend = data.get("sales_marketing_spend", 0.0)
        new_customers = data.get("new_customers", 1)
        cac = sm_spend / new_customers if new_customers else data.get("cac", 0.0)

        # LTV = gross_margin * arpu / churn_rate
        gross_margin = data.get("gross_margin", 0.70)
        churn_rate = data.get("churn_rate", 0.02)  # monthly
        total_customers = data.get("total_customers", new_customers)
        arpu = arr / total_customers / 12.0 if total_customers else 0.0  # monthly ARPU
        ltv = (gross_margin * arpu / churn_rate) if churn_rate > 0 else 0.0
        ltv_cac_ratio = ltv / cac if cac > 0 else 0.0

        # Burn
        burn_rate = data.get("monthly_burn", 0.0)
        cash = data.get("cash_balance", 0.0)
        runway_months = cash / burn_rate if burn_rate > 0 else float("inf")

        # Burn Multiple = net cash burned / net new ARR
        net_new_arr = data.get("net_new_arr", expansion_arr - churned_arr)
        burn_multiple = (burn_rate * 12.0) / net_new_arr if net_new_arr > 0 else float("inf")

        return StartupOutput(
            arr=arr,
            mrr=mrr,
            arr_growth=arr_growth,
            net_dollar_retention=ndr,
            cac=cac,
            ltv=ltv,
            ltv_cac_ratio=ltv_cac_ratio,
            burn_rate=burn_rate,
            runway_months=runway_months,
            burn_multiple=burn_multiple,
        )

    def arr_mrr_bridge(
        self, arr_series: List[float], mrr_series: List[float]
    ) -> List[dict]:
        """
        Returns a bridge list showing implied MRR (ARR/12) vs reported MRR each period.
        """
        bridge = []
        for i, (arr, mrr) in enumerate(zip(arr_series, mrr_series)):
            implied_mrr = arr / 12.0
            bridge.append({
                "period": i,
                "arr": arr,
                "mrr": mrr,
                "implied_mrr": implied_mrr,
                "discrepancy": mrr - implied_mrr,
            })
        return bridge

    def cohort_retention(self, cohort_data: List[List[float]]) -> List[List[float]]:
        """
        cohort_data: list of cohorts, each a list of retained_revenue per period.
        Returns retention rates relative to cohort[0].
        e.g. [[100, 85, 70], [120, 100]] → [[1.0, 0.85, 0.70], [1.0, 0.833]]
        """
        result = []
        for cohort in cohort_data:
            if cohort and cohort[0] > 0:
                rates = [v / cohort[0] for v in cohort]
            else:
                rates = [0.0] * len(cohort)
            result.append(rates)
        return result
