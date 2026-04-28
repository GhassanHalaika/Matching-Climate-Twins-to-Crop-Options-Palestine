from __future__ import annotations

from datetime import date
from typing import Iterable

import pandas as pd
import requests

from .config import NASA_POWER_DAILY_URL, POWER_PARAMETERS


def _format_date(value: date | str) -> str:
    if isinstance(value, date):
        return value.strftime("%Y%m%d")
    return str(value).replace("-", "")


def fetch_daily_power(
    latitude: float,
    longitude: float,
    start: date | str,
    end: date | str,
    parameters: Iterable[str] = POWER_PARAMETERS,
    timeout: int = 90,
) -> pd.DataFrame:
    """Fetch daily NASA POWER agroclimatology data for one point."""
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": _format_date(start),
        "end": _format_date(end),
        "format": "JSON",
    }
    response = requests.get(NASA_POWER_DAILY_URL, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    raw = payload.get("properties", {}).get("parameter", {})
    if not raw:
        raise ValueError("NASA POWER returned no parameter data for this point/date range.")

    df = pd.DataFrame(raw)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.rename(
        columns={
            "PRECTOTCORR": "precip_mm",
            "T2M": "mean_temp_c",
            "T2M_MAX": "max_temp_c",
            "T2M_MIN": "min_temp_c",
        }
    )
    df = df.reset_index(names="date")
    for col in ["precip_mm", "mean_temp_c", "max_temp_c", "min_temp_c"]:
        if col in df:
            df[col] = pd.to_numeric(df[col], errors="coerce").replace(-999, pd.NA)
    return df

