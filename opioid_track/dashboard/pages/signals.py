"""
Signal Detection Page — FAERS pharmacovigilance signal heatmap, detail, and rankings.
"""

import streamlit as st
import plotly.graph_objects as go

from opioid_track.dashboard.components.accessibility import (
    chart_caption, section_banner, BANNERS, CHART_CAPTIONS, WIDGET_HELP,
)
from opioid_track.dashboard.components.charts import (
    create_signal_heatmap,
    DARK_BG, CARD_BG, TEXT_COLOR, TEAL, AMBER, RED,
    _apply_dark,
)


def _metric_card(label: str, value, css_class: str = ""):
    cls = f"metric-card {css_class}".strip()
    st.markdown(
        f'<div class="{cls}"><h3>{label}</h3>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def render(data: dict):
    st.markdown("<h1 class='section-header'>Signal Detection</h1>",
                unsafe_allow_html=True)
    section_banner("How Signal Detection Works", BANNERS["signal_detection"])

    signals_data = data.get("signals")
    if not signals_data:
        st.warning("Signal detection data not available. Run the signal detector first.")
        return

    meta = signals_data.get("metadata", {})
    all_signals = signals_data.get("signals", [])
    consensus = [s for s in all_signals if s.get("consensus_signal")]

    # --- Summary metrics ---
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("Total Signals", len(all_signals))
    with col2:
        _metric_card("Consensus Signals", len(consensus), "danger-high")
    with col3:
        _metric_card("Drugs Scanned", meta.get("target_drugs_scanned", 0))
    with col4:
        _metric_card("Safety Terms", meta.get("safety_terms_scanned", 0))

    # --- Signal Heatmap ---
    st.markdown("### Signal Heatmap (Drug x Reaction)")
    st.caption("Color intensity = number of methods flagging (PRR, ROR, MGPS)")

    # Allow filtering to consensus-only
    show_consensus = st.checkbox("Show consensus signals only", value=True,
                                 help=WIDGET_HELP["show_consensus"])
    display_signals = consensus if show_consensus else all_signals

    if display_signals:
        fig = create_signal_heatmap(display_signals)
        st.plotly_chart(fig, use_container_width=True)
        chart_caption(CHART_CAPTIONS["faers_heatmap"])

    # --- Signal Detail ---
    st.markdown("### Signal Detail")
    section_banner("Reading the Signal Metrics", BANNERS["signal_detail"])
    drugs = sorted(set(s["drug_name"] for s in all_signals))
    reactions = sorted(set(s["reaction"] for s in all_signals))

    col1, col2 = st.columns(2)
    with col1:
        selected_drug = st.selectbox("Select Drug", drugs, help=WIDGET_HELP["signal_drug"])
    with col2:
        drug_reactions = sorted(set(
            s["reaction"] for s in all_signals if s["drug_name"] == selected_drug
        ))
        selected_reaction = st.selectbox("Select Reaction", drug_reactions)

    match = next(
        (s for s in all_signals
         if s["drug_name"] == selected_drug and s["reaction"] == selected_reaction),
        None,
    )

    if match:
        st.divider()
        col1, col2, col3 = st.columns(3)

        # PRR
        prr = match.get("prr", {})
        with col1:
            prr_val = prr.get("value", 0)
            css = "danger-high" if prr.get("signal") else "danger-low"
            _metric_card("PRR", f"{prr_val:.2f}", css)
            if prr.get("chi2"):
                st.caption(f"\u03c7\u00b2 = {prr['chi2']:.1f}")

        # ROR
        ror = match.get("ror", {})
        with col2:
            ror_val = ror.get("value", 0)
            css = "danger-high" if ror.get("signal") else "danger-low"
            _metric_card("ROR", f"{ror_val:.2f}", css)
            ci_low = ror.get("ci_lower", 0)
            ci_high = ror.get("ci_upper", 0)
            st.caption(f"95% CI: [{ci_low:.2f}, {ci_high:.2f}]")

        # MGPS
        mgps = match.get("mgps", {})
        with col3:
            ebgm = mgps.get("ebgm", 0)
            css = "danger-high" if mgps.get("signal") else "danger-low"
            _metric_card("EBGM", f"{ebgm:.2f}", css)
            eb05 = mgps.get("eb05", 0)
            st.caption(f"EB05 = {eb05:.2f}")

        # Summary
        methods_flag = match.get("methods_flagging", 0)
        reports = match.get("report_count", 0)

        if match.get("consensus_signal"):
            st.error(
                f"**CONSENSUS SIGNAL** — {selected_drug.capitalize()} / {selected_reaction}: "
                f"{reports:,} reports, flagged by {methods_flag}/3 methods"
            )
        elif methods_flag >= 1:
            st.warning(
                f"**Partial signal** — {selected_drug.capitalize()} / {selected_reaction}: "
                f"{reports:,} reports, flagged by {methods_flag}/3 methods"
            )
        else:
            st.success(
                f"**No signal** — {selected_drug.capitalize()} / {selected_reaction}: "
                f"{reports:,} reports, not flagged"
            )

    # --- Top Signals Table ---
    st.markdown("### Top Signals (Ranked)")
    sort_by = st.radio("Sort by", ["Methods Flagging", "Report Count"],
                       horizontal=True, help=WIDGET_HELP["sort_signals"])

    if sort_by == "Methods Flagging":
        sorted_signals = sorted(consensus, key=lambda s: (
            -s.get("methods_flagging", 0), -s.get("report_count", 0)
        ))
    else:
        sorted_signals = sorted(consensus, key=lambda s: -s.get("report_count", 0))

    rows = []
    for s in sorted_signals[:50]:
        prr_val = s.get("prr", {}).get("value", 0)
        ror_val = s.get("ror", {}).get("value", 0)
        ebgm_val = s.get("mgps", {}).get("ebgm", 0)
        rows.append({
            "Drug": s["drug_name"].capitalize(),
            "Reaction": s["reaction"],
            "Reports": f"{s.get('report_count', 0):,}",
            "Methods": f"{s.get('methods_flagging', 0)}/3",
            "PRR": f"{prr_val:.1f}",
            "ROR": f"{ror_val:.1f}",
            "EBGM": f"{ebgm_val:.1f}",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- Per-drug signal summary ---
    st.markdown("### Per-Drug Signal Summary")
    drug_summary = {}
    for s in consensus:
        drug = s["drug_name"]
        if drug not in drug_summary:
            drug_summary[drug] = {"count": 0, "total_reports": 0, "top_reaction": "", "top_reports": 0}
        drug_summary[drug]["count"] += 1
        drug_summary[drug]["total_reports"] += s.get("report_count", 0)
        if s.get("report_count", 0) > drug_summary[drug]["top_reports"]:
            drug_summary[drug]["top_reports"] = s.get("report_count", 0)
            drug_summary[drug]["top_reaction"] = s["reaction"]

    summary_rows = []
    for drug, info in sorted(drug_summary.items(), key=lambda x: -x[1]["count"]):
        summary_rows.append({
            "Drug": drug.capitalize(),
            "Consensus Signals": info["count"],
            "Total Reports": f"{info['total_reports']:,}",
            "Top Signal": info["top_reaction"],
        })
    st.dataframe(summary_rows, use_container_width=True, hide_index=True)
