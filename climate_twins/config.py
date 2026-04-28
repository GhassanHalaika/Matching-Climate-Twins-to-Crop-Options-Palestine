from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
DEFAULT_CITY_CATALOG = DATA_DIR / "european_cities.csv"
DEFAULT_FAOSTAT_CACHE = PROJECT_DIR.parent / "faostat_cache"


NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

POWER_PARAMETERS = [
    "PRECTOTCORR",
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
]


@dataclass(frozen=True)
class MetricWeights:
    mean_temp_c: float = 1.15
    max_temp_c: float = 1.0
    min_temp_c: float = 0.85
    annual_precip_mm: float = 1.2
    wet_season_precip_mm: float = 1.15
    rainy_days: float = 0.85
    dry_days: float = 0.85
    max_consecutive_dry_days: float = 0.9
    hot_days_30: float = 1.0
    hot_days_35: float = 1.1
    frost_days: float = 0.9
    gdd_base10: float = 1.0
    aridity_index: float = 1.05


DEFAULT_WEIGHTS = MetricWeights()

