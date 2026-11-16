"""
Valuation engines: DCF, WACC/CAPM, Comps, and LBO.
"""

from financial_engine.valuation.wacc import (
    WACCResult,
    calculate_wacc,
    hamada_unlever_beta,
    hamada_relever_beta,
)
from financial_engine.valuation.dcf import (
    DCFResult,
    run_dcf_valuation,
)
from financial_engine.valuation.comps import (
    PeerCompany,
    MultiplesSummary,
    CompsResult,
    run_comps_analysis,
)
from financial_engine.valuation.lbo import (
    LBOResult,
    run_lbo_screening,
)
from financial_engine.valuation.advanced_metrics import (
    ROICAnalysis,
    DuPont5WayAnalysis,
    FootballFieldRange,
    compute_roic_and_eva,
    compute_dupont_5way,
    build_football_field,
)

__all__ = [
    "WACCResult",
    "calculate_wacc",
    "hamada_unlever_beta",
    "hamada_relever_beta",
    "DCFResult",
    "run_dcf_valuation",
    "PeerCompany",
    "MultiplesSummary",
    "CompsResult",
    "run_comps_analysis",
    "LBOResult",
    "run_lbo_screening",
    "ROICAnalysis",
    "DuPont5WayAnalysis",
    "FootballFieldRange",
    "compute_roic_and_eva",
    "compute_dupont_5way",
    "build_football_field",
]
