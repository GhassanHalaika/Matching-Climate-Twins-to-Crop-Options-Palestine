# Climate Twins Crop Recommender

Reusable Streamlit app for matching a target city against European climate twins and recommending crops from accessible FAOSTAT evidence.

## What changed from the old notebook

- No West Bank-wide climate analysis.
- No dependency on local/current crop datasets for the target city.
- Target city is defined by name and coordinates.
- Climate data comes from the NASA POWER API.
- Forecasts are generated for 5, 10, and 20 years using recent climate trends.
- Twin matching compares the forecasted target climate to historical European city climates.
- Crop recommendations come from FAOSTAT production evidence and FAOSTAT price data when available.

## Run

From `C:\Users\Lenovo\Documents\Data`, the easiest option is to double-click:

```text
Run_Climate_Dashboard.bat
```

Then open `http://localhost:8501`.

Manual command:

```powershell
cd C:\Users\Lenovo\Documents\Data\climate_twins_streamlit
..\climate.venv\Scripts\python.exe -m pip install -r requirements.txt
..\climate.venv\Scripts\python.exe -m streamlit run app.py
```

If dependency installation is blocked by network settings, run the same commands after allowing package downloads.

## Optional FAOSTAT cache

The app can use local FAOSTAT bulk zip files. Put these files in `../faostat_cache` or upload/point the app to equivalent FAOSTAT normalized CSV zip files:

- `Prices_E_All_Data_(Normalized).zip`
- `crop_production_E_All_Data_(Normalized).zip`

If production data is missing, the app still shows climate twins and uses a transparent Mediterranean crop fallback list, but FAOSTAT-backed recommendations require the production zip or API access.
