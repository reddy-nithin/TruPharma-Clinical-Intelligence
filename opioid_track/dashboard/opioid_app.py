"""
TruPharma Opioid Intelligence Dashboard — Main Entry Point
==========================================================
Standalone Streamlit app for opioid pharmacology, signals, and epidemiology.

Usage:
    streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
"""

import json
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from opioid_track import config

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=config.DASHBOARD_TITLE,
    page_icon="\U0001F9EA",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Dark theme CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1b2a 0%, #1b2838 100%);
    }
    [data-testid="stSidebar"] * { color: #e0e6ed !important; }
    .metric-card {
        background: linear-gradient(135deg, #1b2838, #243447);
        border: 1px solid #2d4a5e;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.5rem;
    }
    .metric-card h3 { color: #5eead4; margin: 0 0 0.3rem 0; font-size: 0.85rem; }
    .metric-card .value { color: #f0f4f8; font-size: 1.6rem; font-weight: 700; }
    .danger-high { border-left: 4px solid #ef4444; }
    .danger-moderate { border-left: 4px solid #f59e0b; }
    .danger-low { border-left: 4px solid #22c55e; }
    .section-header {
        color: #5eead4;
        border-bottom: 2px solid #2d4a5e;
        padding-bottom: 0.3rem;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def load_json_safe(path: str) -> dict | list | None:
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return None


@st.cache_data(ttl=3600)
def load_all_data():
    return {
        "registry": load_json_safe(config.REGISTRY_OUTPUT),
        "pharmacology": load_json_safe(config.PHARMACOLOGY_OUTPUT),
        "signals": load_json_safe(config.SIGNAL_RESULTS_OUTPUT),
        "nlp_insights": load_json_safe(config.NLP_INSIGHTS_OUTPUT),
        "mortality": load_json_safe(config.CDC_MORTALITY_OUTPUT),
        "prescribing": load_json_safe(config.CMS_PRESCRIBING_OUTPUT),
        "geographic": load_json_safe(config.GEO_PROFILES_OUTPUT),
        "mme": load_json_safe(config.MME_REFERENCE_OUTPUT),
    }


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown(
            f"<h2 style='color:#5eead4; margin-bottom:0'>{config.DASHBOARD_TITLE}</h2>"
            "<p style='color:#94a3b8; font-size:0.8rem; margin-top:0'>Tier 3 — Deep Intelligence</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "Navigate",
            [
                "\U0001F50D Drug Explorer",
                "\U0001F30D Opioid Landscape",
                "\U0001F5FA Geographic Intelligence",
                "\U000026A0 Signal Detection",
            ],
            label_visibility="collapsed",
        )

        st.divider()

        data = load_all_data()
        reg = data.get("registry")
        if reg:
            meta = reg.get("metadata", {})
            st.caption(f"Registry: {meta.get('total_opioid_rxcuis', '?')} RxCUIs")
        pharma = data.get("pharmacology")
        if pharma:
            meta = pharma.get("metadata", {})
            st.caption(f"Pharmacology: {meta.get('total_ingredients', '?')} ingredients")
        signals = data.get("signals")
        if signals:
            meta = signals.get("metadata", {})
            st.caption(f"Signals: {meta.get('total_consensus_signals', '?')} consensus")
        nlp = data.get("nlp_insights")
        if nlp:
            meta = nlp.get("metadata", {})
            st.caption(f"NLP: {meta.get('total_drugs_processed', '?')} labels mined")

        return page


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    page = render_sidebar()
    data = load_all_data()

    if "\U0001F50D" in page:
        from opioid_track.dashboard.pages.drug_explorer import render
        render(data)
    elif "\U0001F30D" in page:
        from opioid_track.dashboard.pages.landscape import render
        render(data)
    elif "\U0001F5FA" in page:
        from opioid_track.dashboard.pages.geography import render
        render(data)
    elif "\U000026A0" in page:
        from opioid_track.dashboard.pages.signals import render
        render(data)


if __name__ == "__main__":
    main()
