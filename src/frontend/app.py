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

# ─── Staggered fade-in animation ─────────────────────────────
st.markdown("""<style>
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}
.welcome-greeting {
    font-family: var(--font-header);
    font-size: 2.4rem;
    font-weight: 300;
    text-align: center;
    color: var(--text-secondary);
    margin: 3rem 0 1.5rem 0;
    letter-spacing: 0.02em;
    animation: fadeSlideIn 0.7s ease-out both;
}
.welcome-greeting span {
    color: var(--teal-bright);
    font-weight: 700;
}
.landing-title {
    animation: fadeSlideIn 0.7s ease-out 1.2s both;
}
.landing-subtitle {
    animation: fadeSlideIn 0.7s ease-out 1.4s both;
}
.landing-description {
    font-family: var(--font-body);
    font-size: 1rem;
    color: var(--text-secondary);
    text-align: center;
    max-width: 680px;
    margin: 0 auto 2.5rem auto;
    line-height: 1.7;
    font-weight: 500;
    animation: fadeSlideIn 0.7s ease-out 2.0s both;
}
.nav-card-wrapper {
    animation: fadeSlideIn 0.7s ease-out 2.8s both;
}
.nav-btn-block {
    text-align: center;
}
.select-prompt {
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--text-muted);
    text-align: center;
    margin-top: 2rem;
    letter-spacing: 0.04em;
    font-weight: 600;
    animation: fadeSlideIn 0.7s ease-out 3.2s both;
}
.nav-btn-block .card-desc {
    font-size: 0.82rem;
    color: var(--text-muted);
    font-weight: 500;
    line-height: 1.55;
    margin-top: 0.6rem;
    padding-top: 0.6rem;
    border-top: 1px solid var(--border-subtle);
}
</style>""", unsafe_allow_html=True)

# ─── Stage 1: Welcome greeting ───────────────────────────────
st.markdown(
    "<div class='welcome-greeting'>Welcome to <span>TruPharma</span></div>",
    unsafe_allow_html=True,
)

# ─── Stage 2: Title + subtitle ───────────────────────────────
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

# ─── Stage 3: App description ────────────────────────────────
st.markdown(
    "<div class='landing-description'>"
    "TruPharma Clinical Intelligence is an AI-powered platform for drug safety analysis. "
    "It retrieves FDA label evidence, reasons over a biomedical knowledge graph, and surfaces "
    "pharmacovigilance signals&mdash;helping analysts make faster, more informed safety decisions."
    "</div>",
    unsafe_allow_html=True,
)

# ─── Stage 4: Navigation cards ───────────────────────────────
st.markdown("""<style>
div[data-testid="stColumn"] .stButton > button[kind="secondary"] {
    background: transparent;
    border: 1px solid var(--teal-bright);
    color: var(--teal-bright);
    font-weight: 700;
    font-size: 0.85rem;
    padding: 0.5rem 1.5rem;
    border-radius: 8px;
    margin-top: 0.8rem;
    transition: background 0.2s, color 0.2s;
    cursor: pointer;
}
div[data-testid="stColumn"] .stButton > button[kind="secondary"]:hover {
    background: var(--teal-bright);
    color: #0d1117;
}
</style>""", unsafe_allow_html=True)

left, right = st.columns(2, gap="large")

with left:
    st.markdown(
        "<div class='nav-card-wrapper'>"
        "<div class='nav-btn-block primary-demo'>"
        "<div style='font-size:1.15rem; font-weight:800; margin-bottom:0.35rem; "
        "color:var(--teal-bright);'>Safety Chat</div>"
        "<div style='font-size:0.85rem; color:var(--text-secondary); font-weight:500;'>"
        "Drug-label RAG &middot; Knowledge graph &middot; Inline citations</div>"
        "<div class='card-desc'>"
        "Ask drug-safety questions and receive RAG-grounded answers with inline citations, "
        "knowledge graph context, and personalized risk assessment. Powered by FDA label "
        "evidence retrieval and biomedical reasoning."
        "</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Open Safety Chat", key="nav_safety", use_container_width=True):
        st.switch_page("pages/primary_demo.py")

with right:
    st.markdown(
        "<div class='nav-card-wrapper'>"
        "<div class='nav-btn-block opioid'>"
        "<div style='font-size:1.15rem; font-weight:800; margin-bottom:0.35rem; "
        "color:#fcd34d;'>Opioid Intelligence Track</div>"
        "<div style='font-size:0.85rem; color:var(--text-secondary); font-weight:500;'>"
        "Pharmacology &middot; Demographics &middot; Epidemiology</div>"
        "<div class='card-desc'>"
        "Explore opioid pharmacology, ingredient sensitivity rankings, demographic analysis, "
        "and epidemiological trends. Visualize scheduling data, adverse event signals, and "
        "population-level risk factors."
        "</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Open Opioid Dashboard", key="nav_opioid", use_container_width=True):
        st.switch_page("pages/opioid_dashboard.py")

# ─── Prompt to select ────────────────────────────────────────
st.markdown(
    "<div class='select-prompt'>Select a card above to get started</div>",
    unsafe_allow_html=True,
)
