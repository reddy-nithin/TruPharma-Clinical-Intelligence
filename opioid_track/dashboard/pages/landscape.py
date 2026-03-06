"""
Opioid Landscape Page — Classification, potency, danger, and epidemic overview.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from opioid_track.dashboard.components.charts import (
    create_potency_chart,
    create_danger_scatter,
    create_timeline_chart,
    create_schedule_donut,
    DARK_BG, CARD_BG, GRID_COLOR, TEXT_COLOR, TEAL, AMBER, RED,
    CATEGORY_COLORS, _apply_dark,
)


def _build_treemap(registry: dict, signals: dict | None) -> go.Figure:
    """Category treemap sized by drug count (or FAERS reports if available)."""
    signal_counts = {}
    if signals:
        for s in signals.get("signals", []):
            drug = s.get("drug_name", "").lower()
            signal_counts[drug] = signal_counts.get(drug, 0) + s.get("report_count", 0)

    labels = ["Opioids"]
    parents = [""]
    values = [0]
    colors = ["#1e293b"]

    category_drugs = {}
    for drug in registry.get("opioid_drugs", []):
        cat = (drug.get("opioid_category") or "unknown").title()
        name = drug.get("drug_name", "")
        opioid_ings = [i for i in drug.get("active_ingredients", [])
                       if i.get("is_opioid_component")]
        if not opioid_ings:
            continue
        category_drugs.setdefault(cat, []).append({
            "name": name,
            "ingredient": opioid_ings[0]["name"].lower(),
        })

    for cat, drugs_list in category_drugs.items():
        labels.append(cat)
        parents.append("Opioids")
        values.append(0)
        colors.append(CATEGORY_COLORS.get(cat.lower(), "#64748b"))

        seen = set()
        for d in drugs_list[:25]:
            short = d["ingredient"].capitalize()
            if short in seen:
                continue
            seen.add(short)
            labels.append(short)
            parents.append(cat)
            reports = signal_counts.get(d["ingredient"], 1)
            values.append(max(reports, 1))
            colors.append(CATEGORY_COLORS.get(cat.lower(), "#64748b"))

    fig = go.Figure(go.Treemap(
        labels=labels, parents=parents, values=values,
        marker=dict(colors=colors, line=dict(width=1, color=DARK_BG)),
        textinfo="label+value",
        textfont=dict(color=TEXT_COLOR),
        hovertemplate="<b>%{label}</b><br>FAERS Reports: %{value:,}<extra></extra>",
    ))
    return _apply_dark(fig, title="Opioid Classification (sized by FAERS reports)", height=500)


def _build_danger_matrix(pharmacology: dict) -> go.Figure:
    """Matrix scatter: X=potency, Y=therapeutic index, color=danger."""
    ingredients = pharmacology.get("ingredient_pharmacology", {})

    names, x_vals, y_vals, colors, sizes, hovers = [], [], [], [], [], []

    for name, data in ingredients.items():
        potency = data.get("potency_vs_morphine")
        ti = data.get("therapeutic_index")
        if not potency or potency <= 0:
            continue

        danger = data.get("danger_level", "Unknown")
        color_map = {"Extreme": RED, "Very High": "#dc2626",
                     "High": AMBER, "Moderate": "#fbbf24",
                     "Lower": TEAL, "Unknown": "#64748b"}

        names.append(name.capitalize())
        x_vals.append(potency)
        y_vals.append(ti if ti and ti > 0 else 1)
        colors.append(color_map.get(danger, "#64748b"))
        sizes.append(20)
        lethal = data.get("estimated_human_lethal_dose_mg")
        hovers.append(
            f"{name.capitalize()}<br>"
            f"Potency: {potency:.1f}x morphine<br>"
            f"TI: {ti or 'N/A'}<br>"
            f"Danger: {danger}<br>"
            f"Lethal dose: {f'{lethal:.0f} mg' if lethal else 'Unknown'}"
        )

    fig = go.Figure(go.Scatter(
        x=x_vals, y=y_vals, mode="markers+text",
        marker=dict(size=sizes, color=colors, line=dict(width=1, color="#fff")),
        text=names, textposition="top center",
        textfont=dict(size=9, color=TEXT_COLOR),
        hovertext=hovers, hoverinfo="text",
    ))
    fig.update_xaxes(type="log", title="Potency vs Morphine (log)")
    fig.update_yaxes(type="log", title="Therapeutic Index (log) — higher = safer")
    fig.add_hline(y=10, line_dash="dash", line_color=AMBER,
                  annotation_text="TI=10 (narrow margin)")
    return _apply_dark(fig, title="Danger Matrix: Potency vs Safety Margin", height=450)


def render(data: dict):
    st.markdown("<h1 class='section-header'>Opioid Landscape</h1>", unsafe_allow_html=True)

    registry = data.get("registry")
    pharmacology = data.get("pharmacology")
    signals = data.get("signals")
    mortality = data.get("mortality")

    if not registry:
        st.warning("Registry data not available.")
        return

    # --- Classification Treemap ---
    st.markdown("### Classification Overview")
    fig = _build_treemap(registry, signals)
    st.plotly_chart(fig, use_container_width=True)

    # --- Two-column: Potency + Schedule ---
    col1, col2 = st.columns([3, 2])

    with col1:
        if pharmacology:
            st.markdown("### Potency Comparison")
            fig = create_potency_chart(pharmacology)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### Schedule Breakdown")
        fig = create_schedule_donut(registry)
        st.plotly_chart(fig, use_container_width=True)

    # --- Danger Matrix ---
    if pharmacology:
        st.markdown("### Danger Matrix")
        fig = _build_danger_matrix(pharmacology)
        st.plotly_chart(fig, use_container_width=True)

    # --- Danger Scatter (FAERS overlay) ---
    if pharmacology and signals:
        st.markdown("### Potency vs FAERS Safety Signals")
        fig = create_danger_scatter(pharmacology, signals.get("signals", []))
        st.plotly_chart(fig, use_container_width=True)

    # --- Three Waves Timeline ---
    if mortality:
        st.markdown("### Three Waves of the Opioid Epidemic")
        fig = create_timeline_chart(mortality)
        st.plotly_chart(fig, use_container_width=True)

        # Summary stats
        annual = mortality.get("annual_national", [])
        if annual:
            latest = annual[-1]
            by_type = latest.get("by_opioid_type", {})
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(f"Total Opioid Deaths ({latest['year']})",
                          f"{by_type.get('all_opioids', 0):,}")
            with col2:
                st.metric("Synthetic/Fentanyl",
                          f"{by_type.get('synthetic_fentanyl_T40.4', 0):,}")
            with col3:
                st.metric("Natural/Semi-synthetic",
                          f"{by_type.get('natural_semisynthetic_T40.2', 0):,}")
            with col4:
                st.metric("Heroin",
                          f"{by_type.get('heroin_T40.1', 0):,}")
    else:
        st.info("CDC mortality data not available. Run the CDC mortality fetcher first.")

    # --- Danger Rankings Table ---
    if pharmacology:
        rankings = pharmacology.get("danger_rankings", [])
        if rankings:
            st.markdown("### Danger Rankings")
            rows = []
            for r in rankings:
                dose = r.get("estimated_lethal_dose_mg")
                rows.append({
                    "Ingredient": r["ingredient"].capitalize(),
                    "Danger Level": r["danger_level"],
                    "Rank": r["danger_rank"],
                    "Est. Lethal Dose (70kg)": f"{dose:.0f} mg" if dose else "Unknown",
                })
            st.dataframe(rows, use_container_width=True, hide_index=True)
