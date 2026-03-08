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
from datetime import datetime

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
# Design system — Clinical Intelligence Terminal aesthetic
# Fonts: JetBrains Mono (data), Syne (headers), DM Sans (body)
# ---------------------------------------------------------------------------
GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Syne:wght@600;700;800&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Design tokens ──────────────────────────────────────────────────────── */
:root {
    --bg-void:        #060d14;
    --bg-base:        #0b1622;
    --bg-surface:     #111e2e;
    --bg-raised:      #182840;
    --bg-hover:       #1e3450;

    --border-subtle:  #1a2f45;
    --border-default: #1f3d5a;
    --border-accent:  #2a5278;

    --text-primary:   #e8f0f8;
    --text-secondary: #7a9bbf;
    --text-muted:     #3d5a74;
    --text-label:     #5a8aaa;

    --teal-bright:    #3df5c8;
    --teal-mid:       #1ec9a0;
    --teal-dim:       #0e7a60;

    --signal-ok:      #22c55e;
    --signal-warn:    #f59e0b;
    --signal-high:    #ef4444;
    --signal-extreme: #dc2626;

    --font-data:   'JetBrains Mono', 'Courier New', monospace;
    --font-header: 'Syne', sans-serif;
    --font-body:   'DM Sans', sans-serif;

    --radius-sm:  6px;
    --radius-md:  10px;
    --radius-lg:  14px;

    --shadow-card: 0 2px 12px rgba(0,0,0,0.4), 0 0 0 1px rgba(61,245,200,0.04);
    --shadow-glow: 0 0 20px rgba(61,245,200,0.12);
    --shadow-danger: 0 0 16px rgba(239,68,68,0.2);
}

/* ── Hide Streamlit auto-generated page navigation ──────────────────────── */
section[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavLink"] {
    display: none !important;
}

/* ── Hide keyboard shortcut hints on radio/widget hover ─────────────────── */
[data-testid="stShortcutKeyContainer"],
kbd,
[class*="shortcutKey"],
[class*="ShortcutKey"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span[aria-hidden="true"] {
    display: none !important;
}

/* ── Base overrides ─────────────────────────────────────────────────────── */
/* NOTE: do NOT use [class*="css"] here — it overrides Material Icons font
   and causes icon ligatures (keyboard_double_arrow_down etc.) to render as text */
html, body {
    font-family: var(--font-body) !important;
    color: var(--text-primary);
}

/* Apply body font to text containers only — never span (breaks Material Icons ligatures) */
.stApp p, .stApp label, .stApp li, .stApp td, .stApp th {
    font-family: var(--font-body);
}

.stApp {
    background-color: var(--bg-void);
    background-image:
        radial-gradient(circle at 20% 20%, rgba(30,52,80,0.4) 0%, transparent 50%),
        radial-gradient(circle at 80% 80%, rgba(14,122,96,0.08) 0%, transparent 50%),
        url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Ccircle fill='%231a2f45' cx='20' cy='20' r='0.8'/%3E%3C/g%3E%3C/svg%3E");
}

.block-container {
    padding-top: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--bg-void) 0%, var(--bg-base) 60%, var(--bg-surface) 100%);
    border-right: 1px solid var(--border-subtle);
}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label {
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
}

section[data-testid="stSidebar"] hr {
    border-color: var(--border-subtle) !important;
    margin: 0.6rem 0 !important;
}

/* Sidebar radio buttons — styled as nav items */
section[data-testid="stSidebar"] .stRadio > div {
    gap: 2px;
}

section[data-testid="stSidebar"] .stRadio label {
    padding: 0.55rem 0.9rem !important;
    border-radius: var(--radius-sm) !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    cursor: pointer !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.01em !important;
    border: 1px solid transparent !important;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--bg-raised) !important;
    border-color: var(--border-default) !important;
}

section[data-testid="stSidebar"] .stRadio [data-checked="true"] label,
section[data-testid="stSidebar"] .stRadio input:checked + div {
    background: linear-gradient(90deg, rgba(61,245,200,0.08), rgba(61,245,200,0.03)) !important;
    border-color: var(--teal-dim) !important;
    color: var(--teal-bright) !important;
}

/* Shrink radio circles to invisible — keep input in DOM so clicks register */
section[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {
    width: 0 !important;
    height: 0 !important;
    min-width: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
    border: none !important;
}

/* ── Top identity bar ───────────────────────────────────────────────────── */
.tp-topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6rem 0 0.8rem 0;
    margin-bottom: 0.25rem;
    border-bottom: 1px solid var(--border-subtle);
}

.tp-topbar-title {
    font-family: var(--font-header);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--text-muted);
}

.tp-topbar-badge {
    font-family: var(--font-data);
    font-size: 0.65rem;
    color: var(--teal-mid);
    background: rgba(61,245,200,0.06);
    border: 1px solid rgba(61,245,200,0.15);
    border-radius: 4px;
    padding: 2px 8px;
    letter-spacing: 0.06em;
}

/* ── Page headers ───────────────────────────────────────────────────────── */
.tp-page-header {
    font-family: var(--font-header);
    font-size: 2rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    margin: 0.5rem 0 0.25rem 0;
    line-height: 1.1;
}

.tp-page-header span {
    color: var(--teal-bright);
}

.tp-section-header {
    font-family: var(--font-header);
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-label);
    margin: 2rem 0 0.75rem 0;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border-subtle);
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.tp-section-header::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 14px;
    background: var(--teal-bright);
    border-radius: 2px;
}

/* Legacy .section-header compatibility */
.section-header {
    font-family: var(--font-header) !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    padding-bottom: 0.4rem !important;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
}

/* ── Metric cards ───────────────────────────────────────────────────────── */
.metric-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
    box-shadow: var(--shadow-card);
}

.metric-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(61,245,200,0.2), transparent);
    opacity: 0;
    transition: opacity 0.2s ease;
}

.metric-card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-card), 0 0 0 1px rgba(61,245,200,0.06);
    transform: translateY(-1px);
}

.metric-card:hover::after {
    opacity: 1;
}

.metric-card h3 {
    font-family: var(--font-body) !important;
    color: var(--text-label) !important;
    margin: 0 0 0.4rem 0 !important;
    font-size: 0.72rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
}

.metric-card .value {
    font-family: var(--font-data) !important;
    color: var(--text-primary) !important;
    font-size: 1.7rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
    line-height: 1.1 !important;
}

/* Danger level variants */
.danger-high {
    border-left: 3px solid var(--signal-high) !important;
    background: linear-gradient(90deg, rgba(239,68,68,0.06) 0%, var(--bg-surface) 40%) !important;
}

.danger-high:hover {
    box-shadow: var(--shadow-card), var(--shadow-danger) !important;
}

.danger-high .value { color: #fca5a5 !important; }

.danger-moderate {
    border-left: 3px solid var(--signal-warn) !important;
    background: linear-gradient(90deg, rgba(245,158,11,0.06) 0%, var(--bg-surface) 40%) !important;
}

.danger-moderate .value { color: #fcd34d !important; }

.danger-low {
    border-left: 3px solid var(--signal-ok) !important;
    background: linear-gradient(90deg, rgba(34,197,94,0.05) 0%, var(--bg-surface) 40%) !important;
}

.danger-low .value { color: #86efac !important; }

/* ── Status badges (sidebar data sources) ───────────────────────────────── */
.tp-status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 0;
    font-size: 0.75rem;
}

.tp-status-label {
    color: var(--text-secondary);
    font-family: var(--font-body);
}

.tp-status-value {
    font-family: var(--font-data);
    font-size: 0.72rem;
    color: var(--teal-mid);
}

.tp-status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
    margin-right: 6px;
    flex-shrink: 0;
}

.tp-status-dot.ok   { background: var(--signal-ok); box-shadow: 0 0 4px var(--signal-ok); }
.tp-status-dot.miss { background: var(--signal-high); }

/* ── Boxed warning ──────────────────────────────────────────────────────── */
.tp-boxed-warning {
    border: 2px solid var(--signal-high);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    background: rgba(239,68,68,0.06);
    margin: 0.75rem 0;
    position: relative;
}

.tp-boxed-warning::before {
    content: 'BOXED WARNING';
    position: absolute;
    top: -0.6rem;
    left: 1rem;
    background: var(--bg-base);
    padding: 0 0.5rem;
    font-family: var(--font-data);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--signal-high);
}

/* ── Progress / lethal dose bar ─────────────────────────────────────────── */
.tp-dose-bar-wrap {
    background: var(--bg-raised);
    border-radius: var(--radius-sm);
    height: 20px;
    border: 1px solid var(--border-default);
    overflow: hidden;
    margin: 0.5rem 0;
}

.tp-dose-bar-fill {
    height: 100%;
    border-radius: var(--radius-sm) 0 0 var(--radius-sm);
    transition: width 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* ── Dataframe/table overrides ──────────────────────────────────────────── */
.stDataFrame {
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    overflow: hidden !important;
}

.stDataFrame thead th {
    background: var(--bg-raised) !important;
    color: var(--text-label) !important;
    font-family: var(--font-body) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border-default) !important;
}

.stDataFrame tbody tr:hover td {
    background: var(--bg-hover) !important;
}

/* ── Streamlit native component overrides ───────────────────────────────── */
.stSelectbox > div > div {
    background: var(--bg-surface) !important;
    border-color: var(--border-default) !important;
    font-family: var(--font-body) !important;
}

.stTextInput > div > div {
    background: var(--bg-surface) !important;
    border-color: var(--border-default) !important;
    font-family: var(--font-body) !important;
}

.stButton > button {
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--teal-dim), var(--teal-mid)) !important;
    border: none !important;
    color: var(--bg-void) !important;
    transition: box-shadow 0.2s ease !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: var(--shadow-glow) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--bg-surface) !important;
    border-radius: var(--radius-md) !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border-subtle) !important;
}

.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-secondary) !important;
    font-family: var(--font-body) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    transition: background 0.15s ease !important;
}

.stTabs [aria-selected="true"] {
    background: var(--bg-raised) !important;
    color: var(--teal-bright) !important;
}

/* Streamlit metric widget */
[data-testid="metric-container"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    padding: 0.8rem 1rem !important;
}

[data-testid="metric-container"] label {
    font-family: var(--font-body) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-label) !important;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--font-data) !important;
    font-size: 1.6rem !important;
    color: var(--text-primary) !important;
}

/* Info/warning/error boxes */
.stAlert {
    border-radius: var(--radius-md) !important;
    font-family: var(--font-body) !important;
}

/* Dividers */
hr {
    border-color: var(--border-subtle) !important;
    margin: 0.75rem 0 !important;
}

/* Captions */
.stCaption, [data-testid="stCaptionContainer"] {
    font-family: var(--font-body) !important;
    color: var(--text-muted) !important;
    font-size: 0.72rem !important;
}

/* Checkbox */
.stCheckbox label {
    font-family: var(--font-body) !important;
    font-size: 0.875rem !important;
}

/* Slider */
.stSlider {
    font-family: var(--font-body) !important;
}

/* ── Accessibility Layer — Tier 1: Inline Tooltips ──────────────────────── */
.tp-tooltip-wrap {
    position: relative;
    display: inline-block;
    cursor: help;
    border-bottom: 1px dashed var(--text-muted);
    padding-bottom: 1px;
}

.tp-tooltip-term {
    color: var(--teal-mid);
    font-family: var(--font-body);
    font-size: inherit;
}

.tp-tooltip-box {
    visibility: hidden;
    opacity: 0;
    width: 280px;
    background: var(--bg-raised);
    border: 1px solid var(--border-accent);
    border-radius: var(--radius-md);
    padding: 0.6rem 0.8rem;
    font-family: var(--font-body);
    font-size: 0.78rem;
    line-height: 1.55;
    color: var(--text-primary);
    position: absolute;
    z-index: 9999;
    bottom: 130%;
    left: 50%;
    transform: translateX(-50%);
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    transition: opacity 0.15s ease, visibility 0.15s ease;
    pointer-events: none;
    word-wrap: break-word;
}

.tp-tooltip-wrap:hover .tp-tooltip-box {
    visibility: visible;
    opacity: 1;
}

.metric-card { overflow: visible !important; }

/* ── Accessibility Layer — Tier 2: Chart Interpretation Captions ─────────── */
.tp-chart-caption {
    background: rgba(61,245,200,0.04);
    border-left: 3px solid var(--teal-dim);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    padding: 0.6rem 1rem;
    margin: 0.4rem 0 1.2rem 0;
    font-family: var(--font-body);
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.6;
}

.tp-chart-caption-icon {
    margin-right: 0.4rem;
    opacity: 0.7;
}

/* ── Accessibility Layer — Tier 3: Section Context Banners ───────────────── */
.tp-section-banner {
    font-family: var(--font-body);
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.65;
    padding: 0.25rem 0;
}

.tp-section-banner strong {
    color: var(--teal-mid);
    font-weight: 600;
}

/* ── Accessibility Layer — Tier 4: Sidebar Glossary ─────────────────────── */
.tp-glossary {
    max-height: 55vh;
    overflow-y: auto;
    padding-right: 4px;
    scrollbar-width: thin;
    scrollbar-color: var(--border-accent) transparent;
}

.tp-glossary-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border-subtle);
}

.tp-glossary-item:last-child { border-bottom: none; }

.tp-glossary-term {
    font-family: var(--font-body);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--teal-mid);
    letter-spacing: 0.02em;
    margin-bottom: 0.2rem;
}

.tp-glossary-def {
    font-family: var(--font-body);
    font-size: 0.71rem;
    color: var(--text-secondary);
    line-height: 1.5;
}

/* ── Subtle fade-in for page content ────────────────────────────────────── */
.block-container > div:first-child {
    animation: tp-fadein 0.3s ease both;
}

@keyframes tp-fadein {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Sidebar brand block ─────────────────────────────────────────────────── */
.tp-brand {
    padding: 0.25rem 0 0.5rem 0;
}

.tp-brand-name {
    font-family: var(--font-header);
    font-size: 1.05rem;
    font-weight: 800;
    color: var(--teal-bright);
    letter-spacing: -0.01em;
    line-height: 1.2;
}

.tp-brand-tier {
    font-family: var(--font-data);
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* ── Intelligence brief container ───────────────────────────────────────── */
.tp-brief {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: 1.5rem;
    margin: 1rem 0;
    line-height: 1.7;
}
"""

st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)


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
        "registry":    load_json_safe(config.REGISTRY_OUTPUT),
        "pharmacology":load_json_safe(config.PHARMACOLOGY_OUTPUT),
        "signals":     load_json_safe(config.SIGNAL_RESULTS_OUTPUT),
        "nlp_insights":load_json_safe(config.NLP_INSIGHTS_OUTPUT),
        "mortality":   load_json_safe(config.CDC_MORTALITY_OUTPUT),
        "prescribing": load_json_safe(config.CMS_PRESCRIBING_OUTPUT),
        "geographic":  load_json_safe(config.GEO_PROFILES_OUTPUT),
        "mme":         load_json_safe(config.MME_REFERENCE_OUTPUT),
    }


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
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

        reg_meta   = reg.get("metadata", {})    if reg    else {}
        pharma_meta= pharma.get("metadata", {}) if pharma else {}
        sig_meta   = sigs.get("metadata", {})   if sigs   else {}
        nlp_meta   = nlp.get("metadata", {})    if nlp    else {}

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


# ---------------------------------------------------------------------------
# Top identity bar (rendered once per page)
# ---------------------------------------------------------------------------
def render_topbar(page_name: str):
    page_label = page_name.split(" ", 1)[-1] if " " in page_name else page_name
    st.markdown(
        f"<div class='tp-topbar'>"
        f"<span class='tp-topbar-title'>TruPharma &nbsp;&rsaquo;&nbsp; {page_label}</span>"
        f"<span class='tp-topbar-badge'>TIER 3 &middot; OPIOID INTELLIGENCE</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
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
    elif "\U000026A0" in page:
        from opioid_track.dashboard.pages.signals import render
        render(data)
    elif "\U0001F6E1" in page:
        from opioid_track.dashboard.pages.watchdog import render
        render(data)


if __name__ == "__main__":
    main()
