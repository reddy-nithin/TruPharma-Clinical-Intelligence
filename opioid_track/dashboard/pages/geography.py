"""
Geographic Intelligence Page — Choropleth maps and state/county analysis.
Choropleth logic adapted from plotly/dash-opioid-epidemic-demo.
"""

import streamlit as st
import plotly.graph_objects as go

from opioid_track.dashboard.components.charts import (
    create_state_choropleth,
    DARK_BG, CARD_BG, GRID_COLOR, TEXT_COLOR, TEAL, AMBER, RED,
    _apply_dark,
)


METRIC_OPTIONS = {
    "risk_score": "Composite Risk Score",
    "prescribing_rate": "Opioid Prescribing Rate",
    "death_rate_per_100k": "Death Rate per 100K",
    "pills_per_capita": "Medicaid Claims Per Capita",
}


def _build_state_bar(geo_data: dict, metric: str, top_n: int = 25) -> go.Figure:
    """Horizontal bar chart comparing states on selected metric."""
    counties = geo_data.get("counties", [])
    state_agg = {}

    for c in counties:
        state = c.get("state_abbr", "")
        state_name = c.get("state", "")
        if not state:
            continue

        if metric == "risk_score":
            val = c.get("derived_metrics", {}).get("risk_score")
        elif metric == "prescribing_rate":
            val = c.get("cms_data", {}).get("prescribing_rate")
        elif metric == "death_rate_per_100k":
            val = c.get("cdc_state_data", {}).get("death_rate_per_100k")
        elif metric == "pills_per_capita":
            val = c.get("medicaid_supply", {}).get("claims_per_capita_annual_avg")
        else:
            val = c.get("derived_metrics", {}).get("risk_score")

        if val is not None:
            if state not in state_agg:
                state_agg[state] = {"name": state_name, "values": []}
            state_agg[state]["values"].append(val)

    state_avgs = []
    for abbr, info in state_agg.items():
        avg = sum(info["values"]) / len(info["values"])
        state_avgs.append((info["name"], abbr, avg))

    state_avgs.sort(key=lambda x: x[2], reverse=True)
    top = state_avgs[:top_n]

    names = [f"{s[0]} ({s[1]})" for s in reversed(top)]
    vals = [s[2] for s in reversed(top)]
    colors = []
    max_val = max(vals) if vals else 1
    for v in vals:
        ratio = v / max_val
        if ratio > 0.7:
            colors.append(RED)
        elif ratio > 0.4:
            colors.append(AMBER)
        else:
            colors.append(TEAL)

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker_color=colors,
        text=[f"{v:.3f}" for v in vals],
        textposition="outside",
    ))
    fig.update_xaxes(title=METRIC_OPTIONS.get(metric, metric))
    return _apply_dark(fig, title=f"Top {top_n} States — {METRIC_OPTIONS.get(metric, metric)}",
                       height=max(400, top_n * 25))


def _build_county_table(geo_data: dict, state_filter: str, metric: str) -> list[dict]:
    """Get county-level data for a selected state."""
    counties = geo_data.get("counties", [])
    rows = []

    for c in counties:
        if state_filter and c.get("state_abbr") != state_filter:
            continue

        risk = c.get("derived_metrics", {}).get("risk_score", 0)
        tier = c.get("derived_metrics", {}).get("risk_tier", "")
        prescribing = c.get("cms_data", {}).get("prescribing_rate")
        death_rate = c.get("cdc_state_data", {}).get("death_rate_per_100k")
        claims = c.get("medicaid_supply", {}).get("claims_per_capita_annual_avg")

        rows.append({
            "County": c.get("county", ""),
            "FIPS": c.get("fips_code", ""),
            "Population": f"{c.get('population', 0):,}",
            "Risk Score": f"{risk:.3f}",
            "Risk Tier": tier,
            "Rx Rate": f"{prescribing:.1f}" if prescribing else "N/A",
            "Death Rate /100K": f"{death_rate:.1f}" if death_rate else "N/A",
            "Claims/Capita": f"{claims:.3f}" if claims else "N/A",
        })

    sort_key = {
        "risk_score": "Risk Score",
        "prescribing_rate": "Rx Rate",
        "death_rate_per_100k": "Death Rate /100K",
        "pills_per_capita": "Claims/Capita",
    }.get(metric, "Risk Score")

    rows.sort(key=lambda r: float(r[sort_key].replace(",", ""))
              if r[sort_key] not in ("N/A", "") else 0, reverse=True)

    return rows[:100]


def render(data: dict):
    st.markdown("<h1 class='section-header'>Geographic Intelligence</h1>",
                unsafe_allow_html=True)
    st.caption("Choropleth approach adapted from plotly/dash-opioid-epidemic-demo")

    geo_data = data.get("geographic")
    mortality = data.get("mortality")

    if not geo_data:
        st.warning("Geographic profiles not available. Run the geographic joiner first.")
        return

    meta = geo_data.get("metadata", {})
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Counties", f"{meta.get('total_counties', 0):,}")
    with col2:
        st.metric("Data Sources", ", ".join(meta.get("data_sources_joined", [])))
    with col3:
        st.metric("Multi-Source Counties",
                  f"{meta.get('counties_with_2plus_sources', 0):,}")

    # --- Metric selector ---
    st.markdown("### National Map")
    metric = st.selectbox(
        "Select metric to visualize",
        list(METRIC_OPTIONS.keys()),
        format_func=lambda k: METRIC_OPTIONS[k],
    )

    # --- Choropleth ---
    fig = create_state_choropleth(geo_data, metric)
    st.plotly_chart(fig, use_container_width=True)

    # --- State comparison bar ---
    st.markdown("### State Comparison")
    col1, col2 = st.columns([1, 4])
    with col1:
        top_n = st.slider("States to show", 10, 50, 25)
    with col2:
        fig = _build_state_bar(geo_data, metric, top_n)
        st.plotly_chart(fig, use_container_width=True)

    # --- Year timeline from mortality ---
    if mortality:
        annual = mortality.get("annual_national", [])
        if annual and len(annual) > 1:
            st.markdown("### Overdose Deaths Over Time")
            years = [a["year"] for a in annual]
            total_deaths = [a.get("total_overdose_deaths", 0) for a in annual]
            opioid_deaths = [a.get("by_opioid_type", {}).get("all_opioids", 0)
                             for a in annual]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=years, y=total_deaths, name="All Drug Overdoses",
                                     mode="lines+markers",
                                     line=dict(color=TEXT_COLOR, width=2)))
            fig.add_trace(go.Scatter(x=years, y=opioid_deaths, name="Opioid Overdoses",
                                     mode="lines+markers",
                                     line=dict(color=RED, width=3)))
            fig.update_yaxes(title="Deaths")
            fig.update_xaxes(title="Year")
            _apply_dark(fig, title="National Overdose Death Trends", height=400)
            st.plotly_chart(fig, use_container_width=True)

    # --- County detail panel ---
    st.markdown("### County Detail")
    counties = geo_data.get("counties", [])
    states = sorted(set(c.get("state_abbr", "") for c in counties if c.get("state_abbr")))

    selected_state = st.selectbox("Select a state", states)
    if selected_state:
        county_rows = _build_county_table(geo_data, selected_state, metric)
        if county_rows:
            st.dataframe(county_rows, use_container_width=True, hide_index=True)
            st.caption(f"Showing top {len(county_rows)} counties in {selected_state}")
        else:
            st.info(f"No county data for {selected_state}")
