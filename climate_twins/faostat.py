from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


PRICE_ZIP = "Prices_E_All_Data_(Normalized).zip"
PRODUCTION_ZIP = "crop_production_E_All_Data_(Normalized).zip"

FALLBACK_CROPS = pd.DataFrame(
    [
        {"crop": "Olives", "evidence": "fallback crop list", "production_value": None},
        {"crop": "Grapes", "evidence": "fallback crop list", "production_value": None},
        {"crop": "Wheat", "evidence": "fallback crop list", "production_value": None},
        {"crop": "Barley", "evidence": "fallback crop list", "production_value": None},
        {"crop": "Tomatoes", "evidence": "fallback crop list", "production_value": None},
        {"crop": "Almonds, in shell", "evidence": "fallback crop list", "production_value": None},
    ]
)


def _csv_name_in_zip(path: Path) -> str:
    with ZipFile(path) as zf:
        csvs = [name for name in zf.namelist() if name.lower().endswith(".csv") and "all_data" in name.lower()]
        if not csvs:
            csvs = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not csvs:
            raise FileNotFoundError(f"No CSV found inside {path}")
        return csvs[0]


def _read_zip_csv(path: Path, usecols: list[str] | None = None) -> pd.DataFrame:
    inner = _csv_name_in_zip(path)
    with ZipFile(path) as zf:
        with zf.open(inner) as handle:
            return pd.read_csv(handle, usecols=usecols, low_memory=False)


def load_price_reference(cache_dir: Path, recent_years: int = 3) -> pd.DataFrame:
    path = cache_dir / PRICE_ZIP
    if not path.exists():
        return pd.DataFrame(columns=["crop", "price_usd_per_tonne", "price_years"])

    cols = ["Area", "Item", "Element", "Year", "Unit", "Value"]
    prices = _read_zip_csv(path, usecols=lambda c: c in cols)
    prices = prices[prices["Element"].astype(str).str.contains("Producer Price", case=False, na=False)]
    prices = prices[prices["Unit"].astype(str).str.contains("USD", case=False, na=False)]
    if prices.empty:
        return pd.DataFrame(columns=["crop", "price_usd_per_tonne", "price_years"])

    max_year = int(prices["Year"].max())
    prices = prices[prices["Year"] >= max_year - recent_years + 1]
    summary = (
        prices.groupby("Item", as_index=False)
        .agg(price_usd_per_tonne=("Value", "mean"), price_years=("Year", lambda s: f"{int(s.min())}-{int(s.max())}"))
        .rename(columns={"Item": "crop"})
    )
    return summary


def load_successful_crops_for_countries(cache_dir: Path, countries: list[str], top_n: int = 20) -> pd.DataFrame:
    path = cache_dir / PRODUCTION_ZIP
    if not path.exists():
        fallback = FALLBACK_CROPS.copy()
        fallback["country"] = ", ".join(sorted(set(countries)))
        return fallback

    cols = ["Area", "Item", "Element", "Year", "Unit", "Value"]
    crops = _read_zip_csv(path, usecols=lambda c: c in cols)
    crops = crops[crops["Area"].isin(countries)]
    crops = crops[crops["Element"].astype(str).str.contains("Production|Area harvested", case=False, na=False)]
    if crops.empty:
        fallback = FALLBACK_CROPS.copy()
        fallback["country"] = ", ".join(sorted(set(countries)))
        return fallback

    recent_year = int(crops["Year"].max())
    recent = crops[crops["Year"] >= recent_year - 4]
    summary = (
        recent.groupby(["Area", "Item"], as_index=False)
        .agg(production_value=("Value", "mean"), evidence=("Element", lambda s: ", ".join(sorted(set(map(str, s))))))
        .sort_values("production_value", ascending=False)
        .head(top_n)
        .rename(columns={"Area": "country", "Item": "crop"})
    )
    return summary


def crop_recommendations(cache_dir: Path, twin_countries: list[str], top_n: int = 20) -> pd.DataFrame:
    crops = load_successful_crops_for_countries(cache_dir, twin_countries, top_n=top_n)
    prices = load_price_reference(cache_dir)
    out = crops.merge(prices, on="crop", how="left")
    return out.sort_values(["price_usd_per_tonne", "production_value"], ascending=[False, False], na_position="last")
