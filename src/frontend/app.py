"""
TruPharma GenAI Assistant  ·  Home
===================================
Landing page for TruPharma Clinical Intelligence platform.
"""

import streamlit as st
from theme import inject_theme

st.set_page_config(
    page_title="TruPharma | Clinical Intelligence",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_theme()

st.session_state["_reset_chat"] = True

st.markdown(
    "<div style='text-align:center; padding:6rem 2rem 2rem;'>"
    "<div class='landing-title'><span>Tru</span>Pharma</div>"
    "<div class='landing-subtitle'>AI-Powered Clinical Intelligence Platform</div>"
    "</div>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='nav-buttons'>",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    if st.button("🧪  Safety Chat — Drug Intelligence", use_container_width=True, type="primary"):
        st.switch_page("pages/primary_demo.py")
    st.caption("Conversational drug-safety RAG with citations, knowledge graph, and body mapping")

    if st.button("📊  Signal Heatmap — FAERS Explorer", use_container_width=True):
        st.switch_page("pages/signal_heatmap.py")
    st.caption("Disproportionality analysis across FDA adverse event reports")

    if st.button("💊  Opioid Dashboard", use_container_width=True):
        st.switch_page("pages/opioid_dashboard.py")
    st.caption("Focused opioid safety monitoring and signal detection")

    if st.button("⚡  Stress Test", use_container_width=True):
        st.switch_page("pages/stress_test.py")
    st.caption("Batch pipeline testing and performance benchmarks")

st.markdown("</div>", unsafe_allow_html=True)
