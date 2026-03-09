# Sub-Plan 06: DeckGL 3D Heat Globe

## Priority: Early (no dependencies)
## Can parallelize with: Sub-Plan 01, 02, 07

---

## Goal
Add a 3D extruded column map to the Geographic Intelligence page using `pydeck`. Columns rise from each state proportional to the selected metric (mortality rate, prescribing rate, etc.). High visual wow-factor for investor demos.

## Pre-Requisites
- Read `00_STATUS.md` first
- No hard dependencies, but if Sub-Plan 02 (theme) is done, use theme-aware colors

## Context Files to Read First
1. `opioid_track/dashboard/pages/geography.py` — existing geographic page (has Plotly choropleth)
2. `opioid_track/data/opioid_geographic_profiles.json` — geographic data structure
3. `opioid_track/dashboard/opioid_app.py` — app styling for consistency

---

## Agent Assignment

### Agent A (Worktree: `deckgl-globe`) — Create DeckGL Component

**Create file: `opioid_track/dashboard/components/deckgl_map.py`**

```python
"""
3D Geographic visualization using DeckGL via pydeck.
Renders extruded columns on a dark map showing opioid crisis metrics by location.
"""
import pydeck as pdk
import pandas as pd
import streamlit as st
from typing import Optional, Tuple

# Color scales matching the app's teal→amber→red palette
TEAL = [0, 229, 200]      # Low risk
AMBER = [245, 158, 11]    # Medium risk
RED = [239, 68, 68]       # High risk

# US center coordinates
US_CENTER = {"latitude": 39.8283, "longitude": -98.5795}
DEFAULT_ZOOM = 3.5


def _interpolate_color(value: float, min_val: float, max_val: float) -> list:
    """
    Interpolate between teal (low) → amber (mid) → red (high).
    value: the metric value
    min_val, max_val: range for normalization

    Returns [R, G, B, A] list.
    """
    if max_val == min_val:
        return TEAL + [200]

    normalized = (value - min_val) / (max_val - min_val)
    normalized = max(0.0, min(1.0, normalized))

    if normalized < 0.5:
        # Teal to Amber
        t = normalized * 2
        r = int(TEAL[0] + t * (AMBER[0] - TEAL[0]))
        g = int(TEAL[1] + t * (AMBER[1] - TEAL[1]))
        b = int(TEAL[2] + t * (AMBER[2] - TEAL[2]))
    else:
        # Amber to Red
        t = (normalized - 0.5) * 2
        r = int(AMBER[0] + t * (RED[0] - AMBER[0]))
        g = int(AMBER[1] + t * (RED[1] - AMBER[1]))
        b = int(AMBER[2] + t * (RED[2] - AMBER[2]))

    return [r, g, b, 200]


def render_3d_geographic_map(
    df: pd.DataFrame,
    metric_col: str,
    lat_col: str = "latitude",
    lon_col: str = "longitude",
    name_col: str = "state",
    height_multiplier: float = 5000.0,
    radius: int = 25000,
    auto_rotate: bool = True,
) -> None:
    """
    Render a 3D extruded column map using DeckGL.

    Parameters:
    - df: DataFrame with location data and metric values
    - metric_col: Column name for the metric to visualize (height + color)
    - lat_col, lon_col: Column names for coordinates
    - name_col: Column name for location label (shown in tooltip)
    - height_multiplier: Scale factor for column heights
    - radius: Column radius in meters
    - auto_rotate: Enable auto-rotation animation

    The map uses:
    - Carto Dark Matter basemap (no API key needed)
    - ColumnLayer for extruded 3D pillars
    - Color gradient: teal (low) → amber (mid) → red (high)
    - Interactive pitch/yaw/zoom controls
    - Tooltip on hover showing location name + metric value
    """
    if df.empty or metric_col not in df.columns:
        st.warning("No geographic data available for 3D visualization.")
        return

    # Prepare data
    plot_df = df[[lat_col, lon_col, metric_col, name_col]].dropna().copy()
    min_val = plot_df[metric_col].min()
    max_val = plot_df[metric_col].max()

    # Add color and height columns
    plot_df["color"] = plot_df[metric_col].apply(
        lambda v: _interpolate_color(v, min_val, max_val)
    )
    plot_df["elevation"] = plot_df[metric_col].apply(
        lambda v: ((v - min_val) / (max_val - min_val) if max_val > min_val else 0.5) * height_multiplier
    )

    # Create the column layer
    column_layer = pdk.Layer(
        "ColumnLayer",
        data=plot_df,
        get_position=f"[{lon_col}, {lat_col}]",
        get_elevation="elevation",
        elevation_scale=1,
        radius=radius,
        get_fill_color="color",
        pickable=True,
        auto_highlight=True,
        coverage=0.8,
    )

    # View state
    view_state = pdk.ViewState(
        latitude=US_CENTER["latitude"],
        longitude=US_CENTER["longitude"],
        zoom=DEFAULT_ZOOM,
        pitch=45,       # Tilted view for 3D effect
        bearing=0,
    )

    # Tooltip
    tooltip = {
        "html": f"<b>{{{name_col}}}</b><br/>{metric_col}: {{{metric_col}:.2f}}",
        "style": {
            "backgroundColor": "#141b2d",
            "color": "#e8edf5",
            "border": "1px solid #00e5c8",
            "borderRadius": "4px",
            "padding": "8px",
            "fontFamily": "JetBrains Mono, monospace",
        },
    }

    # Render
    deck = pdk.Deck(
        layers=[column_layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    )

    st.pydeck_chart(deck, use_container_width=True)


def get_state_centroids() -> pd.DataFrame:
    """
    Returns a DataFrame with US state centroids (latitude, longitude, state abbreviation).
    Hardcoded for the 50 states + DC.

    Columns: state, latitude, longitude
    """
    centroids = {
        "AL": (32.806671, -86.791130),
        "AK": (61.370716, -152.404419),
        "AZ": (33.729759, -111.431221),
        "AR": (34.969704, -92.373123),
        "CA": (36.116203, -119.681564),
        "CO": (39.059811, -105.311104),
        "CT": (41.597782, -72.755371),
        "DE": (39.318523, -75.507141),
        "FL": (27.766279, -81.686783),
        "GA": (33.040619, -83.643074),
        "HI": (21.094318, -157.498337),
        "ID": (44.240459, -114.478828),
        "IL": (40.349457, -88.986137),
        "IN": (39.849426, -86.258278),
        "IA": (42.011539, -93.210526),
        "KS": (38.526600, -96.726486),
        "KY": (37.668140, -84.670067),
        "LA": (31.169546, -91.867805),
        "ME": (44.693947, -69.381927),
        "MD": (39.063946, -76.802101),
        "MA": (42.230171, -71.530106),
        "MI": (43.326618, -84.536095),
        "MN": (45.694454, -93.900192),
        "MS": (32.741646, -89.678696),
        "MO": (38.456085, -92.288368),
        "MT": (46.921925, -110.454353),
        "NE": (41.125370, -98.268082),
        "NV": (38.313515, -117.055374),
        "NH": (43.452492, -71.563896),
        "NJ": (40.298904, -74.521011),
        "NM": (34.840515, -106.248482),
        "NY": (42.165726, -74.948051),
        "NC": (35.630066, -79.806419),
        "ND": (47.528912, -99.784012),
        "OH": (40.388783, -82.764915),
        "OK": (35.565342, -96.928917),
        "OR": (44.572021, -122.070938),
        "PA": (40.590752, -77.209755),
        "RI": (41.680893, -71.511780),
        "SC": (33.856892, -80.945007),
        "SD": (44.299782, -99.438828),
        "TN": (35.747845, -86.692345),
        "TX": (31.054487, -97.563461),
        "UT": (40.150032, -111.862434),
        "VT": (44.045876, -72.710686),
        "VA": (37.769337, -78.169968),
        "WA": (47.400902, -121.490494),
        "WV": (38.491226, -80.954453),
        "WI": (44.268543, -89.616508),
        "WY": (42.755966, -107.302490),
        "DC": (38.897438, -77.026817),
    }
    rows = [{"state": k, "latitude": v[0], "longitude": v[1]} for k, v in centroids.items()]
    return pd.DataFrame(rows)
```

**Done criteria:** Module imports without error. `render_3d_geographic_map()` callable with a DataFrame.

---

### Agent B (Sequential after A) — Integrate into Geography Page

**Modify: `opioid_track/dashboard/pages/geography.py`**

1. Add import: `from opioid_track.dashboard.components.deckgl_map import render_3d_geographic_map, get_state_centroids`
2. Add a **2D/3D toggle** above the existing map:
   ```python
   view_mode = st.radio("Map View", ["2D Choropleth", "3D Column Map"], horizontal=True)
   ```
3. If "3D Column Map" selected:
   - Merge the existing state-level data with `get_state_centroids()` on state abbreviation
   - Call `render_3d_geographic_map(merged_df, metric_col=selected_metric, ...)`
4. If "2D Choropleth" selected:
   - Render existing Plotly choropleth (current behavior, no changes)

**Add to requirements:** `pydeck>=0.8.0`

**Done criteria:** Geography page has 2D/3D toggle. 3D mode shows extruded columns. 2D mode works as before.

---

## Execution Order
1. **Agent A** creates DeckGL component (worktree)
2. **Agent B** integrates into geography page (sequential)
3. Visual verification: 3D columns render with correct colors/heights
4. Commit: `git commit -m "feat(opioid): add DeckGL 3D heat globe to Geographic Intelligence"`

## Checkpoint Protocol
- **Mid-Agent A:** Note if color interpolation and layer creation are done
- **Mid-Agent B:** Note if toggle is added and data merge is working

## Final Verification
```bash
# Visual: Geography page → toggle to 3D → columns render on dark map
# Hover tooltip shows state name + metric value
# Columns are teal (low) → red (high)
```
Update `00_STATUS.md` to "COMPLETED".
