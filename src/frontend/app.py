"""
TruPharma GenAI Assistant  ·  Home
===================================
Landing page: navigate to Safety Chat or Opioid Intelligence Track.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
from src.frontend.theme import inject_theme, render_topbar

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="TruPharma | Clinical Intelligence",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_theme()
render_topbar("Home", badge_text="CLINICAL INTELLIGENCE")

# ─── Hero ─────────────────────────────────────────────────────
st.markdown(
    "<div class='landing-title'>TruPharma <span>Clinical Intelligence</span></div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='landing-subtitle'>"
    "AI-powered drug safety analysis &middot; FDA label evidence retrieval &middot; Knowledge graph reasoning"
    "</div>",
    unsafe_allow_html=True,
)

# ─── Navigation cards ────────────────────────────────────────
left, right = st.columns(2, gap="large")

with left:
    st.markdown(
        "<div class='nav-btn-block primary-demo'>"
        "<div style='font-size:1.4rem; margin-bottom:0.3rem;'>🧪</div>"
        "<div style='font-size:1.15rem; font-weight:800; margin-bottom:0.35rem; "
        "color:var(--teal-bright);'>Safety Chat</div>"
        "<div style='font-size:0.85rem; color:var(--text-secondary); font-weight:500;'>"
        "Drug-label RAG, knowledge graph, inline citations</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Open Safety Chat", key="nav_safety", use_container_width=True, type="primary"):
        st.switch_page("pages/primary_demo.py")

with right:
    st.markdown(
        "<div class='nav-btn-block opioid'>"
        "<div style='font-size:1.4rem; margin-bottom:0.3rem;'>📊</div>"
        "<div style='font-size:1.15rem; font-weight:800; margin-bottom:0.35rem; "
        "color:#fcd34d;'>Opioid Intelligence Track</div>"
        "<div style='font-size:0.85rem; color:var(--text-secondary); font-weight:500;'>"
        "Opioid pharmacology, demographics, epidemiology</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    if st.button("Open Opioid Track", key="nav_opioid", use_container_width=True, type="primary"):
        st.switch_page("pages/opioid_dashboard.py")
