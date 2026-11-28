"""
Tests for the Hybrid Deterministic + Agentic Workflow:
  - QuantReviewerAgent & ICThesisAgent (financial_engine.reporting.quant_agents)
  - CoAMappingAgent & DataNormalizer integration (src.ingestion.coa_agent)
"""
from __future__ import annotations

import pandas as pd

from financial_engine.reporting.quant_agents import generate_ic_thesis, review_quant_anomalies
from src.ingestion.coa_agent import CoAMappingAgent
from src.ingestion.normalizer import DataNormalizer


def test_quant_reviewer_flags_anomalies_and_clean_case():
    flagged_output = {
        "Base": {
            "wacc": 0.053,
            "dcf": {
                "enterprise_value": 1000.0,
                "pv_tv": 888.0,
                "terminal_growth_rate": 0.04,
                "beta": 0.45,
            },
        }
    }
    pain_points = {
        "ccc": {"dpo": 145.0, "ccc_days": -75.0},
        "roic": {"value_destruction": True, "roic_pct": 4.2, "wacc_pct": 5.3},
    }
    report = review_quant_anomalies(
        flagged_output,
        meta={"data_tier": "Tier 3 Fallback", "fallback_used": True},
        pain_points=pain_points,
    )
    codes = {a["code"] for a in report["anomalies"]}
    assert report["status"] == "critical"
    assert {
        "LOW_BETA_WACC",
        "TV_CONCENTRATION",
        "WACC_TGR_SPREAD_NARROW",
        "WC_PAYABLES_DRIFT",
        "NEGATIVE_ROIC_SPREAD",
        "TIER3_DATA_FALLBACK",
    }.issubset(codes)

    clean_output = {
        "Base": {
            "wacc": 0.105,
            "dcf": {
                "enterprise_value": 1000.0,
                "pv_tv": 620.0,
                "terminal_growth_rate": 0.025,
                "beta": 1.05,
            },
        }
    }
    clean_report = review_quant_anomalies(clean_output)
    assert clean_report["status"] == "clean"
    assert clean_report["anomaly_count"] == 0


def test_ic_thesis_agent_grounds_company_metrics():
    engine_output = {
        "Base": {
            "wacc": 0.095,
            "income_statement": {
                "revenue": {"FY25A": 1000.0, "FY30E": 1610.5},
                "ebitda": {"FY25A": 250.0, "FY30E": 450.0},
                "gross_profit": {"FY25A": 600.0, "FY30E": 990.0},
            },
        }
    }
    meta = {
        "name": "Acme Biotech",
        "currency": "USD",
        "display_standard": "US GAAP",
        "current_market_price": 100.0,
    }
    dcf_base = {"enterprise_value": 5000.0, "price_per_share": 125.0, "net_debt": -200.0, "pv_ufcfs": [400.0, 450.0], "pv_tv": 4150.0}
    dcf_bull = {"enterprise_value": 6200.0}
    dcf_bear = {"enterprise_value": 3900.0}

    pillars = generate_ic_thesis(engine_output, meta, dcf_base, dcf_bull, dcf_bear, cagr=0.10)
    assert len(pillars) == 4
    joined = " ".join(" ".join(bullets) for _, bullets, _ in pillars)
    assert "Acme Biotech" in joined
    assert "10.0%" in joined
    assert "+25.0%" in joined
    assert "Terminal Value" in joined


def test_coa_agent_maps_nonstandard_private_ledger():
    df = pd.DataFrame(
        {
            "Ledger Head": [
                "Total Receipts",
                "Subcontracting Charges",
                "Liquid Funds",
                "Trade Debtors",
                "Total Assets",
                "Trade Creditors",
                "Bank Borrowings",
                "Total Equity and Liabilities",
            ],
            "FY24A": ["120.0", "45.0", "25.0", "18.0", "100.0", "12.0", "30.0", "100.0"],
            "FY25A": ["150.0", "55.0", "32.0", "22.0", "125.0", "15.0", "28.0", "125.0"],
        }
    )

    mapped, report = CoAMappingAgent().map_unmatched_rows(df, ["FY24A", "FY25A"], set())
    assert report["agent_used"] is True
    assert "revenue" in mapped
    assert mapped["revenue"] == [120.0, 150.0]

    normalized = DataNormalizer().normalize(
        df,
        {
            "standard": "IND_AS",
            "currency": "INR",
            "unit": "Crores",
            "multiplier": 1e7,
            "fy_end_month": 3,
            "columns": ["FY24A", "FY25A"],
        },
    )
    assert normalized.revenue == [120.0, 150.0]
    assert normalized.cogs == [45.0, 55.0]
    assert normalized.cash == [25.0, 32.0]
    assert normalized.coa_mapping_report is not None
    assert normalized.coa_mapping_report["mapped_count"] >= 2
