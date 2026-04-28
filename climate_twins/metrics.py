from __future__ import annotations

import numpy as np
import pandas as pd


WET_MONTHS = {10, 11, 12, 1, 2, 3, 4, 5}


def _max_consecutive_true(values: pd.Series) -> int:
    best = run = 0
    for value in values.fillna(False).astype(bool):
        run = run + 1 if value else 0
        best = max(best, run)
    return int(best)


def annual_agro_metrics(daily: pd.DataFrame) -> pd.DataFrame:
    """Calculate annual agriculture-relevant climate indicators."""
    df = daily.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["rainy_day"] = df["precip_mm"] >= 1.0
    df["dry_day"] = df["precip_mm"] < 1.0
    df["hot_day_30"] = df["max_temp_c"] >= 30.0
    df["hot_day_35"] = df["max_temp_c"] >= 35.0
    df["frost_day"] = df["min_temp_c"] < 0.0
    df["gdd_base10_daily"] = (df["mean_temp_c"] - 10.0).clip(lower=0)

    rows = []
    for year, group in df.groupby("year", sort=True):
        precip = group["precip_mm"]
        mean_temp = group["mean_temp_c"]
        rows.append(
            {
                "year": int(year),
                "mean_temp_c": mean_temp.mean(),
                "max_temp_c": group["max_temp_c"].mean(),
                "min_temp_c": group["min_temp_c"].mean(),
                "annual_precip_mm": precip.sum(),
                "wet_season_precip_mm": group.loc[group["month"].isin(WET_MONTHS), "precip_mm"].sum(),
                "rainy_days": group["rainy_day"].sum(),
                "dry_days": group["dry_day"].sum(),
                "max_consecutive_dry_days": _max_consecutive_true(group["dry_day"]),
                "hot_days_30": group["hot_day_30"].sum(),
                "hot_days_35": group["hot_day_35"].sum(),
                "frost_days": group["frost_day"].sum(),
                "gdd_base10": group["gdd_base10_daily"].sum(),
                "aridity_index": precip.sum() / max(1.0, mean_temp.mean() + 10.0),
            }
        )
    return pd.DataFrame(rows)


def metric_columns(metrics: pd.DataFrame) -> list[str]:
    return [col for col in metrics.columns if col != "year" and pd.api.types.is_numeric_dtype(metrics[col])]


def recent_fingerprint(metrics: pd.DataFrame, years: int = 10) -> pd.Series:
    recent = metrics.sort_values("year").tail(years)
    return recent[metric_columns(recent)].mean(numeric_only=True)


def forecast_fingerprints(metrics: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """Project metric fingerprints using a linear trend over the available annual series."""
    clean = metrics.dropna(subset=["year"]).sort_values("year")
    base = recent_fingerprint(clean, years=min(10, len(clean)))
    rows = []
    x = clean["year"].to_numpy(dtype=float)
    for horizon in horizons:
        projected = base.copy()
        for col in metric_columns(clean):
            y = clean[col].to_numpy(dtype=float)
            valid = np.isfinite(x) & np.isfinite(y)
            slope = np.polyfit(x[valid], y[valid], 1)[0] if valid.sum() >= 5 else 0.0
            projected[col] = base[col] + slope * horizon
        projected["horizon_years"] = horizon
        rows.append(projected)
    return pd.DataFrame(rows)

