"""
TruPharma — Shared Design System (Clinical Intelligence Terminal)
=================================================================
Dark-theme CSS design system extracted from opioid_app.py.
Import `inject_theme()` / `render_topbar()` / `render_brand()` in every page.
"""

import streamlit as st
from datetime import datetime

# ---------------------------------------------------------------------------
# Design tokens + Global CSS
# ---------------------------------------------------------------------------
GLOBAL_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@300;400;500;600;700&display=swap');

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

    --font-data:   'Quicksand', sans-serif;
    --font-header: 'Quicksand', sans-serif;
    --font-body:   'Quicksand', sans-serif;

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
[data-testid="stSidebarNavLink"],
div[data-testid="stSidebarNav"],
section[data-testid="stSidebar"] nav,
section[data-testid="stSidebar"] ul[role="list"],
section[data-testid="stSidebar"] ul[data-testid="stSidebarNavItems"] {
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
html, body {
    font-family: var(--font-body) !important;
    color: var(--text-primary);
}

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

/* ── Hide / blend the Streamlit top toolbar ─────────────────────────────── */
header[data-testid="stHeader"],
.stAppHeader {
    background-color: transparent !important;
    background-image: none !important;
    border-bottom: none !important;
    box-shadow: none !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}

.block-container {
    padding-top: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 100% !important;
}

section[data-testid="stSidebar"] > div:first-child {
    padding-top: 0rem !important;
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

/* Shrink radio circles to invisible */
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
    overflow: visible !important;
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

/* ── Dark-themed content cards (used by Safety Chat, Stress Test, etc.) ── */
.card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: 14px 16px;
    box-shadow: var(--shadow-card);
    margin-bottom: 14px;
}

.card-title {
    font-weight: 800;
    font-size: 16px;
    margin-bottom: 8px;
    font-family: var(--font-header);
}
.card-title.response { color: var(--teal-bright); }
.card-title.evidence { color: var(--signal-warn); }
.card-title.metrics  { color: var(--signal-ok); }
.card-title.logs     { color: var(--text-secondary); }
.card.card-response  { border-left: 4px solid var(--teal-mid); }
.card.card-evidence  { border-left: 4px solid var(--signal-warn); }
.card.card-metrics   { border-left: 4px solid var(--signal-ok); }
.card.card-logs      { border-left: 4px solid var(--text-muted); }
.card.card-kg        { border-left: 4px solid #7c3aed; }
.card.card-bodymap   { border-left: 4px solid #7c3aed; }

/* KG pills */
.kg-pill {
    display: inline-block; padding: 5px 14px; margin: 3px 4px;
    border-radius: 20px; font-size: 13px; font-weight: 700;
    line-height: 1.4; font-family: var(--font-body);
}
.kg-pill.ingredient  { background: rgba(0,137,123,0.15); color: #5eead4; border: 1px solid rgba(0,137,123,0.3); }
.kg-pill.interaction { background: rgba(245,124,0,0.15); color: #fcd34d; border: 1px solid rgba(245,124,0,0.3); }
.kg-pill.co-reported { background: rgba(25,118,210,0.15); color: #93c5fd; border: 1px solid rgba(25,118,210,0.3); }
.kg-pill.reaction    { background: rgba(198,40,40,0.15); color: #fca5a5; border: 1px solid rgba(198,40,40,0.3); }

.kg-section-label {
    font-weight: 800; font-size: 14px; margin: 12px 0 6px 0;
    padding-bottom: 4px; border-bottom: 2px solid var(--border-default);
    color: #c4b5fd; font-family: var(--font-header);
}

.kg-summary-card {
    background: var(--bg-raised);
    border: 1px solid var(--border-default); border-radius: 12px;
    padding: 10px 14px; text-align: center;
}
.kg-summary-card .label { font-size: 11px; color: var(--text-label); font-weight: 700; text-transform: uppercase; }
.kg-summary-card .value { font-size: 18px; font-weight: 800; color: var(--text-primary); margin: 2px 0; }
.kg-summary-card .sub   { font-size: 11px; color: var(--text-muted); }

.kg-risk-badge {
    display: inline-block; padding: 3px 10px; border-radius: 8px;
    font-weight: 800; font-size: 13px;
}
.kg-risk-badge.low      { background: rgba(6,95,70,0.3); color: #86efac; }
.kg-risk-badge.moderate { background: rgba(146,64,14,0.3); color: #fcd34d; }
.kg-risk-badge.high     { background: rgba(153,27,27,0.3); color: #fca5a5; }

.bullets { margin: 0; padding-left: 18px; color: var(--text-secondary); }
.bullets li { margin: 6px 0; }

/* ── Scenario / panel styles (Stress Test, etc.) ────────────────────────── */
.scenario-card {
    padding: 10px 12px; border-radius: var(--radius-md);
    margin-bottom: 8px; font-weight: 700; line-height: 1.2;
}
.primary-active {
    background: rgba(61,245,200,0.08); border-left: 6px solid var(--teal-mid);
    color: var(--text-primary);
}
.stress-active {
    background: rgba(245,158,11,0.08); border-left: 6px solid var(--signal-warn);
    color: var(--text-primary);
}

.panel {
    border-radius: var(--radius-lg); padding: 0;
    border: 1px solid var(--border-default);
    overflow: hidden; box-shadow: var(--shadow-card);
    background: var(--bg-surface);
}
.panel-header {
    padding: 12px 18px; font-weight: 900; font-size: 18px;
    color: var(--text-primary); font-family: var(--font-header);
}
.panel-subheader {
    padding: 0 18px 12px 18px; font-weight: 700;
    color: var(--text-secondary);
}
.panel-header.primary {
    background: linear-gradient(90deg, rgba(61,245,200,0.12), rgba(61,245,200,0.04));
    border-radius: var(--radius-lg) !important;
    margin: 14px 14px 6px 14px !important;
    width: calc(100% - 28px) !important;
}
.panel-header.stress {
    background: linear-gradient(90deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04));
    border-radius: var(--radius-lg) !important;
    margin: 14px 14px 6px 14px !important;
    width: calc(100% - 28px) !important;
}

.section-pill {
    display: inline-block;
    background: var(--bg-raised);
    border: 1px solid var(--border-default);
    color: var(--text-primary);
    border-radius: 16px; padding: 8px 14px;
    font-weight: 900; font-size: 15px;
    margin: 10px 0 8px 0;
    font-family: var(--font-header);
}
.inner-card { margin: 10px 18px; border: none; background: transparent; padding: 0; }
.mini { color: var(--text-secondary); font-weight: 600; }

.criteria {
    border-radius: var(--radius-lg); border: 1px solid var(--border-default);
    overflow: hidden; box-shadow: var(--shadow-card);
    background: var(--bg-surface);
}
.criteria-header {
    padding: 10px 14px; font-weight: 900; font-size: 18px;
    color: var(--text-primary); font-family: var(--font-header);
}
.criteria-header.success {
    background: linear-gradient(90deg, rgba(61,245,200,0.12), rgba(61,245,200,0.04));
}
.criteria-header.pass {
    background: linear-gradient(90deg, rgba(245,158,11,0.12), rgba(245,158,11,0.04));
}
.criteria-body {
    padding: 12px 14px;
    background: var(--bg-raised);
    font-weight: 600;
    color: var(--text-secondary);
}

/* ── Main header bar ────────────────────────────────────────────────────── */
.main-header-bar {
    background: linear-gradient(90deg, var(--teal-dim), var(--teal-mid));
    color: var(--bg-void);
    padding: 12px 16px; border-radius: var(--radius-md);
    font-weight: 700; margin-bottom: 14px;
    font-family: var(--font-header);
    letter-spacing: 0.02em;
}

/* ── Landing page ───────────────────────────────────────────────────────── */
.landing-title {
    font-family: var(--font-header);
    font-size: 3.2rem;
    font-weight: 800;
    text-align: center;
    margin: 2rem 0 0.5rem 0;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.landing-title span {
    color: var(--teal-bright);
}

.landing-subtitle {
    font-family: var(--font-body);
    font-size: 1.25rem;
    color: var(--text-secondary);
    text-align: center;
    margin-bottom: 3rem;
    font-weight: 600;
}

.nav-buttons {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.25rem;
    max-width: 480px;
    margin: 0 auto;
}

.nav-btn-block {
    width: 100%;
    padding: 1.25rem 1.5rem;
    font-size: 1.1rem;
    font-weight: 700;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-default);
    background: var(--bg-surface);
    color: var(--text-primary);
    box-shadow: var(--shadow-card);
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
}

.nav-btn-block:hover {
    border-color: var(--teal-mid);
    box-shadow: var(--shadow-card), var(--shadow-glow);
    transform: translateY(-2px);
}

.nav-btn-block.primary-demo {
    border-left: 6px solid var(--teal-mid);
    background: linear-gradient(135deg, rgba(61,245,200,0.06) 0%, var(--bg-surface) 100%);
}

.nav-btn-block.heatmap {
    border-left: 6px solid #818cf8;
    background: linear-gradient(135deg, rgba(129,140,248,0.06) 0%, var(--bg-surface) 100%);
}

/* page-title / page-subtitle (Signal Heatmap, Stress Test, etc.) */
.page-title {
    font-family: var(--font-header);
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 4px;
    color: var(--text-primary);
}
.page-subtitle {
    color: var(--text-secondary);
    font-weight: 600;
    margin-bottom: 14px;
}

/* ── Pill link (used by Safety Chat header navigation) ──────────────────── */
.pill-link {
    flex: 1; text-align: center; padding: 14px;
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-default);
    background: var(--bg-surface);
    font-weight: 800;
    color: var(--text-primary);
    text-decoration: none !important;
    box-shadow: var(--shadow-card);
}

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
    width: 6px; height: 6px; border-radius: 50%;
    display: inline-block; margin-right: 6px; flex-shrink: 0;
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
    top: -0.6rem; left: 1rem;
    background: var(--bg-base);
    padding: 0 0.5rem;
    font-family: var(--font-data);
    font-size: 0.65rem; font-weight: 700;
    letter-spacing: 0.1em;
    color: var(--signal-high);
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
    font-size: 0.72rem !important; font-weight: 600 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
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
.stTextArea textarea {
    background: var(--bg-surface) !important;
    border-color: var(--border-default) !important;
    color: var(--text-primary) !important;
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
    padding: 4px !important; gap: 4px !important;
    border: 1px solid var(--border-subtle) !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-secondary) !important;
    font-family: var(--font-body) !important;
    font-size: 0.85rem !important; font-weight: 500 !important;
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
    font-size: 0.72rem !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: var(--text-label) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-family: var(--font-data) !important;
    font-size: 1.6rem !important;
    color: var(--text-primary) !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border-default) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
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

/* ── Sidebar brand block ─────────────────────────────────────────────────── */
.tp-brand {
    padding: 0.25rem 0 0.5rem 0;
}
.tp-brand-name {
    font-family: var(--font-header);
    font-size: 1.05rem; font-weight: 800;
    color: var(--teal-bright);
    letter-spacing: -0.01em; line-height: 1.2;
}
.tp-brand-tier {
    font-family: var(--font-data);
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* ── Subtle fade-in for page content ────────────────────────────────────── */
.block-container > div:first-child {
    animation: tp-fadein 0.3s ease both;
}
@keyframes tp-fadein {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Restore Material Icons ─────────────────────────────────────────────── */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
[data-testid="collapsedControl"] span,
span[class*="icon"] {
    font-family: "Material Symbols Rounded" !important;
}

/* ── Multiselect chips ──────────────────────────────────────────────────── */
[data-baseweb="tag"] {
    background: var(--bg-raised) !important;
    border-color: var(--border-default) !important;
    color: var(--text-primary) !important;
}

/* ── Number input ───────────────────────────────────────────────────────── */
.stNumberInput > div > div {
    background: var(--bg-surface) !important;
    border-color: var(--border-default) !important;
    color: var(--text-primary) !important;
}

/* ── Safety Chat Query Page ────────────────────────────────────────────── */
.query-page-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-lg);
    padding: 2rem 2.5rem;
    box-shadow: var(--shadow-card);
    max-width: 720px;
    margin: 1.5rem auto;
}

.query-page-title {
    font-family: var(--font-header);
    font-size: 1.6rem;
    font-weight: 800;
    color: var(--text-primary);
    margin-bottom: 0.25rem;
    letter-spacing: -0.02em;
}

.query-page-title span {
    color: var(--teal-bright);
}

.query-page-subtitle {
    font-family: var(--font-body);
    font-size: 0.95rem;
    color: var(--text-secondary);
    margin-bottom: 1.5rem;
    font-weight: 500;
}

/* ── Results Dashboard sidebar query block ─────────────────────────────── */
.results-sidebar-query {
    background: var(--bg-raised);
    border: 1px solid var(--border-default);
    border-left: 4px solid var(--teal-mid);
    border-radius: var(--radius-md);
    padding: 0.75rem 1rem;
    margin: 0.75rem 0;
    font-size: 0.85rem;
    color: var(--text-primary);
    line-height: 1.45;
    font-family: var(--font-body);
    word-wrap: break-word;
}

.results-sidebar-label {
    font-family: var(--font-data);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-label);
    margin-bottom: 0.4rem;
}
"""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def inject_theme():
    """Inject the global CSS design system into the current page."""
    st.markdown(f"<style>{GLOBAL_CSS}</style>", unsafe_allow_html=True)


def render_topbar(page_name: str, badge_text: str = "CLINICAL INTELLIGENCE"):
    """Render the top identity bar."""
    page_label = page_name.split(" ", 1)[-1] if " " in page_name else page_name
    st.markdown(
        f"<div class='tp-topbar'>"
        f"<span class='tp-topbar-title'>TruPharma &nbsp;&rsaquo;&nbsp; {page_label}</span>"
        f"<span class='tp-topbar-badge'>{badge_text}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_brand(title: str = "TruPharma", subtitle: str = "Clinical Intelligence"):
    """Render the sidebar brand block."""
    st.markdown(
        f"<div class='tp-brand'>"
        f"<div class='tp-brand-name'>{title}</div>"
        f"<div class='tp-brand-tier'>{subtitle}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )
