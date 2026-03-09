# Sub-Plan 04: Geographic Overdose Forecasting

## Priority: After Sub-Plan 01 (needs caching)
## Can parallelize with: Sub-Plan 03, 05, 06, 07

---

## Goal
Train Facebook Prophet models on CDC mortality time-series data to forecast state-level overdose rates 12-24 months ahead, with 80%/95% prediction intervals. Validate via walk-forward backtesting. Integrate forecasts into the Geographic Intelligence page.

## Pre-Requisites
- Sub-Plan 01 (Performance Caching) must be COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/config.py` — CDC API endpoints, data paths
2. `opioid_track/core/demographics_builder.py` — existing CDC data loading
3. `opioid_track/data/opioid_mortality.json` — mortality data structure (81K+ records)
4. `opioid_track/data/opioid_geographic_profiles.json` — county-level profiles (3,148 entries)
5. `opioid_track/dashboard/pages/geography.py` — existing geographic page to extend
6. `opioid_track/ingestion/cdc_mortality_fetcher.py` — how mortality data is fetched

---

## Agent Assignment

### Agent A (Worktree: `forecaster`) — Create Forecasting Engine

**Create file: `opioid_track/ml/__init__.py`** (if not exists)

**Create file: `opioid_track/ml/geographic_forecaster.py`**

```python
"""
Geographic Overdose Forecasting using Facebook Prophet.
Trains per-state models on CDC mortality time-series.
"""
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class ForecastResult:
    """Forecast output for a single state."""
    state: str
    historical: pd.DataFrame    # columns: ds, y (date, actual rate)
    forecast: pd.DataFrame      # columns: ds, yhat, yhat_lower_80, yhat_upper_80, yhat_lower_95, yhat_upper_95
    mape: Optional[float]       # from validation (None if not validated)
    trend: str                  # "accelerating", "stable", "declining"
    trend_slope: float          # rate of change in deaths per 100k per year


class GeographicForecaster:
    """
    Per-state overdose mortality forecasting.

    Pipeline:
    1. Load CDC mortality data (deaths per 100k by state by month/year)
    2. Reshape into Prophet-compatible format (ds, y columns)
    3. Walk-forward validation: train 2015-2020, predict 2021-2022, compute MAPE
    4. Full training: retrain on all data
    5. Forecast: predict 12 and 24 months ahead with uncertainty intervals
    6. Spatial smoothing: average with neighboring states
    """

    # State adjacency map for spatial smoothing
    STATE_NEIGHBORS: Dict[str, List[str]] = {
        # Populate with standard US state adjacency
        # e.g., "OH": ["PA", "WV", "KY", "IN", "MI"],
        ...
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """Load mortality data and prepare time-series."""
        ...

    def _prepare_time_series(self) -> Dict[str, pd.DataFrame]:
        """
        Reshape mortality data into per-state DataFrames.
        Each DataFrame has columns: ds (datetime), y (deaths per 100k).

        Data source: opioid_mortality.json
        Expected structure: list of records with state, year, month/quarter, death_rate fields.

        If data is only annual (not monthly), use annual frequency.
        Fill gaps with interpolation if minor; flag states with >30% missing data.
        """
        ...

    def validate(self, state: str) -> Optional[float]:
        """
        Walk-forward validation for a single state.

        1. Train Prophet on 2015-2020 data
        2. Predict 2021-2022
        3. Compute MAPE = mean(|actual - predicted| / actual) × 100
        4. Compute prediction interval coverage = % of actuals within 95% bands

        Returns MAPE value. Also stores coverage internally.
        """
        ...

    def validate_all(self) -> pd.DataFrame:
        """
        Run validation for all states.
        Returns DataFrame: state, mape, coverage_80, coverage_95, n_observations
        """
        ...

    def train_and_forecast(self, state: str, horizon_months: int = 24) -> Optional[ForecastResult]:
        """
        Train Prophet on full historical data and forecast.

        Prophet configuration:
        - yearly_seasonality=True (opioid deaths have seasonal patterns)
        - changepoint_prior_scale=0.1 (moderate flexibility for trend changes)
        - interval_width=[0.80, 0.95] for two-tier uncertainty
        - Add prescribing_rate as external regressor if available

        Returns ForecastResult with historical + forecast DataFrames.
        """
        ...

    def forecast_all(self, horizon_months: int = 24) -> Dict[str, ForecastResult]:
        """Train and forecast for all states. Cache results."""
        ...

    def _apply_spatial_smoothing(self, forecasts: Dict[str, ForecastResult]) -> Dict[str, ForecastResult]:
        """
        Post-process forecasts with spatial smoothing.
        For each state: smoothed_forecast = 0.7 * own_forecast + 0.3 * mean(neighbor_forecasts)
        This captures geographic spillover effects.
        """
        ...

    def _classify_trend(self, forecast: pd.DataFrame) -> Tuple[str, float]:
        """
        Classify trend as accelerating/stable/declining.
        Fit linear regression to last 12 months of forecast.
        slope > 0.5 per year = "accelerating"
        slope < -0.5 per year = "declining"
        otherwise = "stable"

        Returns (trend_label, slope_value).
        """
        ...

    def get_emerging_hotspots(self, top_n: int = 10) -> List[Dict]:
        """
        States with the most accelerating trends.
        Returns list of {state, trend_slope, current_rate, forecast_rate_12m, forecast_rate_24m}
        """
        ...

    def get_forecast_summary(self) -> Dict:
        """
        National-level summary:
        - Average MAPE across states
        - Number of states with accelerating trends
        - Top 5 highest forecast rates
        - Top 5 most improved (declining trends)
        """
        ...
```

**Create file: `opioid_track/ml/model_validation.py`**

```python
"""Model validation utilities for geographic forecaster."""

def compute_mape(actual: pd.Series, predicted: pd.Series) -> float:
    """Mean Absolute Percentage Error. Handles zeros by excluding them."""
    ...

def compute_interval_coverage(actual: pd.Series, lower: pd.Series, upper: pd.Series) -> float:
    """Fraction of actuals that fall within prediction interval."""
    ...

def compute_rmse(actual: pd.Series, predicted: pd.Series) -> float:
    """Root Mean Squared Error."""
    ...

def validation_summary(results: pd.DataFrame) -> Dict:
    """
    Summary statistics from validation_all() output.
    Returns: mean_mape, median_mape, mean_coverage_95, n_states_mape_under_25
    """
    ...
```

**Create file: `opioid_track/tests/test_forecaster.py`**

```python
"""
Tests for Geographic Overdose Forecaster.
pytest opioid_track/tests/test_forecaster.py -v
"""
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "opioid_mortality.json").exists(),
    reason="Mortality data not built yet"
)

from opioid_track.ml.geographic_forecaster import GeographicForecaster

class TestGeographicForecaster:
    def setup_method(self):
        self.forecaster = GeographicForecaster()

    def test_time_series_preparation(self):
        ts = self.forecaster._prepare_time_series()
        assert len(ts) > 0
        # Each state should have ds and y columns
        for state, df in list(ts.items())[:3]:
            assert "ds" in df.columns and "y" in df.columns
            assert len(df) > 0

    def test_single_state_forecast(self):
        result = self.forecaster.train_and_forecast("OH", horizon_months=12)
        if result is not None:
            assert result.state == "OH"
            assert len(result.forecast) == 12  # 12 months ahead
            assert "yhat" in result.forecast.columns
            assert result.trend in ["accelerating", "stable", "declining"]

    def test_forecast_values_reasonable(self):
        result = self.forecaster.train_and_forecast("OH", horizon_months=12)
        if result is not None:
            # Death rates should be positive and within reasonable range (0-200 per 100k)
            assert (result.forecast["yhat"] >= 0).all()
            assert (result.forecast["yhat"] < 200).all()

    def test_prediction_intervals_ordered(self):
        result = self.forecaster.train_and_forecast("OH", horizon_months=12)
        if result is not None:
            fc = result.forecast
            assert (fc["yhat_lower_95"] <= fc["yhat_lower_80"]).all()
            assert (fc["yhat_lower_80"] <= fc["yhat"]).all()
            assert (fc["yhat"] <= fc["yhat_upper_80"]).all()
            assert (fc["yhat_upper_80"] <= fc["yhat_upper_95"]).all()

    def test_emerging_hotspots(self):
        # This may be slow — run only if all states are forecast
        hotspots = self.forecaster.get_emerging_hotspots(top_n=5)
        assert len(hotspots) <= 5
        if len(hotspots) > 0:
            assert "state" in hotspots[0]
            assert "trend_slope" in hotspots[0]
```

**Done criteria:** Tests pass for at least one state. Forecasts have valid intervals.

---

### Agent B (Sequential after A) — Dashboard Integration

**Modify: `opioid_track/dashboard/pages/geography.py`**

Add a new "Predictive" tab (using `st.tabs`) alongside existing content:

1. **Forecast Chart:**
   - State selector dropdown
   - Plotly line chart with:
     - Historical data (solid line)
     - Forecast (dashed line)
     - 80% prediction interval (dark shaded band)
     - 95% prediction interval (light shaded band)
   - X-axis: date, Y-axis: deaths per 100k

2. **Emerging Hotspots Map:**
   - Plotly choropleth or DeckGL map (if Sub-Plan 06 is done)
   - Color = trend slope (red = accelerating, yellow = stable, green = declining)
   - Size/height = forecast rate

3. **Model Performance Panel:**
   - Summary metrics: avg MAPE, states with MAPE < 25%, coverage rate
   - Per-state validation table (sortable by MAPE)
   - Interpretation note: "Lower MAPE = more reliable forecast"

4. **National Summary:**
   - Card with: "X states trending up, Y stable, Z improving"
   - Top 5 highest forecast rates
   - Top 5 most improved

**Modify: `opioid_track/config.py`**
Add:
```python
# === ML Configuration ===
FORECAST_HORIZON_MONTHS = 24
FORECAST_CONFIDENCE_LEVELS = [0.80, 0.95]
FORECAST_VALIDATION_SPLIT_YEAR = 2020
PROPHET_CHANGEPOINT_PRIOR = 0.1
```

**Done criteria:** Predictive tab renders with forecast chart, hotspot map, and performance metrics.

---

## Execution Order
1. **Agent A** creates forecaster + validation + tests (worktree)
2. **Agent B** integrates into geography page (sequential)
3. Run tests: `pytest opioid_track/tests/test_forecaster.py -v`
4. Commit: `git commit -m "feat(opioid): add Prophet-based geographic overdose forecasting with validation"`

## Checkpoint Protocol
- **Mid-Agent A:** Note which methods are implemented and which are stubs
- **Mid-Agent B:** Note which dashboard sections are done (chart? hotspots? performance?)

## Final Verification
```bash
pytest opioid_track/tests/test_forecaster.py -v
# Visual: Geography page → Predictive tab shows forecast chart
```
Update `00_STATUS.md` to "COMPLETED".
