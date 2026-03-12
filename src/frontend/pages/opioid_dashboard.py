"""
TruPharma  ·  Opioid Intelligence Dashboard
=============================================
Full opioid pharmacology, signals, and epidemiology — powered by
opioid_track Tier 3 pipeline.

This page integrates all opioid_track dashboard functionality into the
unified frontend without importing opioid_app.py (which has module-level
st.set_page_config that would conflict).
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

from opioid_track import config

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Opioid Intelligence | TruPharma",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Force-expand sidebar on subpages after navigation ───────
components.html("""
<script>
(function() {
    const doc = window.parent.document;
    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
    if (sidebar && sidebar.getAttribute('aria-expanded') === 'false') {
        const btn = doc.querySelector('[data-testid="collapsedControl"]');
        if (btn) btn.click();
    }
})();
</script>
""", height=0)


# ══════════════════════════════════════════════════════════════
#  DESIGN SYSTEM — inject the opioid_app.py CSS directly
# ══════════════════════════════════════════════════════════════
# Read the GLOBAL_CSS constant from the source file to avoid importing
# the module (which triggers st.set_page_config at module level).
_OPIOID_APP_PATH = _PROJECT_ROOT / "opioid_track" / "dashboard" / "opioid_app.py"
_src = _OPIOID_APP_PATH.read_text(encoding="utf-8")
_css_start = _src.index('GLOBAL_CSS = """') + len('GLOBAL_CSS = """')
_css_end = _src.index('"""', _css_start)
GLOBAL_CSS = _src[_css_start:_css_end]

st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  DATA LOADING (cached)
# ══════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def load_json_safe(path: str):
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
        "registry":     load_json_safe(config.REGISTRY_OUTPUT),
        "pharmacology": load_json_safe(config.PHARMACOLOGY_OUTPUT),
        "signals":      load_json_safe(config.SIGNAL_RESULTS_OUTPUT),
        "nlp_insights": load_json_safe(config.NLP_INSIGHTS_OUTPUT),
        "mortality":    load_json_safe(config.CDC_MORTALITY_OUTPUT),
        "prescribing":  load_json_safe(config.CMS_PRESCRIBING_OUTPUT),
        "geographic":   load_json_safe(config.GEO_PROFILES_OUTPUT),
        "mme":          load_json_safe(config.MME_REFERENCE_OUTPUT),
        "demographics": load_json_safe(config.DEMOGRAPHICS_OUTPUT),
    }


# ══════════════════════════════════════════════════════════════
#  SIDEBAR HELPERS
# ══════════════════════════════════════════════════════════════
def _status_row(label: str, value: str, loaded: bool) -> str:
    dot_cls = "ok" if loaded else "miss"
    return (
        f"<div class='tp-status-row'>"
        f"<span><span class='tp-status-dot {dot_cls}'></span>"
        f"<span class='tp-status-label'>{label}</span></span>"
        f"<span class='tp-status-value'>{value}</span>"
        f"</div>"
    )


def render_sidebar():
    with st.sidebar:
        # Home button (prominent, at the top)
        if st.button("⬅ Return to Home", key="opioid_go_home", use_container_width=True):
            st.switch_page("app.py")

        st.divider()

        # Brand block
        st.markdown(
            f"<div class='tp-brand'>"
            f"<div class='tp-brand-name'>{config.DASHBOARD_TITLE}</div>"
            f"<div class='tp-brand-tier'>Tier 3 &mdash; Deep Intelligence</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.divider()

        page = st.radio(
            "Navigate",
            [
                "\U0001F50D Drug Explorer",
                "\U0001F30D Opioid Landscape",
                "\U0001F5FA Geographic Intelligence",
                "\U0001F4CA Demographics",
                "\U000026A0 Signal Detection",
                "\U0001F6E1 Watchdog Tools",
            ],
            label_visibility="collapsed",
        )

        st.divider()

        # Data source status panel
        data = load_all_data()

        reg    = data.get("registry")
        pharma = data.get("pharmacology")
        sigs   = data.get("signals")
        nlp    = data.get("nlp_insights")
        geo    = data.get("geographic")
        demo   = data.get("demographics")

        reg_meta    = reg.get("metadata", {})    if reg    else {}
        pharma_meta = pharma.get("metadata", {}) if pharma else {}
        sig_meta    = sigs.get("metadata", {})   if sigs   else {}
        nlp_meta    = nlp.get("metadata", {})    if nlp    else {}

        rxcuis = reg_meta.get("total_opioid_rxcuis", "—") if reg else "—"
        ings   = pharma_meta.get("total_ingredients", "—") if pharma else "—"
        cons   = sig_meta.get("total_consensus_signals", "—") if sigs else "—"
        nlp_n  = nlp_meta.get("total_drugs_processed", "—") if nlp else "—"

        rows_html = (
            _status_row("Registry", f"{rxcuis} RxCUIs", bool(reg))
            + _status_row("Pharmacology", f"{ings} ingredients", bool(pharma))
            + _status_row("FAERS Signals", f"{cons} consensus", bool(sigs))
            + _status_row("NLP Labels", f"{nlp_n} drugs", bool(nlp))
            + _status_row("Geographic", "loaded" if geo else "missing", bool(geo))
            + _status_row("Demographics", "loaded" if demo else "missing", bool(demo))
        )

        st.markdown(
            f"<div style='font-family:var(--font-body); font-size:0.72rem; "
            f"font-weight:600; letter-spacing:0.08em; text-transform:uppercase; "
            f"color:var(--text-muted); margin-bottom:0.4rem;'>Data Sources</div>"
            + rows_html,
            unsafe_allow_html=True,
        )

        st.divider()

        # Glossary
        from opioid_track.dashboard.components.accessibility import render_sidebar_glossary
        render_sidebar_glossary()

        st.divider()

        # Footer: last refreshed
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        st.markdown(
            f"<div style='font-family:var(--font-data); font-size:0.62rem; "
            f"color:var(--text-muted); letter-spacing:0.04em;'>"
            f"Session: {now}</div>",
            unsafe_allow_html=True,
        )

        return page


# ══════════════════════════════════════════════════════════════
#  TOP IDENTITY BAR
# ══════════════════════════════════════════════════════════════
def render_topbar(page_name: str):
    page_label = page_name.split(" ", 1)[-1] if " " in page_name else page_name
    st.markdown(
        f"<div class='tp-topbar'>"
        f"<span class='tp-topbar-title'>TruPharma &nbsp;&rsaquo;&nbsp; {page_label}</span>"
        f"<span class='tp-topbar-badge'>TIER 3 &middot; OPIOID INTELLIGENCE</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════
#  MAIN — sidebar navigation → page dispatch
# ══════════════════════════════════════════════════════════════
page = render_sidebar()
data = load_all_data()

render_topbar(page)

if "\U0001F50D" in page:
    from opioid_track.dashboard.pages.drug_explorer import render
    render(data)
elif "\U0001F30D" in page:
    from opioid_track.dashboard.pages.landscape import render
    render(data)
elif "\U0001F5FA" in page:
    from opioid_track.dashboard.pages.geography import render
    render(data)
elif "\U0001F4CA" in page:
    from opioid_track.dashboard.pages.demographics import render
    render(data)
elif "\U000026A0" in page:
    from opioid_track.dashboard.pages.signals import render
    render(data)
elif "\U0001F6E1" in page:
    from opioid_track.dashboard.pages.watchdog import render
    render(data)
