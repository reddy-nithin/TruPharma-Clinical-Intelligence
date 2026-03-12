"""
Demographics Page — Opioid overdose deaths by age, sex, and race/ethnicity.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from opioid_track.dashboard.components.accessibility import (
    chart_caption, section_banner, BANNERS, CHART_CAPTIONS, WIDGET_HELP,
)
from opioid_track.dashboard.components.charts import (
    DARK_BG, CARD_BG, GRID_COLOR, TEXT_COLOR, TEAL, AMBER, RED,
    CATEGORY_COLORS, _apply_dark,
)


def _metric_card(label: str, value, css_class: str = ""):
    cls = f"metric-card {css_class}".strip()
    st.markdown(
        f'<div class="{cls}"><h3>{label}</h3>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


# Color palettes for demographic charts
AGE_COLORS = ["#1e3a5f", "#0e7a60", "#3df5c8", "#f59e0b", "#ef4444", "#dc2626", "#9333ea"]
SEX_COLORS = ["#3df5c8", "#f472b6"]
RACE_COLORS = ["#3df5c8", "#ef4444", "#f59e0b", "#9333ea", "#60a5fa", "#a3a3a3"]


def _build_age_bar(data: list[dict]) -> go.Figure:
    """Horizontal bar chart of overdose deaths by age group."""
    groups = [d["group"] for d in data]
    deaths = [d["deaths"] for d in data]
    rates = [d["rate_per_100k"] for d in data]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=groups, x=deaths, orientation="h",
        marker_color=AGE_COLORS[:len(groups)],
        text=[f"{d:,}" for d in deaths],
        textposition="outside",
        customdata=rates,
        hovertemplate="<b>%{y}</b><br>Deaths: %{x:,}<br>Rate: %{customdata:.1f}/100K<extra></extra>",
    ))
    fig.update_xaxes(title="Opioid-Involved Overdose Deaths")
    return _apply_dark(fig, title="Deaths by Age Group (2022)", height=350)


def _build_sex_donut(data: list[dict]) -> go.Figure:
    """Donut chart of male vs female deaths."""
    labels = [d["sex"] for d in data]
    values = [d["deaths"] for d in data]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=SEX_COLORS),
        textinfo="label+percent",
        textfont=dict(size=14, color=TEXT_COLOR),
        hovertemplate="<b>%{label}</b><br>Deaths: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color=TEXT_COLOR),
        showlegend=False,
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(
            text="Deaths by Sex (2022)",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
        ),
    )
    return fig


def _build_race_bar(data: list[dict], metric: str = "rate_per_100k") -> go.Figure:
    """Bar chart of overdose death rates by race/ethnicity."""
    groups = [d["group"] for d in data]
    values = [d[metric] for d in data]

    if metric == "rate_per_100k":
        title = "Rate per 100K by Race/Ethnicity (2022)"
        x_title = "Deaths per 100,000 Population"
        text = [f"{v:.1f}" for v in values]
    else:
        title = "Deaths by Race/Ethnicity (2022)"
        x_title = "Opioid-Involved Overdose Deaths"
        text = [f"{v:,}" for v in values]

    fig = go.Figure(go.Bar(
        y=groups, x=values, orientation="h",
        marker_color=RACE_COLORS[:len(groups)],
        text=text,
        textposition="outside",
    ))
    fig.update_xaxes(title=x_title)
    return _apply_dark(fig, title=title, height=350)


def _build_age_trends(data: list[dict]) -> go.Figure:
    """Multi-line chart: trends over time by age group."""
    age_groups = sorted(set(d["age_group"] for d in data))
    colors_map = dict(zip(age_groups, AGE_COLORS))

    fig = go.Figure()
    for ag in age_groups:
        subset = sorted(
            [d for d in data if d["age_group"] == ag],
            key=lambda x: x["year"],
        )
        fig.add_trace(go.Scatter(
            x=[d["year"] for d in subset],
            y=[d["rate_per_100k"] for d in subset],
            mode="lines+markers",
            name=ag,
            line=dict(width=2, color=colors_map.get(ag, TEXT_COLOR)),
            marker=dict(size=6),
        ))
    fig.update_xaxes(title="Year", dtick=1)
    fig.update_yaxes(title="Rate per 100K")
    return _apply_dark(fig, title="Opioid Overdose Rate Trends by Age Group (2015–2022)", height=420)


def _build_sex_trends(data: list[dict]) -> go.Figure:
    """Line chart: trends by sex."""
    fig = go.Figure()
    for i, sex in enumerate(["Male", "Female"]):
        subset = sorted(
            [d for d in data if d["sex"] == sex],
            key=lambda x: x["year"],
        )
        fig.add_trace(go.Scatter(
            x=[d["year"] for d in subset],
            y=[d["rate_per_100k"] for d in subset],
            mode="lines+markers",
            name=sex,
            line=dict(width=3, color=SEX_COLORS[i]),
            marker=dict(size=7),
        ))
    fig.update_xaxes(title="Year", dtick=1)
    fig.update_yaxes(title="Rate per 100K")
    return _apply_dark(fig, title="Overdose Rate by Sex (2015–2022)", height=380)


def _build_race_trends(data: list[dict]) -> go.Figure:
    """Multi-line chart: trends by race/ethnicity."""
    groups = sorted(set(d["group"] for d in data))
    colors_map = dict(zip(groups, RACE_COLORS))

    fig = go.Figure()
    for grp in groups:
        subset = sorted(
            [d for d in data if d["group"] == grp],
            key=lambda x: x["year"],
        )
        fig.add_trace(go.Scatter(
            x=[d["year"] for d in subset],
            y=[d["rate_per_100k"] for d in subset],
            mode="lines+markers",
            name=grp,
            line=dict(width=2, color=colors_map.get(grp, TEXT_COLOR)),
            marker=dict(size=6),
        ))
    fig.update_xaxes(title="Year", dtick=1)
    fig.update_yaxes(title="Rate per 100K")
    return _apply_dark(fig, title="Overdose Rate by Race/Ethnicity (2015–2022)", height=420)


def render(data: dict):
    st.markdown("<h1 class='section-header'>Demographics</h1>",
                unsafe_allow_html=True)
    st.caption("Opioid-involved overdose deaths by age, sex, and race/ethnicity "
               "(Source: CDC NCHS, WONDER, MMWR)")

    demographics = data.get("demographics")
    if not demographics:
        st.warning("Demographics data not available. Run demographics_builder first.")
        return

    meta = demographics.get("metadata", {})
    by_age = demographics.get("by_age_group", [])
    by_sex = demographics.get("by_sex", [])
    by_race = demographics.get("by_race_ethnicity", [])
    trends_age = demographics.get("trends_by_age", [])
    trends_sex = demographics.get("trends_by_sex", [])
    trends_race = demographics.get("trends_by_race", [])

    # --- Summary metrics ---
    total = meta.get("total_opioid_overdose_deaths_2022", 0)
    peak_age = meta.get("peak_age_group", "N/A")
    highest_rate_race = meta.get("highest_rate_race_ethnicity", "N/A")
    male_pct = next((d["pct_of_total"] for d in by_sex if d["sex"] == "Male"), 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("Total Deaths (2022)", f"{total:,}", "danger-high")
    with col2:
        _metric_card("Peak Age Group", peak_age)
    with col3:
        _metric_card("Male Share", f"{male_pct:.0f}%")
    with col4:
        _metric_card("Highest Rate", highest_rate_race, "danger-high")

    # --- Distribution Section ---
    st.markdown("<h2 class='tp-section-header'>Distribution (2022)</h2>",
                unsafe_allow_html=True)

    col_age, col_sex = st.columns([3, 2])
    with col_age:
        if by_age:
            fig = _build_age_bar(by_age)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Age group 35–44 has the highest number of deaths; 25–34 has "
                "the second-highest rate per 100K, reflecting the peak impact "
                "on working-age adults."
            )
    with col_sex:
        if by_sex:
            fig = _build_sex_donut(by_sex)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Males account for nearly 70% of all opioid overdose deaths. "
                "The male death rate is more than 2× the female rate."
            )

    # Race/ethnicity
    if by_race:
        st.markdown("### Race/Ethnicity Breakdown")
        race_metric = st.radio(
            "View by",
            ["Rate per 100K", "Total Deaths"],
            horizontal=True,
            key="race_metric",
        )
        metric_key = "rate_per_100k" if "Rate" in race_metric else "deaths"
        fig = _build_race_bar(by_race, metric=metric_key)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "American Indian/Alaska Native populations have the highest "
            "age-adjusted rate per 100K, followed by Black Non-Hispanic. "
            "White Non-Hispanic populations have the highest absolute number "
            "of deaths due to larger population size."
        )

    # --- Trends Section ---
    st.markdown("<h2 class='tp-section-header'>Trends Over Time (2015–2022)</h2>",
                unsafe_allow_html=True)

    trend_tab = st.radio(
        "Trend view",
        ["By Age Group", "By Sex", "By Race/Ethnicity"],
        horizontal=True,
        key="trend_view",
    )

    if trend_tab == "By Age Group" and trends_age:
        fig = _build_age_trends(trends_age)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Ages 25–44 saw the steepest increases from 2019–2022, driven by "
            "the rise of illicitly manufactured fentanyl (Wave 3). The 35–44 "
            "age group overtook 25–34 as the highest-rate group in 2022."
        )
    elif trend_tab == "By Sex" and trends_sex:
        fig = _build_sex_trends(trends_sex)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Both sexes show sharp increases from 2019–2022. The male rate "
            "diverged significantly from the female rate during this period, "
            "widening the gender gap."
        )
    elif trend_tab == "By Race/Ethnicity" and trends_race:
        fig = _build_race_trends(trends_race)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "The most dramatic increase was among American Indian/Alaska Native "
            "and Black Non-Hispanic populations, whose rates tripled from "
            "2015 to 2022. This reflects widening racial disparities in the "
            "opioid crisis."
        )

    # --- Key Insights ---
    st.markdown("<h2 class='tp-section-header'>Key Insights</h2>",
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            "**Age:** Adults aged 25–44 account for nearly **47%** of all "
            "opioid overdose deaths. The 35–44 age group now has the highest "
            "rate at 43.9 per 100K."
        )
        st.markdown(
            "**Sex:** Males die from opioid overdoses at **2.3×** the rate "
            "of females (33.1 vs 14.2 per 100K)."
        )
    with col2:
        st.markdown(
            "**Race/Ethnicity:** American Indian/Alaska Native populations "
            "have the highest rate (44.3/100K) — despite representing only "
            "1.9% of total deaths. Black Non-Hispanic populations have the "
            "second-highest rate (40.8/100K)."
        )
        st.markdown(
            "**Trend:** Opioid deaths increased **133%** from 2015 to 2022 "
            "(33,258 → 77,403), driven primarily by synthetic opioids "
            "(fentanyl) in Wave 3 of the epidemic."
        )
