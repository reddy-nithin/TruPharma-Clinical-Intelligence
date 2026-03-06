"""
TruPharma Opioid Dashboard — Reusable Chart Components
======================================================
Plotly figure builders for the opioid dashboard.
Choropleth logic adapted from plotly/dash-opioid-epidemic-demo.
"""

import math
import plotly.graph_objects as go
import plotly.express as px

DARK_BG = "#0d1b2a"
CARD_BG = "#1b2838"
GRID_COLOR = "#2d4a5e"
TEXT_COLOR = "#e0e6ed"
TEAL = "#5eead4"
CYAN = "#22d3ee"
AMBER = "#f59e0b"
RED = "#ef4444"

CATEGORY_COLORS = {
    "natural/semi-synthetic": "#22c55e",
    "synthetic": "#ef4444",
    "semi-synthetic": "#f59e0b",
    "combination": "#8b5cf6",
    "treatment/recovery": "#3b82f6",
}

DARK_LAYOUT = dict(
    paper_bgcolor=DARK_BG,
    plot_bgcolor=CARD_BG,
    font=dict(color=TEXT_COLOR, size=12),
    margin=dict(l=40, r=20, t=50, b=40),
    xaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
    yaxis=dict(gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR),
)


def _apply_dark(fig, **overrides):
    layout = {**DARK_LAYOUT, **overrides}
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Choropleth — adapted from plotly/dash-opioid-epidemic-demo
# ---------------------------------------------------------------------------

def create_choropleth(geo_data: dict, metric: str = "risk_score") -> go.Figure:
    """County-level choropleth map.

    geo_data: opioid_geographic_profiles.json
    metric: one of risk_score, prescribing_rate, death_rate_per_100k
    """
    counties = geo_data.get("counties", [])
    if not counties:
        fig = go.Figure()
        fig.add_annotation(text="No geographic data available", showarrow=False)
        return _apply_dark(fig, title="Geographic Data Unavailable")

    fips_codes = []
    values = []
    hover_texts = []

    metric_labels = {
        "risk_score": "Risk Score",
        "prescribing_rate": "Prescribing Rate",
        "death_rate_per_100k": "Death Rate /100K",
        "pills_per_capita": "Claims Per Capita",
    }

    for c in counties:
        fips = c.get("fips_code", "")
        if not fips:
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

        if val is None:
            continue

        fips_codes.append(fips)
        values.append(val)
        county_name = c.get("county", "")
        state = c.get("state_abbr", "")
        hover_texts.append(f"{county_name}, {state}<br>{metric_labels.get(metric, metric)}: {val:.3f}")

    colorscales = {
        "risk_score": "YlOrRd",
        "prescribing_rate": "Oranges",
        "death_rate_per_100k": "Reds",
        "pills_per_capita": "Blues",
    }

    fig = go.Figure(go.Choropleth(
        locationmode="USA-states",
        locations=[f[:2] for f in fips_codes],
        z=values,
        text=hover_texts,
        hoverinfo="text",
        colorscale=colorscales.get(metric, "YlOrRd"),
        colorbar=dict(
            title=metric_labels.get(metric, metric),
            thickness=15,
            len=0.6,
        ),
    ))

    fig.update_layout(
        geo=dict(
            scope="usa",
            bgcolor=DARK_BG,
            lakecolor=CARD_BG,
            landcolor=CARD_BG,
            showlakes=True,
        ),
    )
    return _apply_dark(fig, title=f"US {metric_labels.get(metric, metric)} by State")


def create_state_choropleth(geo_data: dict, metric: str = "risk_score") -> go.Figure:
    """State-level aggregated choropleth."""
    counties = geo_data.get("counties", [])
    state_agg = {}

    for c in counties:
        state = c.get("state_abbr", "")
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
            state_agg.setdefault(state, []).append(val)

    states = sorted(state_agg.keys())
    avgs = [sum(state_agg[s]) / len(state_agg[s]) for s in states]

    metric_labels = {
        "risk_score": "Avg Risk Score",
        "prescribing_rate": "Avg Prescribing Rate",
        "death_rate_per_100k": "Avg Death Rate /100K",
        "pills_per_capita": "Avg Claims Per Capita",
    }

    fig = go.Figure(go.Choropleth(
        locationmode="USA-states",
        locations=states,
        z=avgs,
        colorscale="YlOrRd",
        colorbar=dict(title=metric_labels.get(metric, metric)),
    ))
    fig.update_layout(
        geo=dict(scope="usa", bgcolor=DARK_BG, lakecolor=CARD_BG, landcolor=CARD_BG),
    )
    return _apply_dark(fig, title=f"US {metric_labels.get(metric, metric)} by State")


# ---------------------------------------------------------------------------
# Potency chart
# ---------------------------------------------------------------------------

def create_potency_chart(pharmacology_data: dict) -> go.Figure:
    """Horizontal bar chart of ingredient potency vs morphine (log scale)."""
    ingredients = pharmacology_data.get("ingredient_pharmacology", {})
    names, potencies, colors = [], [], []

    for name, data in ingredients.items():
        potency = data.get("potency_vs_morphine")
        if potency and potency > 0:
            names.append(name.capitalize())
            potencies.append(potency)
            mu_ki = data.get("receptor_affinities", {}).get("mu", {}).get("ki_nM")
            if mu_ki and mu_ki < 1:
                colors.append(RED)
            elif mu_ki and mu_ki < 5:
                colors.append(AMBER)
            else:
                colors.append(TEAL)

    sorted_data = sorted(zip(names, potencies, colors), key=lambda x: x[1])
    names, potencies, colors = zip(*sorted_data) if sorted_data else ([], [], [])

    fig = go.Figure(go.Bar(
        x=list(potencies),
        y=list(names),
        orientation="h",
        marker_color=list(colors),
        text=[f"{p:.1f}x" for p in potencies],
        textposition="outside",
    ))
    fig.add_vline(x=1.0, line_dash="dash", line_color=CYAN,
                  annotation_text="Morphine reference")
    fig.update_xaxes(type="log", title="Potency vs Morphine (log scale)")
    return _apply_dark(fig, title="Opioid Potency vs Morphine (mu Ki ratio)",
                       height=max(350, len(names) * 35))


# ---------------------------------------------------------------------------
# Danger scatter
# ---------------------------------------------------------------------------

def create_danger_scatter(pharmacology_data: dict, signal_data: list | None) -> go.Figure:
    """Scatter: X=potency, Y=FAERS reports, bubble=danger level."""
    ingredients = pharmacology_data.get("ingredient_pharmacology", {})

    signal_counts = {}
    if signal_data:
        for s in signal_data:
            drug = s.get("drug_name", "").lower()
            signal_counts[drug] = signal_counts.get(drug, 0) + s.get("report_count", 0)

    names, x_vals, y_vals, sizes, colors, hovers = [], [], [], [], [], []

    for name, data in ingredients.items():
        potency = data.get("potency_vs_morphine")
        if not potency or potency <= 0:
            continue

        reports = signal_counts.get(name, 0)
        danger = data.get("danger_level", "Unknown")
        danger_rank = data.get("danger_rank", 5)

        names.append(name.capitalize())
        x_vals.append(potency)
        y_vals.append(max(reports, 1))
        sizes.append(max(15, 50 - danger_rank * 8))

        color_map = {"Extreme": RED, "Very High": "#dc2626",
                     "High": AMBER, "Moderate": "#fbbf24", "Lower": TEAL}
        colors.append(color_map.get(danger, "#64748b"))
        hovers.append(f"{name.capitalize()}<br>Potency: {potency:.1f}x<br>"
                      f"FAERS reports: {reports:,}<br>Danger: {danger}")

    fig = go.Figure(go.Scatter(
        x=x_vals, y=y_vals, mode="markers+text",
        marker=dict(size=sizes, color=colors, line=dict(width=1, color="#fff")),
        text=names, textposition="top center",
        textfont=dict(size=9, color=TEXT_COLOR),
        hovertext=hovers, hoverinfo="text",
    ))
    fig.update_xaxes(type="log", title="Potency vs Morphine")
    fig.update_yaxes(type="log", title="FAERS Report Count")
    return _apply_dark(fig, title="Potency vs Safety Signal Profile", height=500)


# ---------------------------------------------------------------------------
# Signal heatmap
# ---------------------------------------------------------------------------

def create_signal_heatmap(signal_data: list) -> go.Figure:
    """Drug x Reaction heatmap colored by methods flagging count."""
    if not signal_data:
        fig = go.Figure()
        fig.add_annotation(text="No signal data available", showarrow=False)
        return _apply_dark(fig)

    drugs = sorted(set(s["drug_name"] for s in signal_data))
    reactions = sorted(set(s["reaction"] for s in signal_data))

    z = []
    hover = []
    for reaction in reactions:
        row = []
        hover_row = []
        for drug in drugs:
            match = next(
                (s for s in signal_data
                 if s["drug_name"] == drug and s["reaction"] == reaction),
                None,
            )
            if match:
                row.append(match.get("methods_flagging", 0))
                hover_row.append(
                    f"{drug} — {reaction}<br>"
                    f"Reports: {match.get('report_count', 0):,}<br>"
                    f"Methods: {match.get('methods_flagging', 0)}/3"
                )
            else:
                row.append(0)
                hover_row.append(f"{drug} — {reaction}<br>No data")
        z.append(row)
        hover.append(hover_row)

    fig = go.Figure(go.Heatmap(
        x=[d.capitalize() for d in drugs],
        y=reactions,
        z=z,
        hovertext=hover,
        hoverinfo="text",
        colorscale=[[0, "#1b2838"], [0.33, "#22c55e"],
                    [0.66, AMBER], [1.0, RED]],
        colorbar=dict(title="Methods<br>Flagging", tickvals=[0, 1, 2, 3]),
    ))
    fig.update_xaxes(tickangle=45)
    return _apply_dark(fig, title="FAERS Signal Heatmap (Drug x Reaction)",
                       height=max(500, len(reactions) * 22))


# ---------------------------------------------------------------------------
# Timeline chart
# ---------------------------------------------------------------------------

def create_timeline_chart(mortality_data: dict) -> go.Figure:
    """Three waves of the opioid epidemic timeline."""
    annual = mortality_data.get("annual_national", [])
    if not annual:
        fig = go.Figure()
        fig.add_annotation(text="No mortality data available", showarrow=False)
        return _apply_dark(fig)

    years = [a["year"] for a in annual]

    traces = {
        "All Opioids": [],
        "Natural/Semi-synthetic (T40.2)": [],
        "Heroin (T40.1)": [],
        "Synthetic/Fentanyl (T40.4)": [],
        "Methadone (T40.3)": [],
    }
    trace_colors = {
        "All Opioids": TEXT_COLOR,
        "Natural/Semi-synthetic (T40.2)": "#22c55e",
        "Heroin (T40.1)": AMBER,
        "Synthetic/Fentanyl (T40.4)": RED,
        "Methadone (T40.3)": "#8b5cf6",
    }

    for a in annual:
        by_type = a.get("by_opioid_type", {})
        traces["All Opioids"].append(by_type.get("all_opioids", 0))
        traces["Natural/Semi-synthetic (T40.2)"].append(
            by_type.get("natural_semisynthetic_T40.2", 0))
        traces["Heroin (T40.1)"].append(by_type.get("heroin_T40.1", 0))
        traces["Synthetic/Fentanyl (T40.4)"].append(
            by_type.get("synthetic_fentanyl_T40.4", 0))
        traces["Methadone (T40.3)"].append(by_type.get("methadone_T40.3", 0))

    fig = go.Figure()
    for name, vals in traces.items():
        fig.add_trace(go.Scatter(
            x=years, y=vals, name=name, mode="lines+markers",
            line=dict(color=trace_colors.get(name, TEAL), width=2 if name != "All Opioids" else 3),
            marker=dict(size=5),
        ))

    wave_annotations = [
        dict(x=2000, y=max(traces["All Opioids"][:6]) if len(traces["All Opioids"]) > 5 else 0,
             text="Wave 1<br>Rx Opioids", showarrow=True, arrowcolor=TEAL,
             font=dict(color=TEAL, size=10)),
        dict(x=2011, y=max(traces["Heroin (T40.1)"]) if traces["Heroin (T40.1)"] else 0,
             text="Wave 2<br>Heroin", showarrow=True, arrowcolor=AMBER,
             font=dict(color=AMBER, size=10)),
        dict(x=2015, y=max(traces["Synthetic/Fentanyl (T40.4)"]) if traces["Synthetic/Fentanyl (T40.4)"] else 0,
             text="Wave 3<br>Synthetic", showarrow=True, arrowcolor=RED,
             font=dict(color=RED, size=10)),
    ]
    fig.update_layout(annotations=[a for a in wave_annotations if a["y"] > 0])
    fig.update_yaxes(title="Overdose Deaths")
    fig.update_xaxes(title="Year")
    return _apply_dark(fig, title="Three Waves of the Opioid Epidemic",
                       height=450, legend=dict(orientation="h", y=-0.15))


# ---------------------------------------------------------------------------
# Receptor affinity bar (per-drug)
# ---------------------------------------------------------------------------

def create_receptor_bar(affinities: dict) -> go.Figure:
    """Bar chart of receptor Ki values for a single drug."""
    receptor_labels = {"mu": "\u03bc (OPRM1)", "kappa": "\u03ba (OPRK1)",
                       "delta": "\u03b4 (OPRD1)", "nop": "NOP (OPRL1)"}
    receptor_colors = {"mu": TEAL, "kappa": AMBER, "delta": "#8b5cf6", "nop": "#3b82f6"}

    receptors, kis, cols = [], [], []
    for rec in ("mu", "kappa", "delta", "nop"):
        data = affinities.get(rec)
        if data and data.get("ki_nM"):
            receptors.append(receptor_labels[rec])
            kis.append(data["ki_nM"])
            cols.append(receptor_colors[rec])

    if not receptors:
        fig = go.Figure()
        fig.add_annotation(text="No receptor affinity data", showarrow=False)
        return _apply_dark(fig, height=200)

    fig = go.Figure(go.Bar(
        x=receptors, y=kis, marker_color=cols,
        text=[f"{k:.1f} nM" for k in kis],
        textposition="outside",
    ))
    fig.update_yaxes(type="log", title="Ki (nM) — lower = stronger binding")
    return _apply_dark(fig, title="Receptor Binding Affinity", height=350)


# ---------------------------------------------------------------------------
# Schedule donut
# ---------------------------------------------------------------------------

def create_schedule_donut(registry: dict) -> go.Figure:
    """Donut chart of drugs by DEA schedule."""
    schedule_counts = {}
    for drug in registry.get("opioid_drugs", []):
        sched = drug.get("schedule", "") or "Unscheduled"
        schedule_counts[sched] = schedule_counts.get(sched, 0) + 1

    labels = list(schedule_counts.keys())
    values = list(schedule_counts.values())

    sched_colors = {"CII": RED, "CIII": AMBER, "CIV": "#fbbf24",
                    "CV": TEAL, "Unscheduled": "#64748b"}
    colors = [sched_colors.get(l, "#64748b") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.5,
        marker=dict(colors=colors, line=dict(color=DARK_BG, width=2)),
        textinfo="label+percent",
        textfont=dict(color=TEXT_COLOR),
    ))
    return _apply_dark(fig, title="Opioid Products by DEA Schedule", height=400)
