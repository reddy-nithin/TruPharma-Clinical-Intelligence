"""
TruPharma GenAI Assistant  ·  Home
===================================
Auto-redirect to Safety Chat (the primary experience).
"""

import streamlit as st

# ─── Page config ────────
st.set_page_config(
    page_title="TruPharma | Clinical Intelligence",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.switch_page("pages/primary_demo.py")
