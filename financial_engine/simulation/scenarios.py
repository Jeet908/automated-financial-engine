"""
Scenario Manager: Bull, Base, and Bear case projections and probability weighting.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from financial_engine.core.types import ScenarioType, ModelConfiguration


@dataclass
class ScenarioOutcome:
    scenario_type: ScenarioType
    probability: float
    enterprise_value: float
    equity_value: float
    value_per_share: float
    revenue_cagr: float
    terminal_ebitda: float
    wacc: float


@dataclass
class ScenarioSummary:
    scenarios: List[ScenarioOutcome]
    expected_value_per_share: float
    bull_upside_pct: float
    bear_downside_pct: float


def create_scenario_configurations(base_config: ModelConfiguration) -> Dict[ScenarioType, ModelConfiguration]:
    """Generates parameterized Bull, Base, and Bear configurations."""
    # Base
    base = base_config

    # Bull: +2% revenue growth, -100 bps COGS, +50 bps terminal growth
    bull_dict = base_config.to_dict()
    bull_dict["assumptions"]["revenue_growth"] = [g + 0.02 for g in base_config.assumptions.revenue_growth]
    bull_dict["valuation_inputs"]["terminal_growth_rate"] = base_config.valuation_inputs.terminal_growth_rate + 0.005
    bull = ModelConfiguration.from_dict(bull_dict)

    # Bear: -2% revenue growth, +100 bps COGS, -50 bps terminal growth
    bear_dict = base_config.to_dict()
    bear_dict["assumptions"]["revenue_growth"] = [max(0.01, g - 0.02) for g in base_config.assumptions.revenue_growth]
    bear_dict["valuation_inputs"]["terminal_growth_rate"] = max(0.01, base_config.valuation_inputs.terminal_growth_rate - 0.005)
    bear = ModelConfiguration.from_dict(bear_dict)

    return {
        ScenarioType.BASE: base,
        ScenarioType.BULL: bull,
        ScenarioType.BEAR: bear,
    }
