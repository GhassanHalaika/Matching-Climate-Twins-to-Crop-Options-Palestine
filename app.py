from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from climate_twins.config import DEFAULT_CITY_CATALOG, DEFAULT_FAOSTAT_CACHE
from climate_twins.faostat import crop_recommendations
from climate_twins.matcher import weighted_twin_distance
from climate_twins.metrics import annual_agro_metrics, forecast_fingerprints, recent_fingerprint
from climate_twins.nasa_power import fetch_daily_power


st.set_page_config(page_title="Climate Twin Crop Recommender", layout="wide")


@st.cache_data(show_spinner=False)
def load_city_catalog(uploaded_file) -> pd.DataFrame:
    if uploaded_file is not None:
        return pd.read_csv(uploaded_file)
    return pd.read_csv(DEFAULT_CITY_CATALOG)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def climate_metrics_for_point(lat: float, lon: float, start_year: int, end_year: int) -> pd.DataFrame:
    daily = fetch_daily_power(lat, lon, f"{start_year}0101", f"{end_year}1231")
    return annual_agro_metrics(daily)


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def build_candidate_fingerprints(cities: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    rows = []
    for city in cities.itertuples(index=False):
        metrics = climate_metrics_for_point(float(city.latitude), float(city.longitude), start_year, end_year)
        fp = recent_fingerprint(metrics, years=min(10, len(metrics))).to_dict()
        fp.update(
            {
                "city": city.city,
                "country": city.country,
                "latitude": city.latitude,
                "longitude": city.longitude,
                "region_group": getattr(city, "region_group", "Europe"),
            }
        )
        rows.append(fp)
    return pd.DataFrame(rows)


def validate_city_catalog(cities: pd.DataFrame) -> pd.DataFrame:
    required = {"city", "country", "latitude", "longitude"}
    missing = required - set(cities.columns)
    if missing:
        raise ValueError(f"City catalogue is missing columns: {', '.join(sorted(missing))}")
    cities = cities.copy()
    cities["latitude"] = pd.to_numeric(cities["latitude"], errors="coerce")
    cities["longitude"] = pd.to_numeric(cities["longitude"], errors="coerce")
    return cities.dropna(subset=["latitude", "longitude"])


st.title("Climate Twin Crop Recommender")

with st.sidebar:
    st.header("Target city")
    target_name = st.text_input("Name", value="Jenin")
    latitude = st.number_input("Latitude", value=32.46, min_value=-90.0, max_value=90.0, step=0.01)
    longitude = st.number_input("Longitude", value=35.30, min_value=-180.0, max_value=180.0, step=0.01)

    st.header("Climate windows")
    current_year = date.today().year
    start_year = st.number_input("Historical start year", value=1990, min_value=1981, max_value=current_year - 2)
    end_year = st.number_input("Historical end year", value=current_year - 1, min_value=int(start_year) + 5, max_value=current_year)
    candidate_start_year = st.number_input("European twin climate start", value=2014, min_value=1981, max_value=current_year - 2)
    candidate_end_year = st.number_input("European twin climate end", value=current_year - 1, min_value=int(candidate_start_year) + 3, max_value=current_year)

    st.header("Twin search")
    horizons = st.multiselect("Forecast horizons", [5, 10, 20], default=[5, 10, 20])
    top_n = st.slider("Twin cities to show", min_value=3, max_value=20, value=8)
    city_upload = st.file_uploader("Optional European city CSV", type=["csv"])

    st.header("FAOSTAT")
    faostat_cache = Path(st.text_input("FAOSTAT cache folder", value=str(DEFAULT_FAOSTAT_CACHE)))
    crop_top_n = st.slider("Crop recommendation rows", min_value=5, max_value=50, value=20)

run = st.button("Run climate twin analysis", type="primary")

if not run:
    st.info("Set a target city and run the analysis. Climate calls are cached after the first run.")
    st.stop()

try:
    city_catalog = validate_city_catalog(load_city_catalog(city_upload))
except Exception as exc:
    st.error(str(exc))
    st.stop()

with st.status("Fetching NASA POWER climate data and calculating agroclimate metrics...", expanded=True) as status:
    target_metrics = climate_metrics_for_point(float(latitude), float(longitude), int(start_year), int(end_year))
    target_forecasts = forecast_fingerprints(target_metrics, sorted(horizons))
    candidate_fps = build_candidate_fingerprints(city_catalog, int(candidate_start_year), int(candidate_end_year))
    status.update(label="Climate data ready.", state="complete")

target_tab, twin_tab, crop_tab, data_tab = st.tabs(["Forecast", "Twin cities", "Crop recommendations", "Data"])

with target_tab:
    st.subheader(f"{target_name} climate forecast fingerprints")
    metric = st.selectbox(
        "Metric",
        [
            "mean_temp_c",
            "annual_precip_mm",
            "wet_season_precip_mm",
            "hot_days_30",
            "hot_days_35",
            "frost_days",
            "gdd_base10",
            "max_consecutive_dry_days",
            "aridity_index",
        ],
    )
    annual_fig = px.line(target_metrics, x="year", y=metric, markers=True, title=f"Historical trend: {metric}")
    st.plotly_chart(annual_fig, use_container_width=True)
    st.dataframe(target_forecasts.set_index("horizon_years").round(2), use_container_width=True)

ranked_by_horizon: dict[int, pd.DataFrame] = {}
for row in target_forecasts.itertuples(index=False):
    horizon = int(row.horizon_years)
    ranked_by_horizon[horizon] = weighted_twin_distance(pd.Series(row._asdict()), candidate_fps).head(top_n)

with twin_tab:
    selected_horizon = st.selectbox("Forecast horizon", sorted(ranked_by_horizon), index=0)
    twins = ranked_by_horizon[selected_horizon]
    st.subheader(f"European climate twins for {target_name} in {selected_horizon} years")
    st.dataframe(
        twins[
            [
                "city",
                "country",
                "similarity_score",
                "climate_distance",
                "mean_temp_c",
                "annual_precip_mm",
                "hot_days_30",
                "hot_days_35",
                "frost_days",
                "gdd_base10",
            ]
        ].round(2),
        use_container_width=True,
    )
    map_df = twins[["city", "country", "latitude", "longitude", "similarity_score"]].copy()
    st.map(map_df.rename(columns={"latitude": "lat", "longitude": "lon"}), size="similarity_score")

    compare_cols = ["mean_temp_c", "annual_precip_mm", "wet_season_precip_mm", "hot_days_30", "hot_days_35", "frost_days"]
    compare = twins.head(5).melt(id_vars=["city", "country"], value_vars=compare_cols, var_name="metric", value_name="value")
    st.plotly_chart(px.bar(compare, x="metric", y="value", color="city", barmode="group"), use_container_width=True)

with crop_tab:
    selected_horizon = st.selectbox("Crop horizon", sorted(ranked_by_horizon), index=0, key="crop_horizon")
    twin_countries = ranked_by_horizon[selected_horizon]["country"].dropna().unique().tolist()
    recs = crop_recommendations(faostat_cache, twin_countries, top_n=crop_top_n)
    st.subheader("FAOSTAT-backed crop recommendation table")
    if recs["evidence"].astype(str).str.contains("fallback", case=False, na=False).any():
        st.warning("FAOSTAT crop production cache was not found. Showing fallback crops; add the production zip for database-backed crop evidence.")
    if "price_usd_per_tonne" in recs and recs["price_usd_per_tonne"].notna().any():
        price_fig = px.bar(
            recs.dropna(subset=["price_usd_per_tonne"]).head(15),
            x="crop",
            y="price_usd_per_tonne",
            color="country" if "country" in recs.columns else None,
        )
        st.plotly_chart(price_fig, use_container_width=True)
    st.dataframe(recs.round(2), use_container_width=True)

with data_tab:
    st.subheader("European city catalogue")
    st.dataframe(city_catalog, use_container_width=True)
    st.subheader("Candidate fingerprints")
    st.dataframe(candidate_fps.round(2), use_container_width=True)
    st.download_button(
        "Download twin rankings CSV",
        pd.concat(
            [df.assign(horizon_years=horizon) for horizon, df in ranked_by_horizon.items()],
            ignore_index=True,
        ).to_csv(index=False),
        file_name=f"{target_name.lower().replace(' ', '_')}_climate_twins.csv",
        mime="text/csv",
    )
