"""
TruPharma GenAI Assistant  ·  Home
===================================
Main landing page: navigate to Safety Chat or Signal Heatmap Dashboard.
"""

import sys
from pathlib import Path

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

from src.frontend.theme import inject_theme, render_topbar, render_brand

# ─── Page config (sidebar starts collapsed on homepage) ────────
st.set_page_config(
    page_title="TruPharma | Clinical Intelligence",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── Force-collapse sidebar on homepage even after navigation ─
components.html("""
<script>
(function() {
    const doc = window.parent.document;
    const sidebar = doc.querySelector('[data-testid="stSidebar"]');
    if (sidebar && sidebar.getAttribute('aria-expanded') !== 'false') {
        const btn = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
        if (btn) btn.click();
    }
})();
</script>
""", height=0)

# ─── Inject dark theme ───────────────────────────────────────
inject_theme()


# ══════════════════════════════════════════════════════════════
#  MAIN LANDING
# ══════════════════════════════════════════════════════════════
render_topbar("Home", badge_text="CLINICAL INTELLIGENCE")

st.markdown(
    "<div class='landing-title'><span>TruPharma</span> GenAI Assistant</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='landing-subtitle'>Clinical Intelligence · Drug Label Evidence RAG</div>",
    unsafe_allow_html=True,
)

# Two navigation buttons
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("<div class='nav-buttons'>", unsafe_allow_html=True)

    if st.button(
        "🟢 **Safety Chat**  \n*Drug-label questions, RAG answers, knowledge graph*",
        key="nav_safety_chat",
        use_container_width=True,
    ):
        st.switch_page("pages/primary_demo.py")

    if st.button(
        "📊 **Signal Heatmap Dashboard**  \n*Analyst disparity and signal visualization*",
        key="nav_heatmap",
        use_container_width=True,
    ):
        st.switch_page("pages/signal_heatmap.py")

    if st.button(
        "💊 **Opioid Intelligence Dashboard**  \n*Pharmacology, FAERS signals, epidemiology*",
        key="nav_opioid",
        use_container_width=True,
    ):
        st.switch_page("pages/opioid_dashboard.py")

    st.markdown("</div>", unsafe_allow_html=True)
