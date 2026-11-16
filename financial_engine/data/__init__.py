"""
Pre-packaged corporate financial modeling datasets and benchmarks.
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent
KAVERI_FOODS_PATH = str(DATA_DIR / "kaveri_foods.json")
SAAS_GROWTH_PATH = str(DATA_DIR / "saas_growth.json")
INDUSTRIAL_CORP_PATH = str(DATA_DIR / "industrial_corp.json")

__all__ = [
    "DATA_DIR",
    "KAVERI_FOODS_PATH",
    "SAAS_GROWTH_PATH",
    "INDUSTRIAL_CORP_PATH",
]
