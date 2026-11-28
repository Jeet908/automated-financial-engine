"""
Simulation and sensitivity analysis suite: 2D Sensitivity, Scenarios, and Monte Carlo.
"""

from financial_engine.simulation.sensitivity import (
    SensitivityMatrix,
    build_wacc_growth_sensitivity,
)
from financial_engine.simulation.scenarios import (
    ScenarioOutcome,
    ScenarioSummary,
    create_scenario_configurations,
)
from financial_engine.simulation.monte_carlo import (
    MonteCarloStats,
    run_monte_carlo_simulation,
)

__all__ = [
    "SensitivityMatrix",
    "build_wacc_growth_sensitivity",
    "ScenarioOutcome",
    "ScenarioSummary",
    "create_scenario_configurations",
    "MonteCarloStats",
    "run_monte_carlo_simulation",
]
