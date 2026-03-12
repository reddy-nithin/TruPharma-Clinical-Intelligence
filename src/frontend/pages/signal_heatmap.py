"""
TruPharma  ·  Signal Heatmap Dashboard
=======================================
Analyst disparity and signal visualization.
"""

import sys
from pathlib import Path

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

from src.frontend.theme import inject_theme, render_topbar, render_brand

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Signal Heatmap | TruPharma",
    page_icon="📊",
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

# ─── Inject theme ────────────────────────────────────────────
inject_theme()


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    render_brand()
    st.divider()

if st.sidebar.button("⬅ Return to Home", key="go_home"):
    st.switch_page("app.py")

st.sidebar.caption("Analyst disparity and signal visualization.")


# ══════════════════════════════════════════════════════════════
#  MAIN CONTENT
# ══════════════════════════════════════════════════════════════
render_topbar("Signal Heatmap Dashboard")

st.markdown(
    "<div class='tp-page-header'>Signal Heatmap <span>Dashboard</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='main-header-bar'>TruPharma Signal Heatmap — Placeholder</div>",
    unsafe_allow_html=True,
)

st.info(
    "This page is a placeholder for the Signal Heatmap Dashboard. "
    "Connect your signal or disparity data and visualizations here."
)
