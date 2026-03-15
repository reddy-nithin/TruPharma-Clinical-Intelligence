"""
TruPharma GenAI Assistant  ·  Safety Intelligence Chat
======================================================
Perplexity-style conversational drug-safety RAG with inline citations,
expandable evidence/KG/metrics panels, dark theme integration.
"""

import sys
from pathlib import Path

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime
import time
import base64
import math
import json as _json
import re

from src.rag.engine import run_rag_query, read_logs
from src.frontend.theme import inject_theme, render_topbar, render_brand

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Safety Chat | TruPharma RAG",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()


# ══════════════════════════════════════════════════════════════
#  CHAT-SPECIFIC CSS (extends theme.py dark tokens)
# ══════════════════════════════════════════════════════════════
st.markdown("""<style>
/* ── Citation superscripts ── */
.cite-pill {
    display: inline-flex; align-items: center; justify-content: center;
    background: rgba(14,122,96,0.25); color: var(--teal-bright, #3df5c8);
    font-size: 11px; font-weight: 700; min-width: 18px; height: 18px;
    padding: 0 5px; border-radius: 9px; margin: 0 1px;
    vertical-align: super; line-height: 1; cursor: default;
    border: 1px solid rgba(61,245,200,0.2);
}

/* ── Source type badges ── */
.source-badge {
    display: inline-block; padding: 3px 10px; margin: 2px 3px;
    border-radius: 12px; font-size: 11px; font-weight: 700;
    letter-spacing: 0.03em;
}
.source-badge.fda-label {
    background: rgba(25,118,210,0.15); color: #64b5f6;
    border: 1px solid rgba(25,118,210,0.3);
}
.source-badge.faers {
    background: rgba(198,40,40,0.15); color: #ef9a9a;
    border: 1px solid rgba(198,40,40,0.3);
}
.source-badge.kg {
    background: rgba(124,58,237,0.15); color: #c4b5fd;
    border: 1px solid rgba(124,58,237,0.3);
}

/* ── Disclaimer banner ── */
.disclaimer-banner {
    background: var(--bg-raised, #182840);
    border: 1px solid var(--signal-warn, #f59e0b);
    border-radius: var(--radius-md, 10px);
    padding: 8px 16px; font-size: 12px;
    color: var(--signal-warn, #f59e0b);
    margin-bottom: 16px; text-align: center;
    font-family: var(--font-body);
}

/* ── KG pills (dark theme) ── */
.kg-pill {
    display: inline-block; padding: 5px 14px; margin: 3px 4px;
    border-radius: 20px; font-size: 13px; font-weight: 700; line-height: 1.4;
}
.kg-pill.ingredient {
    background: rgba(0,137,123,0.15); color: #4db6ac;
    border: 1px solid rgba(0,137,123,0.3);
}
.kg-pill.interaction {
    background: rgba(245,124,0,0.15); color: #ffb74d;
    border: 1px solid rgba(245,124,0,0.3);
}
.kg-pill.co-reported {
    background: rgba(25,118,210,0.15); color: #64b5f6;
    border: 1px solid rgba(25,118,210,0.3);
}
.kg-pill.reaction {
    background: rgba(198,40,40,0.15); color: #ef9a9a;
    border: 1px solid rgba(198,40,40,0.3);
}
.kg-risk-badge {
    font-size: 10px; font-weight: 800; padding: 2px 8px;
    border-radius: 6px; text-transform: uppercase; margin-left: 4px;
}
.kg-risk-badge.severe {
    background: rgba(153,27,27,0.3); color: #fca5a5;
}
.kg-risk-badge.moderate {
    background: rgba(146,64,14,0.3); color: #fcd34d;
}
.kg-risk-badge.mild {
    background: rgba(6,95,70,0.3); color: #86efac;
}

/* ── Example query buttons ── */
.example-btn {
    display: block; width: 100%; padding: 8px 12px; margin: 4px 0;
    background: var(--bg-raised, #182840);
    border: 1px solid var(--border-subtle, #1a2f45);
    border-radius: var(--radius-sm, 6px);
    color: var(--text-secondary, #7a9bbf);
    font-size: 12px; text-align: left; cursor: pointer;
    font-family: var(--font-body); transition: all 0.15s;
}
.example-btn:hover {
    background: var(--bg-hover, #1e3450);
    border-color: var(--teal-dim, #0e7a60);
    color: var(--text-primary, #e8f0f8);
}

/* ── Evidence card styling ── */
.evidence-chunk {
    background: var(--bg-surface, #111e2e);
    border: 1px solid var(--border-subtle, #1a2f45);
    border-radius: var(--radius-sm, 6px);
    padding: 10px 14px; margin-bottom: 8px;
}
.evidence-chunk-header {
    display: flex; align-items: center; gap: 8px;
    margin-bottom: 6px; font-size: 13px; font-weight: 700;
    color: var(--text-primary, #e8f0f8);
}
.evidence-chunk-text {
    font-size: 12px; color: var(--text-secondary, #7a9bbf);
    line-height: 1.5; font-family: var(--font-body);
}

/* ── Chat area tweaks ── */
[data-testid="stChatMessage"] {
    background: var(--bg-surface, #111e2e) !important;
    border: 1px solid var(--border-subtle, #1a2f45) !important;
    border-radius: var(--radius-md, 10px) !important;
    margin-bottom: 12px !important;
    animation: msg-appear 0.3s ease both;
}
@keyframes msg-appear {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Enhanced chat input ── */
[data-testid="stChatInput"] textarea {
    border: 1px solid var(--border-subtle, #1a2f45) !important;
    background: var(--bg-surface, #111e2e) !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--teal-bright, #3df5c8) !important;
    box-shadow: none !important;
}

/* ── Welcome state ── */
.welcome-hero {
    text-align: center;
    padding: 48px 20px 32px;
    animation: msg-appear 0.5s ease both;
}
.welcome-title {
    font-size: 2.4rem;
    font-weight: 800;
    color: var(--text-primary, #e8f0f8);
    font-family: var(--font-heading, 'Quicksand', sans-serif);
    margin-bottom: 4px;
}
.welcome-title span {
    color: var(--teal-bright, #3df5c8);
}
.welcome-subtitle {
    font-size: 1.05rem;
    color: var(--text-secondary, #7a9bbf);
    font-family: var(--font-body);
    margin-bottom: 32px;
}
.trust-row {
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 36px;
}
.trust-card {
    background: var(--bg-raised, #182840);
    border: 1px solid var(--border-subtle, #1a2f45);
    border-radius: var(--radius-md, 10px);
    padding: 14px 20px;
    min-width: 150px;
    text-align: center;
}
.trust-card .trust-val {
    font-size: 1.15rem;
    font-weight: 800;
    color: var(--teal-bright, #3df5c8);
    font-family: var(--font-data, 'JetBrains Mono', monospace);
}
.trust-card .trust-label {
    font-size: 0.72rem;
    color: var(--text-secondary, #7a9bbf);
    font-family: var(--font-body);
    margin-top: 2px;
}
.example-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    max-width: 720px;
    margin: 0 auto 24px;
}
.example-card {
    background: var(--bg-surface, #111e2e);
    border: 1px solid var(--border-subtle, #1a2f45);
    border-radius: var(--radius-md, 10px);
    padding: 14px 16px;
    text-align: left;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: var(--font-body);
}
.example-card:hover {
    border-color: var(--teal-dim, #0e7a60);
    box-shadow: 0 0 12px rgba(61,245,200,0.08);
    transform: translateY(-1px);
}
.example-card .ec-icon {
    font-size: 1.2rem;
    margin-bottom: 4px;
}
.example-card .ec-query {
    font-size: 0.85rem;
    font-weight: 700;
    color: var(--text-primary, #e8f0f8);
    margin-bottom: 3px;
    line-height: 1.3;
}
.example-card .ec-desc {
    font-size: 0.72rem;
    color: var(--text-muted, #3d5a74);
    line-height: 1.3;
}
.welcome-prompt {
    text-align: center;
    color: var(--text-muted, #3d5a74);
    font-size: 0.82rem;
    font-family: var(--font-body);
    margin-top: 8px;
    animation: pulse-arrow 2s ease-in-out infinite;
}
@keyframes pulse-arrow {
    0%, 100% { opacity: 0.5; transform: translateY(0); }
    50%      { opacity: 1;   transform: translateY(4px); }
}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "kg_poll_count" not in st.session_state:
    st.session_state.kg_poll_count = 0
if "safety_view" not in st.session_state:
    st.session_state.safety_view = "query"
if "submitted_query" not in st.session_state:
    st.session_state.submitted_query = ""
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = ""

def set_panel(name: str):
    st.session_state.active_panel = (
        "ALL" if st.session_state.active_panel == name else name
    )


# ══════════════════════════════════════════════════════════════
#  EXAMPLE QUERIES
# ══════════════════════════════════════════════════════════════
EXAMPLES = [
    "What are the drug interactions for ibuprofen?",
    "Can I take aspirin with warfarin?",
    "What safety warnings exist for metformin?",
    "What are the side effects of omeprazole?",
    "Compare adverse reactions of ibuprofen and naproxen.",
    "What drugs are co-reported with prednisone in FAERS?",
]


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
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

with st.sidebar:
    render_brand()
    st.divider()

    if st.button("⬅ Return to Home", use_container_width=True):
        st.switch_page("app.py")

    st.divider()

    # New Chat / Clear
    col_new, col_clear = st.columns(2)
    with col_new:
        if st.button("+ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.active_detail = None
            st.rerun()
    with col_clear:
        if st.button("Clear All", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.divider()

    if st.button("⚠️ Stress Test", use_container_width=True):
        st.switch_page("pages/stress_test.py")

    st.divider()

    # Advanced settings
    with st.expander("Advanced Settings", expanded=False):
        method = st.selectbox("Retrieval method", ["hybrid", "dense", "sparse"], index=0)
        top_k = st.slider("Top-K evidence chunks", 3, 15, 5)

        # Auto-load Gemini key from secrets or environment
        _default_key = ""
        try:
            _default_key = st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
        if not _default_key:
            import os as _os
            _default_key = _os.environ.get("GEMINI_API_KEY", "") or _os.environ.get("GOOGLE_API_KEY", "")

        gemini_key = st.text_input("Gemini API key (optional)", type="password",
                                    value=st.session_state.get("_gemini_key", _default_key),
                                    help="Used for Gemini 2.5 Flash answer generation. Auto-loaded from secrets/environment if available.")
        if gemini_key:
            st.session_state["_gemini_key"] = gemini_key

    st.divider()



# Retrieve settings from sidebar (defaults if not set via expander)
if "method" not in dir():
    method = "hybrid"
if "top_k" not in dir():
    top_k = 5
if "gemini_key" not in dir():
    gemini_key = st.session_state.get("_gemini_key", "")


# ══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════

def _normalize_citations(answer: str, evidence: list) -> str:
    """Replace raw chunk-ID citations with [1], [2], ... superscript format."""
    for i, ev in enumerate(evidence, 1):
        raw_id = ev.get("_raw_id", "")
        if raw_id:
            answer = answer.replace(f"[{raw_id}]", f"[{i}]")
    # Convert [Evidence N] to [N]
    answer = re.sub(r"\[Evidence (\d+)\]", r"[\1]", answer)
    # Replace unknown bracket citations
    def _replace_unknown(m):
        inner = m.group(1)
        if re.match(r"\d+$", inner):
            return m.group(0)
        for j, ev in enumerate(evidence, 1):
            if ev.get("doc_id", "") in inner or ev.get("field", "") in inner:
                return f"[{j}]"
        return m.group(0)
    answer = re.sub(r"\[([^\]]+)\]", _replace_unknown, answer)
    return answer


def _citations_to_pills(answer: str, evidence: list = None) -> str:
    """Convert [N] references to styled HTML citation pills with hover excerpts."""
    def _pill(m):
        n = int(m.group(1))
        tooltip = ""
        if evidence and 0 < n <= len(evidence):
            excerpt = evidence[n-1].get("content", "")
            excerpt = excerpt.replace('"', '&quot;').replace("'", "&apos;")
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            source = evidence[n-1].get("field", "Source")
            tooltip = f" title='{source}: {excerpt}'"
        return f'<span class="cite-pill"{tooltip}>{n}</span>'
    return re.sub(r"\[(\d+)\]", _pill, answer)


def _get_source_badge(field: str) -> str:
    """Return an HTML source-type badge based on the evidence field name."""
    f = field.lower()
    if any(k in f for k in ("interaction", "warning", "precaution", "contraindication",
                             "dosage", "adverse", "boxed", "indication", "ingredient",
                             "overdosage", "label")):
        return "<span class='source-badge fda-label'>FDA Label</span>"
    elif any(k in f for k in ("faers", "signal", "report")):
        return "<span class='source-badge faers'>FAERS</span>"
    elif any(k in f for k in ("kg", "graph", "knowledge")):
        return "<span class='source-badge kg'>Knowledge Graph</span>"
    return "<span class='source-badge fda-label'>FDA Label</span>"


def _render_confidence_bar(evidence: list) -> str:
    """Render a stacked horizontal bar showing the breakdown of evidence sources."""
    if not evidence:
        return ""
    total = len(evidence)
    counts = {"blue": 0, "red": 0, "purple": 0}
    for ev in evidence:
        f = ev.get("field", "").lower()
        if any(k in f for k in ("faers", "signal", "report")):
            counts["red"] += 1
        elif any(k in f for k in ("kg", "graph", "knowledge")):
            counts["purple"] += 1
        else:
            counts["blue"] += 1
    n_blue, n_red, n_purple = counts["blue"], counts["red"], counts["purple"]
    html = "<div class='source-conf-bar'>"
    if n_blue:
        w = (n_blue / total) * 100
        html += f"<div class='conf-segment' style='width:{w:.1f}%; background:#3b82f6;' title='FDA Labels: {n_blue}'></div>"
    if n_red:
        w = (n_red / total) * 100
        html += f"<div class='conf-segment' style='width:{w:.1f}%; background:#ef4444;' title='FAERS Reports: {n_red}'></div>"
    if n_purple:
        w = (n_purple / total) * 100
        html += f"<div class='conf-segment' style='width:{w:.1f}%; background:#7c3aed;' title='Knowledge Graph: {n_purple}'></div>"
    html += "</div>"
    return html


def render_response():
    st.markdown(
        "<div class='card card-response'><div class='card-title response'>Response Panel</div>",
        unsafe_allow_html=True,
    )
    r = st.session_state.result
    if not r:
        st.info("Enter a drug-label question in the sidebar and click **Run RAG Query**.")
    else:
        meta_cols = st.columns([1, 1, 1])
        with meta_cols[0]:
            conf = r['confidence']
            conf_color = "#059669" if conf >= 0.7 else "#d97706" if conf >= 0.4 else "#dc2626"
            st.markdown(
                f"<div style='font-size:13px;'><b>Confidence:</b> "
                f"<span style='color:{conf_color};font-weight:800;'>{conf:.0%}</span></div>",
                unsafe_allow_html=True,
            )
        with meta_cols[1]:
            llm_label = "Gemini 2.0 Flash" if r["llm_used"] else "Extractive fallback"
            llm_icon = "🤖" if r["llm_used"] else "📄"
            st.markdown(f"<div style='font-size:13px;'>{llm_icon} <b>Generator:</b> {llm_label}</div>",
                        unsafe_allow_html=True)
        with meta_cols[2]:
            embed_label = "Medical BERT (PubMedBERT)" if r.get("method") else "TF-IDF"
            st.markdown(f"<div style='font-size:13px;'>🧬 <b>Embeddings:</b> {embed_label}</div>",
                        unsafe_allow_html=True)

        # Show Gemini error banner if the API key was provided but Gemini failed
        gemini_err = r.get("gemini_error")
        if gemini_err:
            st.markdown(
                f"<div style='padding:10px 14px;background:rgba(220,38,38,0.08);"
                f"border-left:4px solid #dc2626;border-radius:6px;"
                f"margin:8px 0;font-size:13px;color:#fca5a5;'>"
                f"⚠️ <b>Gemini API Failed:</b> {gemini_err}<br/>"
                f"<span style='color:#7a9bbf;font-size:12px;'>"
                f"Falling back to extractive summarization.</span></div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        display_answer = _normalize_citations(r["answer"], r.get("evidence", []))
        st.markdown(display_answer)
    st.markdown("</div>", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════
#  KG DATA ENRICHMENT
# ══════════════════════════════════════════════════════════════

def _enrich_kg_data(ingredients, interactions, co_reported, reactions):
    """Derive severity, importance, and summary metrics from raw KG data."""
    max_rxn = max((r.get("report_count", 0) for r in reactions), default=1) or 1
    enriched_rx = []
    for rx in reactions:
        cnt = rx.get("report_count", 0)
        pct = cnt / max_rxn
        sev = "severe" if pct > 0.66 else ("moderate" if pct > 0.33 else "mild")
        enriched_rx.append({**rx, "_severity": sev, "_pct": round(pct * 100, 1), "_importance": pct})

    enriched_ix = []
    for ix in interactions:
        desc = (ix.get("description") or "").lower()
        if any(w in desc for w in ("contraindicated", "severe", "fatal", "death", "serious")):
            sev = "severe"
        elif any(w in desc for w in ("caution", "monitor", "moderate", "avoid", "careful")):
            sev = "moderate"
        else:
            sev = "mild"
        enriched_ix.append({**ix, "_severity": sev})

    max_co = max((c.get("report_count", 0) for c in co_reported), default=1) or 1
    enriched_co = []
    for cr in co_reported:
        cnt = cr.get("report_count", 0)
        enriched_co.append({**cr, "_pct": round(cnt / max_co * 100, 1), "_importance": cnt / max_co})

    return {
        "ingredients": ingredients,
        "interactions": enriched_ix,
        "co_reported": enriched_co,
        "reactions": enriched_rx,
    }


# ══════════════════════════════════════════════════════════════
#  KG VISUALIZATION (vis.js — dark theme)
# ══════════════════════════════════════════════════════════════

def _build_kg_network_html(drug_name, ingredients, interactions, co_reported, reactions,
                           compact=False):
    """Build a decision-support KG visualization with vis.js in dark theme.

    When compact=True the layout is tuned for the narrow detail panel: smaller
    radius, shorter canvas, overlay-style detail card instead of a side drawer,
    and a streamlined toolbar.
    """
    nodes, edges, details_map = [], [], {}
    nid = 0
    RADIUS = 130 if compact else 210
    MAX_ITEMS = 6 if compact else 8

    center_font = 13 if compact else 16
    center_margin = {"top": 7, "bottom": 7, "left": 10, "right": 10} if compact else \
                    {"top": 10, "bottom": 10, "left": 14, "right": 14}

    # Center node
    center_id = nid
    nodes.append({
        "id": center_id, "label": drug_name.upper(),
        "x": 0, "y": 0, "fixed": {"x": True, "y": True},
        "color": {"background": "#7c3aed", "border": "#5b21b6",
                  "highlight": {"background": "#8b5cf6", "border": "#5b21b6"}},
        "font": {"color": "#fff", "size": center_font, "face": "Quicksand", "bold": True},
        "shape": "box", "borderWidth": 2,
        "margin": center_margin,
    })
    details_map[center_id] = {
        "name": drug_name.title(), "type_label": "Queried Drug", "color": "#7c3aed",
        "fields": [{"label": "Role", "value": "Central query subject"},
                    {"label": "Data sources", "value": "FDA labels, FAERS, openFDA"}],
    }

    # Category definitions (dark theme colors)
    categories = []
    if ingredients:
        categories.append(("ingredient", ingredients[:MAX_ITEMS],
                           "rgba(0,137,123,0.2)", "#00897b", "contains"))
    if interactions:
        categories.append(("interaction", interactions[:MAX_ITEMS],
                           "rgba(245,124,0,0.2)", "#f57c00", "interacts"))
    if co_reported:
        categories.append(("co_reported", co_reported[:MAX_ITEMS],
                           "rgba(25,118,210,0.2)", "#1976d2", "co-reported"))
    if reactions:
        categories.append(("reaction", reactions[:MAX_ITEMS],
                           "rgba(198,40,40,0.2)", "#c62828", "adverse rxn"))

    n_cat = len(categories)
    for ci, (cat, items, bg, border, edge_label) in enumerate(categories):
        sector_start = (2 * math.pi * ci / n_cat) - math.pi / 2
        sector_span = 2 * math.pi / n_cat
        n = len(items)
        for idx, item in enumerate(items):
            nid += 1
            angle = sector_start + sector_span * (idx + 1) / (n + 1)
            x = round(RADIUS * math.cos(angle))
            y = round(RADIUS * math.sin(angle))

            importance = item.get("_importance", 0.5)
            if compact:
                font_sz = round(9 + importance * 3)
                margin_v = round(4 + importance * 3)
                margin_h = round(6 + importance * 3)
                bw = round(1 + importance * 1.5, 1)
                edge_w = round(0.8 + importance * 1.5, 1)
            else:
                font_sz = round(11 + importance * 5)
                margin_v = round(6 + importance * 5)
                margin_h = round(10 + importance * 4)
                bw = round(1 + importance * 2, 1)
                edge_w = round(1.0 + importance * 2.5, 1)
            sev = item.get("_severity", "")
            dashes = (sev == "mild") if sev else False

            if cat == "ingredient":
                label = item["ingredient"]
                if item.get("strength") and not compact:
                    label += f"\n({item['strength']})"
                det_fields = [
                    {"label": "Dosage / Strength", "value": item.get("strength") or "See label"},
                    {"label": "Source", "value": "FDA drug label"},
                ]
            elif cat == "interaction":
                label = item["drug_name"]
                det_fields = [
                    {"label": "Clinical severity", "value": sev.title(), "badge": sev},
                    {"label": "Evidence", "value": "FDA label-derived"},
                ]
            elif cat == "co_reported":
                label = item["drug_name"]
                cnt = item.get("report_count", 0)
                det_fields = [
                    {"label": "Co-occurrence reports", "value": f"{cnt:,}"},
                    {"label": "Relative frequency", "value": f"{item.get('_pct', 0):.0f}%"},
                    {"label": "Source", "value": "FAERS"},
                ]
            else:
                label = item["reaction"]
                cnt = item.get("report_count", 0)
                det_fields = [
                    {"label": "Report count", "value": f"{cnt:,}"},
                    {"label": "Relative frequency", "value": f"{item.get('_pct', 0):.0f}%"},
                    {"label": "Severity", "value": sev.title(), "badge": sev},
                    {"label": "Source", "value": "FAERS"},
                ]

            nodes.append({
                "id": nid, "label": label, "x": x, "y": y,
                "color": {"background": bg, "border": border},
                "font": {"size": font_sz, "face": "Quicksand", "color": "#e8f0f8"},
                "shape": "box", "borderWidth": bw,
                "margin": {"top": margin_v, "bottom": margin_v,
                           "left": margin_h, "right": margin_h},
            })
            edge_font_sz = 8 if compact else 9
            edges.append({
                "id": f"e{nid}", "from": center_id, "to": nid,
                "label": edge_label, "width": edge_w,
                "font": {"size": edge_font_sz, "color": "#3d5a74"},
                "color": {"color": border},
                "dashes": dashes,
            })
            type_labels = {"ingredient": "Active Ingredient", "interaction": "Drug Interaction",
                           "co_reported": "Co-Reported Drug", "reaction": "Adverse Reaction"}
            details_map[nid] = {
                "name": label.replace("\n", " "), "type_label": type_labels[cat],
                "color": border, "fields": det_fields,
            }

    nj = _json.dumps(nodes)
    ej = _json.dumps(edges)
    dj = _json.dumps(details_map)

    # ── Layout parameters that differ between compact & full ──
    net_height = "320px" if compact else "470px"
    spring_len = 90 if compact else 145
    grav_const = -28 if compact else -38
    toolbar_pad = "4px 6px" if compact else "6px 8px"
    search_max_w = "140px" if compact else "220px"
    search_pad = "4px 8px" if compact else "5px 10px"
    search_fs = "11px" if compact else "12px"
    btn_pad = "4px 8px" if compact else "5px 11px"
    btn_fs = "10px" if compact else "11px"
    legend_gap = "8px" if compact else "14px"
    legend_fs = "10px" if compact else "11.5px"
    dot_sz = "9px" if compact else "11px"
    hint_max_w = "200px" if compact else "260px"
    hint_fs = "10.5px" if compact else "11.5px"

    # In compact mode the node-detail card is a centered overlay instead of a
    # side drawer, so it never steals horizontal space from the graph.
    if compact:
        detail_css = (
            "#kg-detail{position:absolute;left:50%;top:50%;width:88%;max-width:300px;"
            "max-height:60%;transform:translate(-50%,-50%) scale(0.92);opacity:0;"
            "background:rgba(17,30,46,.97);border:1px solid #2a5278;border-radius:10px;"
            "padding:12px 14px;overflow-y:auto;pointer-events:none;"
            "transition:transform .2s ease,opacity .2s ease;z-index:20;"
            "font-size:12px;color:#e8f0f8;box-shadow:0 8px 32px rgba(0,0,0,.45)}"
            "#kg-detail.visible{transform:translate(-50%,-50%) scale(1);opacity:1;"
            "pointer-events:auto}"
            "#kg-detail h3{margin:0 0 2px;font-size:13px}"
        )
    else:
        detail_css = (
            "#kg-detail{position:absolute;top:40px;right:0;width:260px;height:calc(100% - 40px);"
            "background:rgba(17,30,46,.97);border-left:2px solid #2a5278;"
            "padding:14px;overflow-y:auto;transform:translateX(100%);"
            "transition:transform .25s ease;z-index:20;font-size:13px;color:#e8f0f8}"
            "#kg-detail.visible{transform:translateX(0)}"
            "#kg-detail h3{margin:0 0 2px;font-size:15px}"
        )

    return f"""<html><head>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:0;background:transparent;font-family:"Quicksand",sans-serif}}
#kg-root{{position:relative;width:100%;overflow:hidden}}
#kg-toolbar{{display:flex;gap:{'4px' if compact else '6px'};align-items:center;padding:{toolbar_pad};
  background:#111e2e;border:1px solid #1f3d5a;border-radius:10px 10px 0 0}}
#kg-search{{flex:1;max-width:{search_max_w};padding:{search_pad};border:1px solid #1f3d5a;border-radius:7px;
  font-size:{search_fs};font-family:inherit;outline:none;background:#182840;color:#e8f0f8}}
#kg-search:focus{{border-color:#7c3aed;box-shadow:0 0 0 2px rgba(124,58,237,.15)}}
.tb-btn{{padding:{btn_pad};border:1px solid #1f3d5a;border-radius:7px;background:#182840;
  font-size:{btn_fs};font-weight:700;cursor:pointer;font-family:inherit;color:#7a9bbf;
  transition:background .12s,box-shadow .12s}}
.tb-btn:hover{{background:#1e3450;box-shadow:0 1px 4px rgba(0,0,0,.2)}}
.tb-btn.active{{background:rgba(124,58,237,0.15);border-color:#7c3aed;color:#c4b5fd}}
#kg-net{{width:100%;height:{net_height};border-left:1px solid #1f3d5a;border-right:1px solid #1f3d5a;
  background:#0b1622}}
{detail_css}
.det-type{{font-size:{'10px' if compact else '11px'};color:#7a9bbf;margin-bottom:{'8px' if compact else '10px'};padding-bottom:{'6px' if compact else '8px'};border-bottom:1px solid #1f3d5a}}
.det-row{{display:flex;justify-content:space-between;align-items:baseline;padding:{'4px' if compact else '5px'} 0;
  border-bottom:1px solid #1a2f45}}
.det-label{{font-size:{'10px' if compact else '11px'};color:#7a9bbf;font-weight:700;flex-shrink:0;margin-right:8px}}
.det-value{{font-size:{'11px' if compact else '12px'};color:#e8f0f8;text-align:right}}
.det-badge{{font-size:{'9px' if compact else '10px'};font-weight:800;padding:2px 8px;border-radius:6px;text-transform:uppercase}}
.det-badge.severe{{background:rgba(153,27,27,0.3);color:#fca5a5}}
.det-badge.moderate{{background:rgba(146,64,14,0.3);color:#fcd34d}}
.det-badge.mild{{background:rgba(6,95,70,0.3);color:#86efac}}
#kg-detail-close{{position:absolute;top:{'6px' if compact else '8px'};right:{'8px' if compact else '10px'};background:none;border:none;
  font-size:{'14px' if compact else '16px'};cursor:pointer;color:#3d5a74;font-family:inherit}}
#kg-detail-close:hover{{color:#e8f0f8}}
#kg-hint{{position:absolute;bottom:8px;left:8px;z-index:15;
  background:rgba(17,30,46,.95);border:1px solid #1f3d5a;border-radius:10px;
  padding:{'7px 10px' if compact else '9px 14px'};font-size:{hint_fs};color:#7a9bbf;line-height:1.45;
  box-shadow:0 2px 8px rgba(0,0,0,.2);max-width:{hint_max_w};transition:opacity .3s}}
#kg-hint b{{color:#e8f0f8}}
#kg-hint-close{{position:absolute;top:3px;right:7px;cursor:pointer;font-size:13px;
  color:#3d5a74;background:none;border:none;padding:0;font-family:inherit}}
#kg-hint-close:hover{{color:#e8f0f8}}
.legend{{display:flex;gap:{legend_gap};flex-wrap:wrap;padding:{'4px 6px' if compact else '6px 8px'};font-size:{legend_fs};
  background:#111e2e;border:1px solid #1f3d5a;border-radius:0 0 10px 10px;color:#7a9bbf}}
.legend span{{display:inline-flex;align-items:center;gap:{'3px' if compact else '4px'}}}
.dot{{width:{dot_sz};height:{dot_sz};border-radius:3px;display:inline-block}}
.legend .sep{{border-left:1px solid #1f3d5a;height:14px;margin:0 2px}}
.legend .dash-label{{color:#3d5a74;font-style:italic}}
</style></head><body>
<div id="kg-root">
  <div id="kg-toolbar">
    <input id="kg-search" placeholder="Search nodes..." autocomplete="off"
      title="Type to filter nodes by name"/>
    <button class="tb-btn" id="kg-focus-btn" title="Focus on selected node">Focus</button>
    <button class="tb-btn" id="kg-reset-btn" title="Reset graph">Reset</button>
    <button class="tb-btn" id="kg-fit-btn" title="Fit to view">Fit</button>
  </div>
  <div id="kg-net"></div>
  <div id="kg-detail">
    <button id="kg-detail-close">&times;</button>
    <div id="kg-detail-content"></div>
  </div>
  <div id="kg-hint">
    <button id="kg-hint-close">&times;</button>
    <b>Click a node</b> for clinical info.
    {'<br/>' if not compact else ' '}<b>Drag nodes</b> to rearrange.
  </div>
</div>
<div class="legend">
  <span><span class="dot" style="background:rgba(0,137,123,0.4);border:1px solid #00897b"></span> Ingredient</span>
  <span><span class="dot" style="background:rgba(245,124,0,0.4);border:1px solid #f57c00"></span> Interaction</span>
  <span><span class="dot" style="background:rgba(25,118,210,0.4);border:1px solid #1976d2"></span> Co-reported</span>
  <span><span class="dot" style="background:rgba(198,40,40,0.4);border:1px solid #c62828"></span> Adverse Rxn</span>
  {'<span class="sep"></span><span class="dash-label">Dashed = milder evidence</span>' if not compact else ''}
</div>
<script>
var nodesData={nj};
var edgesData={ej};
var detailsMap={dj};
var nodes=new vis.DataSet(nodesData);
var edges=new vis.DataSet(edgesData);
var container=document.getElementById("kg-net");
var network=new vis.Network(container,{{nodes:nodes,edges:edges}},{{
  physics:{{solver:"forceAtlas2Based",
    forceAtlas2Based:{{gravitationalConstant:{grav_const},centralGravity:0.006,
      springLength:{spring_len},springConstant:0.04,damping:0.45}},
    stabilization:{{iterations:160}}}},
  interaction:{{hover:true,tooltipDelay:120,zoomView:true,dragView:true}},
  edges:{{smooth:{{type:"cubicBezier",roundness:0.4}}}}
}});
var selectedNodeId=null;
var origN=JSON.stringify(nodesData);
var origE=JSON.stringify(edgesData);

network.once("stabilizationIterationsDone",function(){{
  network.fit({{animation:{{duration:400,easingFunction:"easeInOutQuad"}}}});
}});

function esc(s){{var d=document.createElement("div");d.textContent=s;return d.innerHTML}}
function showDetail(id){{
  var d=detailsMap[id];if(!d)return;
  var h='<h3 style="color:'+esc(d.color)+'">'+esc(d.name)+'</h3>';
  h+='<div class="det-type">'+esc(d.type_label)+'</div>';
  for(var i=0;i<d.fields.length;i++){{
    var f=d.fields[i];
    h+='<div class="det-row"><span class="det-label">'+esc(f.label)+'</span>';
    if(f.badge){{h+='<span class="det-badge '+f.badge+'">'+esc(f.value)+'</span>'}}
    else{{h+='<span class="det-value">'+esc(f.value)+'</span>'}}
    h+='</div>';
  }}
  document.getElementById("kg-detail-content").innerHTML=h;
  document.getElementById("kg-detail").classList.add("visible");
}}
function hideDetail(){{document.getElementById("kg-detail").classList.remove("visible")}}
network.on("click",function(p){{
  if(p.nodes.length>0){{selectedNodeId=p.nodes[0];showDetail(selectedNodeId)}}
  else{{hideDetail()}}
}});
document.getElementById("kg-detail-close").addEventListener("click",hideDetail);

document.getElementById("kg-search").addEventListener("input",function(){{
  var q=this.value.toLowerCase().trim();
  if(!q){{resetView();return}}
  var keep=[0];
  nodes.forEach(function(n){{if(n.label.toLowerCase().indexOf(q)!==-1)keep.push(n.id)}});
  if(keep.length>1)fadeExcept(keep);
}});

function fadeExcept(keepIds){{
  var nu=[],eu=[];
  nodes.forEach(function(n){{
    if(keepIds.indexOf(n.id)===-1)
      nu.push({{id:n.id,color:{{background:"#182840",border:"#1a2f45"}},
        font:{{color:"#3d5a74",size:10}}}});
  }});
  edges.forEach(function(e){{
    if(keepIds.indexOf(e.from)===-1||keepIds.indexOf(e.to)===-1)
      eu.push({{id:e.id,color:{{color:"#1a2f45"}},font:{{color:"#1a2f45"}}}});
  }});
  nodes.update(nu);edges.update(eu);
}}
document.getElementById("kg-focus-btn").addEventListener("click",function(){{
  if(selectedNodeId===null)return;
  var keep=network.getConnectedNodes(selectedNodeId);
  keep.push(selectedNodeId);keep.push(0);
  fadeExcept(keep);
  network.focus(selectedNodeId,{{scale:1.1,animation:{{duration:350}}}});
  this.classList.add("active");
}});

function resetView(){{
  nodes.clear();nodes.add(JSON.parse(origN));
  edges.clear();edges.add(JSON.parse(origE));
  selectedNodeId=null;hideDetail();
  document.getElementById("kg-search").value="";
  document.getElementById("kg-focus-btn").classList.remove("active");
  network.fit({{animation:{{duration:350}}}});
}}
document.getElementById("kg-reset-btn").addEventListener("click",resetView);

document.getElementById("kg-fit-btn").addEventListener("click",function(){{
  network.fit({{animation:{{duration:350,easingFunction:"easeInOutQuad"}}}});
}});

document.getElementById("kg-hint-close").addEventListener("click",function(){{
  var h=document.getElementById("kg-hint");h.style.opacity="0";
  setTimeout(function(){{h.style.display="none"}},300);
}});
</script></body></html>"""


# ══════════════════════════════════════════════════════════════
#  BODY-REGION HEATMAP
# ══════════════════════════════════════════════════════════════

_SYMPTOM_REGION_MAP: dict[str, str] = {}

_REGION_KEYWORDS: dict[str, list[str]] = {
    "head": [
        "headache", "migraine", "dizziness", "vertigo", "syncope", "tinnitus",
        "blurred vision", "vision", "visual", "eye", "ear", "hearing",
        "somnolence", "insomnia", "confusion", "seizure", "tremor",
        "anxiety", "depression", "hallucination", "amnesia", "coma",
        "cerebral", "encephalopathy", "meningitis", "stroke",
    ],
    "chest": [
        "chest pain", "palpitation", "tachycardia", "bradycardia", "arrhythmia",
        "dyspnoea", "dyspnea", "cough", "bronchospasm", "asthma",
        "pneumonia", "pulmonary", "respiratory", "cardiac", "myocardial",
        "heart", "angina", "hypertension", "hypotension", "oedema",
        "edema", "pleural", "wheezing",
    ],
    "abdomen": [
        "nausea", "vomiting", "diarrhoea", "diarrhea", "constipation",
        "abdominal", "stomach", "gastro", "gi ", "hepat", "liver",
        "pancreat", "intestin", "colitis", "dyspepsia", "flatulence",
        "rectal", "jaundice", "biliary", "spleen", "ascites",
    ],
    "arms": [
        "arm", "hand", "wrist", "elbow", "shoulder", "upper extremity",
        "carpal", "finger", "grip",
    ],
    "legs": [
        "leg", "foot", "feet", "ankle", "knee", "hip", "lower extremity",
        "gait", "claudication", "deep vein", "dvt", "toe",
    ],
    "skin": [
        "rash", "pruritus", "urticaria", "dermatitis", "erythema",
        "skin", "alopecia", "acne", "photosensitivity", "blister",
        "stevens-johnson", "toxic epidermal", "angioedema", "injection site",
        "swelling", "bruising", "petechiae", "purpura", "cellulitis",
    ],
    "systemic": [
        "fatigue", "fever", "pyrexia", "malaise", "weight", "anaphyla",
        "death", "multi-organ", "sepsis", "infection", "anaemia", "anemia",
        "thrombocytopenia", "leukopenia", "neutropenia", "lymph",
        "blood", "coagul", "haemorrhage", "hemorrhage", "pain",
        "arthralgia", "myalgia", "back pain", "muscle",
    ],
}

for _region, _kws in _REGION_KEYWORDS.items():
    for _kw in _kws:
        _SYMPTOM_REGION_MAP[_kw] = _region


def map_symptoms_to_regions(symptoms: list[str]) -> dict[str, int]:
    """Map symptom strings to body regions and return counts per region."""
    counts: dict[str, int] = {r: 0 for r in _REGION_KEYWORDS}
    counts["unknown"] = 0
    for sym in symptoms:
        low = sym.lower().strip()
        matched = False
        for kw, region in _SYMPTOM_REGION_MAP.items():
            if kw in low:
                counts[region] += 1
                matched = True
                break
        if not matched:
            counts["unknown"] += 1
    return counts


def _build_body_heatmap_html(region_counts: dict[str, int], symptoms: list[str]) -> str:
    """Return HTML with the human body image overlaid with radial gradient circles (dark theme)."""
    img_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "humanbody.jpg"
    img_b64 = base64.b64encode(img_path.read_bytes()).decode()

    body_max = max(
        (v for k, v in region_counts.items() if k not in ("unknown", "skin", "systemic")),
        default=1,
    ) or 1
    total = sum(region_counts.values())
    unknown = region_counts.get("unknown", 0)

    def _rgb(region: str) -> str | None:
        c = region_counts.get(region, 0)
        if c == 0:
            return None
        frac = c / body_max
        if frac > 0.66:
            return "220,38,38"
        elif frac > 0.33:
            return "245,158,11"
        return "59,130,246"

    def _size(region: str) -> int:
        c = region_counts.get(region, 0)
        if c == 0:
            return 0
        return 40 + int(40 * (c / body_max))

    region_positions: dict[str, list[dict[str, float]]] = {
        "head":    [{"x": 47.5, "y": 8.6}],
        "chest":   [{"x": 47.5, "y": 28.8}],
        "abdomen": [{"x": 47.5, "y": 44.2}],
        "arms":    [{"x": 17.5, "y": 34.0}, {"x": 77.3, "y": 34.0}],
        "legs":    [{"x": 39.0, "y": 68.0}, {"x": 57.7, "y": 68.0}],
    }

    circles: list[str] = []
    for region, positions in region_positions.items():
        rgb = _rgb(region)
        if not rgb:
            continue
        sz = _size(region)
        cnt = region_counts.get(region, 0)
        for i, pos in enumerate(positions):
            label = f"<span class='cnt'>{cnt}</span>" if i == 0 else ""
            circles.append(
                f"<div class='heat-dot' style='"
                f"left:{pos['x']}%;top:{pos['y']}%;"
                f"width:{sz}px;height:{sz}px;"
                f"background:radial-gradient(circle,"
                f"rgba({rgb},0.85) 0%,rgba({rgb},0.45) 30%,"
                f"rgba({rgb},0.15) 55%,transparent 72%);'>"
                f"{label}</div>"
            )
    circles_html = "\n    ".join(circles)

    skin_count = region_counts.get("skin", 0)
    skin_overlay = ""
    skin_legend = ""
    if skin_count > 0:
        sk_frac = skin_count / body_max
        sk_hex = "#dc2626" if sk_frac > 0.66 else "#f59e0b" if sk_frac > 0.33 else "#3b82f6"
        skin_overlay = (
            f"<div style='position:absolute;left:6%;top:1%;width:87%;height:96%;"
            f"border:2.5px dashed {sk_hex};border-radius:35%;opacity:0.55;"
            f"pointer-events:none;z-index:1'></div>"
        )
        skin_legend = f"<span>| Dashed = Skin ({skin_count})</span>"

    return f"""<html><head><style>
*{{box-sizing:border-box}}
body{{margin:0;padding:0;background:transparent;font-family:"Quicksand",sans-serif}}
.bm-wrap{{text-align:center;padding:4px 0}}
.bm-title{{font-size:13px;font-weight:800;color:#e8f0f8;margin-bottom:2px}}
.bm-sub{{font-size:11px;color:#7a9bbf;margin-bottom:6px}}
.body-ctr{{position:relative;display:inline-block;width:220px;overflow:hidden;cursor:zoom-in}}
.body-img{{display:block;width:192%;max-width:none;opacity:0.82}}
.heat-dot{{position:absolute;border-radius:50%;transform:translate(-50%,-50%);
  display:flex;align-items:center;justify-content:center;pointer-events:none;z-index:2}}
.cnt{{font-size:11px;font-weight:800;color:#fff;text-shadow:0 1px 4px rgba(0,0,0,0.6)}}
.zoom-hint{{position:absolute;bottom:6px;right:6px;font-size:9px;color:#7a9bbf;
  background:rgba(17,30,46,0.85);padding:2px 7px;border-radius:8px;z-index:3;
  display:flex;align-items:center;gap:3px;pointer-events:none}}
.legend{{display:flex;justify-content:center;gap:12px;margin-top:8px;font-size:10px;color:#7a9bbf}}
.legend span{{display:inline-flex;align-items:center;gap:3px}}
.ldot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
.how-to{{font-size:10px;color:#3d5a74;margin-top:6px;font-style:italic;line-height:1.4}}
#zoom-overlay{{display:none;position:fixed;inset:0;z-index:9999;
  background:rgba(0,0,0,0.82);flex-direction:column;
  align-items:center;justify-content:center;cursor:pointer;
  backdrop-filter:blur(6px)}}
#zoom-inner{{background:#111e2e;border-radius:14px;padding:16px 20px 12px;
  box-shadow:0 12px 48px rgba(0,0,0,0.45);position:relative;cursor:default;
  max-width:90vw;max-height:92vh;overflow:hidden;display:flex;flex-direction:column;align-items:center}}
#zoom-inner .body-ctr{{width:min(420px,38vh)!important;cursor:default;overflow:hidden}}
#zoom-inner .body-img{{opacity:1!important}}
#zoom-inner .zoom-hint{{display:none}}
#zoom-inner .cnt{{font-size:13px}}
.zoom-x{{position:absolute;top:10px;right:14px;width:32px;height:32px;border-radius:50%;
  background:rgba(255,255,255,0.08);border:none;cursor:pointer;display:flex;
  align-items:center;justify-content:center;font-size:20px;color:#7a9bbf;
  transition:background 0.2s,color 0.2s;z-index:10000}}
.zoom-x:hover{{background:rgba(255,255,255,0.16);color:#e8f0f8}}
</style></head><body>
<div class="bm-wrap">
  <div class="bm-title">Symptom Body Map</div>
  <div class="bm-sub">{total} symptom(s) mapped{f' &middot; {unknown} unclassified' if unknown else ''}</div>
  <div class="body-ctr" id="body-main">
    <img class="body-img" src="data:image/jpeg;base64,{img_b64}" alt="body outline"/>
    {skin_overlay}
    {circles_html}
    <div class="zoom-hint"><svg width="10" height="10" viewBox="0 0 24 24" fill="none"
      stroke="#7a9bbf" stroke-width="2.5"><circle cx="10" cy="10" r="7"/><line x1="15" y1="15" x2="21" y2="21"/></svg>
      Click to zoom</div>
  </div>
  <div class="legend">
    <span><span class="ldot" style="background:#3b82f6"></span> Low</span>
    <span><span class="ldot" style="background:#f59e0b"></span> Med</span>
    <span><span class="ldot" style="background:#dc2626"></span> High</span>
    {skin_legend}
  </div>
  <div class="how-to">Circles show affected areas &mdash; larger &amp; warmer colors mean more reported symptoms.<br/>
  Numbers indicate symptom count per region.</div>
</div>
<div id="zoom-overlay">
  <div id="zoom-inner">
    <button class="zoom-x" id="zoom-x-btn" title="Close">&times;</button>
    <div id="zoom-clone-slot"></div>
    <div class="legend" style="margin-top:12px">
      <span><span class="ldot" style="background:#3b82f6"></span> Low</span>
      <span><span class="ldot" style="background:#f59e0b"></span> Med</span>
      <span><span class="ldot" style="background:#dc2626"></span> High</span>
      {skin_legend}
    </div>
    <div class="how-to" style="margin-top:8px">Circles show affected areas &mdash; larger &amp; warmer colors mean more reported symptoms.<br/>
    Numbers indicate symptom count per region.</div>
  </div>
</div>
<script>
(function(){{
  var main=document.getElementById('body-main');
  var overlay=document.getElementById('zoom-overlay');
  var inner=document.getElementById('zoom-inner');
  var xBtn=document.getElementById('zoom-x-btn');
  var origFrameStyle='';
  function expandFrame(){{
    try{{
      var f=window.frameElement;
      if(f){{
        origFrameStyle=f.getAttribute('style')||'';
        f.style.position='fixed';
        f.style.inset='0';
        f.style.width='100vw';
        f.style.height='100vh';
        f.style.zIndex='9999';
        f.style.background='transparent';
      }}
    }}catch(e){{}}
  }}
  function restoreFrame(){{
    try{{
      var f=window.frameElement;
      if(f) f.setAttribute('style',origFrameStyle);
    }}catch(e){{}}
  }}
  var slot=document.getElementById('zoom-clone-slot');
  function openLightbox(){{
    expandFrame();
    var clone=main.cloneNode(true);
    clone.removeAttribute('id');
    slot.innerHTML='';
    slot.appendChild(clone);
    overlay.style.display='flex';
  }}
  function closeLightbox(){{
    overlay.style.display='none';
    slot.innerHTML='';
    restoreFrame();
  }}
  main.addEventListener('click',openLightbox);
  overlay.addEventListener('click',function(e){{
    if(e.target===overlay) closeLightbox();
  }});
  xBtn.addEventListener('click',function(e){{
    e.stopPropagation();
    closeLightbox();
  }});
  document.addEventListener('keydown',function(e){{
    if(e.key==='Escape'&&overlay.style.display==='flex') closeLightbox();
  }});
}})();
</script>
</body></html>"""


def _extract_symptoms_from_result(r: dict) -> list[str]:
    """Pull symptom strings from KG reactions + evidence field names."""
    symptoms = []
    for rx in r.get("kg_reactions", []):
        name = rx.get("reaction", "")
        if name:
            symptoms.append(name)
    return symptoms


# ══════════════════════════════════════════════════════════════
#  PERSONALIZED RISK CALCULATOR
# ══════════════════════════════════════════════════════════════

_COMORBIDITY_WEIGHTS = {
    "Liver disease (hepatic impairment)": 0.9,
    "Kidney disease (renal impairment)": 0.8,
    "Heart disease / cardiovascular": 0.7,
    "Pregnancy / nursing": 0.9,
    "Blood disorders (coagulopathy)": 0.7,
    "GI disorders (ulcers, bleeding)": 0.6,
    "Diabetes": 0.4,
    "Hypertension": 0.4,
    "Asthma / respiratory": 0.4,
    "Immunocompromised": 0.5,
}


def _compute_personalized_risk(age_group, comorbidities,
                                dosage, duration, concurrent_meds,
                                reactions, interactions):
    """Compute a personalized risk score from transparent, justified factors."""
    factors = []
    score = 1.0

    n_sev_ix = sum(1 for ix in interactions if ix.get("_severity") == "severe")
    n_mod_ix = sum(1 for ix in interactions if ix.get("_severity") == "moderate")
    n_sev_rx = sum(1 for rx in reactions if rx.get("_severity") == "severe")
    n_mod_rx = sum(1 for rx in reactions if rx.get("_severity") == "moderate")

    if n_sev_ix:
        v = round(n_sev_ix * 0.8, 1)
        names = ", ".join(ix["drug_name"] for ix in interactions
                          if ix.get("_severity") == "severe")[:80]
        factors.append((f"{n_sev_ix} severe interaction(s)", v,
                         f"FDA labels flag contraindications or serious risk with: {names}"))
        score += v
    if n_mod_ix:
        v = round(n_mod_ix * 0.3, 1)
        factors.append((f"{n_mod_ix} moderate interaction(s)", v,
                         "These interactions require monitoring or dose adjustment"))
        score += v
    if n_sev_rx:
        v = round(n_sev_rx * 0.5, 1)
        names = ", ".join(rx["reaction"] for rx in reactions
                          if rx.get("_severity") == "severe")[:80]
        factors.append((f"{n_sev_rx} high-frequency reaction(s)", v,
                         f"FAERS data shows frequent reports of: {names}"))
        score += v
    if n_mod_rx:
        v = round(n_mod_rx * 0.15, 1)
        factors.append((f"{n_mod_rx} moderate-frequency reaction(s)", v,
                         "These adverse events appear at moderate rates in FAERS"))
        score += v

    age_mult = {"Pediatric (<18)": 0.6, "Adult (18–64)": 0.0, "Elderly (65+)": 0.8}
    age_add = age_mult.get(age_group, 0.0)
    if age_add:
        just = ("Pediatric patients have immature hepatic/renal metabolism"
                if "Pediatric" in age_group else
                "Elderly patients have reduced clearance and higher sensitivity")
        factors.append((f"Age — {age_group}", age_add, just))
        score += age_add

    _COMORB_JUST = {
        "Liver disease (hepatic impairment)":
            "Most drugs are hepatically metabolized; impairment raises plasma levels and toxicity",
        "Kidney disease (renal impairment)":
            "Reduced renal clearance prolongs drug half-life and increases adverse-event risk",
        "Heart disease / cardiovascular":
            "Cardiovascular conditions can be exacerbated by vasoconstrictive or QT-prolonging agents",
        "Pregnancy / nursing":
            "Many drugs cross the placental barrier; FDA pregnancy categories must be reviewed",
        "Blood disorders (coagulopathy)":
            "Anticoagulant or antiplatelet interactions can cause life-threatening bleeding",
        "GI disorders (ulcers, bleeding)":
            "GI-irritant drugs (NSAIDs, corticosteroids) sharply increase perforation/bleeding risk",
        "Diabetes":
            "Some drugs alter glucose metabolism or interact with hypoglycemics",
        "Hypertension":
            "Risk of additive or antagonistic effects with antihypertensives",
        "Asthma / respiratory":
            "Beta-blockers and certain agents can trigger bronchospasm",
        "Immunocompromised":
            "Reduced immune surveillance may amplify infection-related adverse events",
    }
    for cond in comorbidities:
        w = _COMORBIDITY_WEIGHTS.get(cond, 0.3)
        factors.append((cond, w, _COMORB_JUST.get(cond, "Condition may alter drug safety profile")))
        score += w

    d_add = {"Low": -0.3, "Standard": 0.0, "High": 0.6}.get(dosage, 0.0)
    if d_add:
        just = ("Lower dose reduces exposure and adverse-event probability" if d_add < 0
                else "Higher dose increases systemic exposure and toxicity risk")
        factors.append((f"Dosage — {dosage}", d_add, just))
        score += d_add

    dur_add = {"Short-term (<2 wk)": 0.0, "Long-term (2–12 wk)": 0.4,
               "Chronic (>12 wk)": 0.7}.get(duration, 0.0)
    if dur_add:
        factors.append((f"Duration — {duration}", dur_add,
                         "Prolonged exposure increases cumulative organ toxicity and "
                         "the likelihood of delayed adverse reactions"))
        score += dur_add

    if concurrent_meds > 0:
        med_add = round(min(1.5, concurrent_meds * 0.35), 1)
        factors.append((f"{concurrent_meds} concurrent medication(s)", med_add,
                         "Each additional drug increases the chance of pharmacokinetic "
                         "or pharmacodynamic interactions"))
        score += med_add

    score = min(10.0, max(0.0, round(score, 1)))

    warnings = []
    sev_ix = [ix for ix in interactions if ix.get("_severity") == "severe"]
    sev_rx = [rx for rx in reactions if rx.get("_severity") == "severe"]

    if any("Liver" in c for c in comorbidities):
        warnings.append("Pre-existing liver disease increases hepatotoxicity risk. "
                         "Monitor liver enzymes regularly.")
    if any("Kidney" in c for c in comorbidities):
        warnings.append("Renal impairment may reduce drug clearance. "
                         "Consider dose adjustment and monitor renal function.")
    if any("Pregnancy" in c for c in comorbidities):
        warnings.append("Verify FDA pregnancy category. Many drugs are "
                         "contraindicated or require risk-benefit assessment.")
    if any("Blood" in c for c in comorbidities) and sev_ix:
        warnings.append("Coagulopathy combined with severe drug interactions "
                         "increases bleeding risk.")
    if age_group == "Elderly (65+)":
        warnings.append("Elderly patients may need dose reduction due to "
                         "altered pharmacokinetics and polypharmacy risk.")
    if concurrent_meds >= 3:
        warnings.append(f"{concurrent_meds} concurrent medications significantly "
                         "increase the probability of drug-drug interactions.")
    if sev_ix:
        names = ", ".join(ix["drug_name"] for ix in sev_ix[:3])
        warnings.append(f"Severe interaction(s) flagged with: {names}. "
                         "Review before co-prescribing.")
    if sev_rx:
        names = ", ".join(rx["reaction"] for rx in sev_rx[:3])
        warnings.append(f"High-frequency adverse reaction(s): {names}.")

    if not warnings:
        warnings.append("No elevated-risk factors detected for this profile.")

    return score, factors, warnings


def _build_risk_gauge_html(score):
    """Return an HTML/SVG semicircle gauge for the personalized risk score (dark theme)."""
    frac = score / 10.0
    arc_len = 251.3
    fill = round(frac * arc_len, 1)
    if score >= 7:
        color, label = "#dc2626", "HIGH RISK"
    elif score >= 4:
        color, label = "#d97706", "MODERATE"
    else:
        color, label = "#059669", "LOW RISK"
    return f"""
    <div style="text-align:center;padding:8px 0">
      <svg viewBox="0 0 200 115" width="220" height="130">
        <path d="M 20 100 A 80 80 0 0 1 180 100"
              stroke="#1a2f45" stroke-width="16" fill="none" stroke-linecap="round"/>
        <path d="M 20 100 A 80 80 0 0 1 180 100"
              stroke="{color}" stroke-width="16" fill="none" stroke-linecap="round"
              stroke-dasharray="{fill} {arc_len}"
              style="transition:stroke-dasharray .6s ease"/>
        <text x="100" y="80" text-anchor="middle"
              font-size="28" font-weight="800" fill="{color}"
              font-family="Quicksand,sans-serif">{score:.1f}</text>
        <text x="100" y="98" text-anchor="middle"
              font-size="11" fill="#7a9bbf"
              font-family="Quicksand,sans-serif">{label}</text>
      </svg>
    </div>"""


def _parse_reference_dose(ingredients):
    """Extract a numeric dose + unit from the first ingredient strength for the dosage bar."""
    import re as _re
    for ing in ingredients:
        s = ing.get("strength", "")
        m = _re.match(r"([\d.]+)\s*([A-Za-z/%]+)", s)
        if m:
            return float(m.group(1)), m.group(2), ing["ingredient"]
    return None, None, None


def _build_dosage_bar_html(dose_val, dose_unit, ingredient, selected_level):
    """HTML bar showing Low / Standard / High dose ranges (dark theme)."""
    if dose_val is None:
        return ""
    low = round(dose_val * 0.5, 1)
    std = round(dose_val, 1)
    high = round(dose_val * 2, 1)

    def _fmt(v):
        return f"{v:g}"

    sel_colors = {"Low": ("#059669", 0), "Standard": ("#d97706", 1), "High": ("#dc2626", 2)}
    sel_color, sel_idx = sel_colors.get(selected_level, ("#d97706", 1))

    segments = [
        (f"Low\n≤ {_fmt(low)} {dose_unit}", "rgba(5,150,105,0.12)", "#059669", 0),
        (f"Standard\n~{_fmt(std)} {dose_unit}", "rgba(217,119,6,0.12)", "#d97706", 1),
        (f"High\n≥ {_fmt(high)} {dose_unit}", "rgba(220,38,38,0.12)", "#dc2626", 2),
    ]
    bar_html = (
        f"<div style='margin:8px 0 4px;font-size:11px;color:#7a9bbf'>"
        f"Dosage reference for <b style=\"color:#e8f0f8\">{ingredient}</b> ({_fmt(std)} {dose_unit} labeled strength)</div>"
        f"<div style='display:flex;gap:3px;margin-bottom:6px'>"
    )
    for label, bg, border, idx in segments:
        active = idx == sel_idx
        weight = "800" if active else "600"
        bdr = f"3px solid {border}" if active else f"1px solid {border}40"
        opacity = "1" if active else "0.55"
        parts = label.split("\n")
        bar_html += (
            f"<div style='flex:1;text-align:center;padding:8px 4px;border-radius:8px;"
            f"background:{bg};border:{bdr};opacity:{opacity};line-height:1.35'>"
            f"<div style='font-weight:{weight};font-size:12px;color:{border}'>{parts[0]}</div>"
            f"<div style='font-size:11px;color:#7a9bbf'>{parts[1]}</div></div>"
        )
    bar_html += "</div>"
    return bar_html


def _render_risk_calculator(enriched, drug_name):
    """Render the personalized risk assessment panel (dark theme)."""
    st.markdown(
        f"<div style='border:2px solid #2a5278;border-radius:10px;padding:16px;margin-bottom:8px'>"
        f"<div style='color:#7c3aed;font-size:16px;font-weight:800;margin-bottom:12px;'>"
        f"Personalized Risk Assessment — {drug_name.title()}</div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1.2], gap="large")

    with left:
        st.markdown("##### Patient Context")
        age_group = st.selectbox(
            "Age group",
            ["Adult (18–64)", "Pediatric (<18)", "Elderly (65+)"],
            key="risk_age",
        )
        comorbidities = st.multiselect(
            "Comorbidities & conditions",
            list(_COMORBIDITY_WEIGHTS.keys()),
            key="risk_comorb",
        )
        rc1, rc2 = st.columns(2)
        with rc1:
            dosage = st.selectbox("Dosage level", ["Standard", "Low", "High"],
                                   key="risk_dosage")
        with rc2:
            duration = st.selectbox("Duration",
                                     ["Short-term (<2 wk)", "Long-term (2–12 wk)",
                                      "Chronic (>12 wk)"],
                                     key="risk_duration")

        dose_val, dose_unit, dose_ing = _parse_reference_dose(enriched["ingredients"])
        dose_bar = _build_dosage_bar_html(dose_val, dose_unit, dose_ing, dosage)
        if dose_bar:
            st.markdown(dose_bar, unsafe_allow_html=True)

        concurrent_meds = st.number_input(
            "Concurrent medications", 0, 20, 0, key="risk_meds",
            help="Number of other drugs the patient is currently taking",
        )

    p_score, factors, warns = _compute_personalized_risk(
        age_group, comorbidities, dosage, duration, concurrent_meds,
        enriched["reactions"], enriched["interactions"],
    )

    with right:
        st.markdown("##### Risk Score")
        st.markdown(_build_risk_gauge_html(p_score), unsafe_allow_html=True)

        st.markdown("**Factor Breakdown**")
        for label, val, justification in factors:
            sign = "+" if val > 0 else ""
            bar_w = min(100, max(4, abs(val) / 2 * 100))
            bar_color = "#dc2626" if val > 0.5 else ("#d97706" if val > 0 else "#059669")
            st.markdown(
                f"<div style='margin:5px 0 1px'>"
                f"<div style='display:flex;align-items:center;gap:8px;font-size:12px'>"
                f"<span style='flex:1;color:#e8f0f8;font-weight:700'>{label}</span>"
                f"<span style='width:50px;text-align:right;font-weight:800;"
                f"color:{bar_color}'>{sign}{val}</span>"
                f"<div style='width:70px;height:6px;background:#1a2f45;border-radius:3px'>"
                f"<div style='width:{bar_w}%;height:100%;background:{bar_color};"
                f"border-radius:3px'></div></div></div>"
                f"<div style='font-size:11px;color:#5a8aaa;margin:1px 0 0 4px;'>"
                f"{justification}</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("##### Contextual Warnings")
    for w in warns:
        icon = "&#9888;" if "risk" in w.lower() or "severe" in w.lower() else "&#9432;"
        st.markdown(
            f"<div style='padding:6px 10px;margin:4px 0;background:rgba(245,158,11,0.08);"
            f"border-left:4px solid #d97706;border-radius:6px;font-size:13px;color:#e8f0f8'>"
            f"{icon}&nbsp; {w}</div>",
            unsafe_allow_html=True,
        )

    st.caption("This assessment uses a heuristic model for exploratory purposes — "
               "not a substitute for clinical judgment. Factor weights are illustrative, "
               "not derived from validated pharmacological models.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_kg():
    st.markdown(
        "<div class='card card-kg'><div class='card-title' style='color:#7c3aed;'>"
        "Knowledge Graph — Decision Support</div>",
        unsafe_allow_html=True,
    )
    r = st.session_state.result
    if not r:
        st.info("Run a query to see Knowledge Graph data.")
    elif not r.get("kg_available", False):
        st.warning("Knowledge Graph not available. "
                   "Build it with: `python3 scripts/build_kg.py`")
    else:
        # ── Dynamic build banners ──────────────────────────────
        is_dynamic = r.get("kg_dynamic", False)
        build_status = r.get("kg_build_status", "")
        phase1_time = r.get("kg_build_phase1_time", 0)

        if is_dynamic:
            if build_status in ("PHASE1_COMPLETE", "PHASE2_RUNNING"):
                st.markdown(
                    "<div style='padding:10px 14px;background:rgba(37,99,235,0.08);"
                    "border-left:4px solid #2563eb;border-radius:6px;"
                    "margin-bottom:12px;font-size:14px;'>"
                    "🔄 <b>Building full drug profile...</b> "
                    f"Basic data shown below (loaded in {phase1_time:.1f}s). "
                    "Full data (interactions, co-reported drugs) will appear automatically."
                    "</div>",
                    unsafe_allow_html=True,
                )
                # Auto-poll: rerun up to 5 times every 5 seconds
                if st.session_state.kg_poll_count < 5:
                    st.session_state.kg_poll_count += 1
                    time.sleep(5)
                    st.rerun()
            elif build_status == "PHASE2_COMPLETE":
                st.session_state.kg_poll_count = 0  # reset counter
                st.markdown(
                    "<div style='padding:10px 14px;background:rgba(5,150,105,0.08);"
                    "border-left:4px solid #059669;border-radius:6px;"
                    "margin-bottom:12px;font-size:14px;'>"
                    "✅ <b>Full drug profile built!</b> "
                    "This drug was dynamically added to the Knowledge Graph. "
                    "All data panels are now fully populated."
                    "</div>",
                    unsafe_allow_html=True,
                )
        raw_ix = r.get("kg_interactions", [])
        raw_co = r.get("kg_co_reported", [])
        raw_rx = r.get("kg_reactions", [])
        raw_ing = r.get("kg_ingredients", [])

        # ── Ingredient-only match ──
        ing_match = r.get("kg_ingredient_match")
        if ing_match:
            ing_name = ing_match["ingredient"].title()
            drugs = ing_match["drugs"]
            st.markdown(
                f"<div style='margin-bottom:0.75rem;padding:0.6rem 1rem;"
                f"background:rgba(202,138,4,0.08);border-left:4px solid #ca8a04;border-radius:6px;'>"
                f"<span style='font-size:1.05rem;color:#fcd34d'><b>{ing_name}</b> is an "
                f"<b>ingredient</b>, not a standalone drug in the Knowledge Graph.</span><br/>"
                f"<span style='color:#7a9bbf;font-size:0.88rem;'>"
                f"Found in {len(drugs)} drug(s):</span></div>",
                unsafe_allow_html=True,
            )
            for d in drugs[:8]:
                brand_preview = ", ".join(d.get("brand_names", [])[:3]) or "—"
                strength = f" ({d['strength']})" if d.get("strength") else ""
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;**{d['generic_name'].title()}**{strength}"
                    f" — *{brand_preview}*"
                )
            if len(drugs) > 8:
                st.caption(f"  ...and {len(drugs) - 8} more")
            st.markdown("</div>", unsafe_allow_html=True)
            return

        if not (raw_ix or raw_co or raw_rx or raw_ing):
            st.info("This drug is not in the Knowledge Graph seed list. "
                    "Try a more common drug, or rebuild with a larger seed.")
        else:
            # ── Partial KG Data badge ──
            if is_dynamic and build_status in ("PHASE1_COMPLETE", "PHASE2_RUNNING"):
                st.markdown(
                    f"<div style='display:inline-block;padding:3px 12px;"
                    "background:rgba(245,158,11,0.12);border:1px solid #f59e0b;"
                    "border-radius:20px;font-size:12px;font-weight:700;"
                    "color:#fcd34d;margin-bottom:10px;'>"
                    "⏳ Partial KG Data</div>",
                    unsafe_allow_html=True,
                )
            # ── Drug identity subheading ──
            kg_id = r.get("kg_identity") or {}
            queried_name = r.get("drug_name", "")
            generic = kg_id.get("generic_name", "")
            brands = kg_id.get("brand_names", [])
            brand_str = ", ".join(brands[:5]) if brands else "—"
            if generic:
                resolved_line = f"<b>{generic.title()}</b>"
                if queried_name.lower() != generic.lower():
                    resolved_line = f"<b>{generic.title()}</b> (searched: <i>{queried_name}</i>)"
                st.markdown(
                    f"<div style='margin-bottom:0.75rem;padding:0.6rem 1rem;"
                    f"background:rgba(124,58,237,0.08);border-left:4px solid #7c3aed;border-radius:6px;'>"
                    f"<span style='font-size:1.05rem;color:#c4b5fd'>{resolved_line}</span><br/>"
                    f"<span style='color:#7a9bbf;font-size:0.88rem;'>"
                    f"Brand names: {brand_str}"
                    f"{'&hellip;' if len(brands) > 5 else ''}</span></div>",
                    unsafe_allow_html=True,
                )

            enriched = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)
            ingredients = enriched["ingredients"]
            interactions = enriched["interactions"]
            co_reported = enriched["co_reported"]
            reactions = enriched["reactions"]

            # ── Summary insight panel ──
            s1, s2, s3, s4 = st.columns(4)
            mcr = enriched["most_common_rxn"]
            msi = enriched["most_severe_ix"]

            with s1:
                st.markdown(
                    "<div class='kg-summary-card'><div class='label'>Most Common Reaction</div>"
                    f"<div class='value'>{mcr['reaction'] if mcr else '—'}</div>"
                    f"<div class='sub'>{mcr.get('report_count', 0):,} reports</div></div>"
                    if mcr else
                    "<div class='kg-summary-card'><div class='label'>Most Common Reaction</div>"
                    "<div class='value'>—</div><div class='sub'>No data</div></div>",
                    unsafe_allow_html=True)
            with s2:
                st.markdown(
                    "<div class='kg-summary-card'><div class='label'>Most Severe Interaction</div>"
                    f"<div class='value'>{msi['drug_name'] if msi else '—'}</div>"
                    f"<div class='sub'>"
                    f"<span class='kg-risk-badge {msi['_severity']}'>{msi['_severity']}</span>"
                    f"</div></div>"
                    if msi else
                    "<div class='kg-summary-card'><div class='label'>Most Severe Interaction</div>"
                    "<div class='value'>—</div><div class='sub'>No data</div></div>",
                    unsafe_allow_html=True)
            with s3:
                total_rels = len(interactions) + len(co_reported) + len(reactions) + len(ingredients)
                st.markdown(
                    "<div class='kg-summary-card'><div class='label'>Total Relationships</div>"
                    f"<div class='value'>{total_rels}</div>"
                    f"<div class='sub'>{len(interactions)} interactions · "
                    f"{len(reactions)} reactions</div></div>",
                    unsafe_allow_html=True)
            with s4:
                st.markdown(
                    "<div class='kg-summary-card' style='cursor:pointer'>"
                    "<div class='label'>Personalized Assessment</div>"
                    "<div class='value' style='font-size:15px;color:#7c3aed'>Analyze My Risk</div>"
                    "<div class='sub'>Based on your patient context</div></div>",
                    unsafe_allow_html=True)
                def _toggle_risk():
                    st.session_state["show_risk_calc"] = not st.session_state.get("show_risk_calc", False)

                _risk_open = st.session_state.get("show_risk_calc", False)
                _risk_label = "Close Assessment" if _risk_open else "Open Assessment"
                _risk_type = "secondary" if _risk_open else "primary"
                st.button(_risk_label, key="kg_risk_toggle",
                          use_container_width=True, type=_risk_type,
                          on_click=_toggle_risk)

            # ── Personalized risk calculator (shown on toggle) ──
            if st.session_state.get("show_risk_calc", False):
                drug_name_for_calc = r.get("drug_name") or "Drug"
                _render_risk_calculator(enriched, drug_name_for_calc)

            # ── Filter controls ──
            with st.expander("Filters", expanded=False):
                fc1, fc2, fc3 = st.columns([2, 1.5, 1.5])
                with fc1:
                    show_cats = st.multiselect(
                        "Show categories",
                        ["Ingredients", "Interactions", "Co-reported", "Adverse Reactions"],
                        default=["Ingredients", "Interactions", "Co-reported", "Adverse Reactions"],
                        key="kg_cats",
                    )
                with fc2:
                    sev_filter = st.multiselect(
                        "Severity",
                        ["mild", "moderate", "severe"],
                        default=["mild", "moderate", "severe"],
                        key="kg_sev",
                    )
                with fc3:
                    all_counts = (
                        [rx.get("report_count", 0) for rx in reactions]
                        + [cr.get("report_count", 0) for cr in co_reported]
                    )
                    max_count = max(all_counts) if all_counts else 0
                    freq_thresh = st.slider(
                        "Min reports", 0, max(max_count, 1), 0, key="kg_freq",
                    ) if max_count > 0 else 0

            # Apply filters
            f_ing = ingredients if "Ingredients" in show_cats else []
            f_ix = [ix for ix in interactions
                    if "Interactions" in show_cats and ix.get("_severity", "mild") in sev_filter]
            f_co = [cr for cr in co_reported
                    if "Co-reported" in show_cats and cr.get("report_count", 0) >= freq_thresh]
            f_rx = [rx for rx in reactions
                    if "Adverse Reactions" in show_cats
                    and rx.get("_severity", "mild") in sev_filter
                    and rx.get("report_count", 0) >= freq_thresh]

            # ── Interactive network visualization ──
            drug_name = r.get("drug_name") or ""
            if not drug_name:
                import re as _re
                _stop = {"what","are","the","is","of","for","a","an","in","on","to",
                         "and","or","how","does","do","can","side","effects","warnings",
                         "interactions","dosage","dose","drug","about","with","tell","me",
                         "information","safety","adverse","reactions","risk","taking","take",
                         "should","i","my","it","its","this","that"}
                _toks = _re.findall(r"[a-zA-Z0-9\-]+", query_text or "")
                _cands = [t for t in _toks if t.lower() not in _stop and len(t) > 2]
                drug_name = _cands[0] if _cands else "Drug"
            html = _build_kg_network_html(drug_name, f_ing, f_ix, f_co, f_rx)
            components.html(html, height=560, scrolling=False)

            # ── Tabbed detail sections ──
            tab_labels, tab_data = [], []
            if f_ing:
                tab_labels.append(f"Ingredients ({len(f_ing)})")
                tab_data.append(("ing", f_ing))
            if f_ix:
                tab_labels.append(f"Interactions ({len(f_ix)})")
                tab_data.append(("ix", f_ix))
            if f_co:
                tab_labels.append(f"Co-Reported ({len(f_co)})")
                tab_data.append(("co", f_co))
            if f_rx:
                tab_labels.append(f"Adverse Reactions ({len(f_rx)})")
                tab_data.append(("rx", f_rx))

            if tab_labels:
                tabs = st.tabs(tab_labels)
                _tab_desc = {
                    "ing": "Active and inactive ingredients listed on the drug label, with strengths where available.",
                    "ix":  "Known drug-drug interactions sourced from FDA labels, ranked by severity.",
                    "co":  "Drugs most frequently reported alongside this one in FDA adverse-event reports (FAERS).",
                    "rx":  "Adverse reactions reported to the FDA, ranked by frequency in the FAERS database.",
                }
                for ti, (kind, items) in enumerate(tab_data):
                    with tabs[ti]:
                        st.caption(_tab_desc[kind])
                        if kind == "ing":
                            pills = "".join(
                                f"<span class='kg-pill ingredient'>{i['ingredient']}"
                                f"{(' · ' + i['strength']) if i.get('strength') else ''}</span>"
                                for i in items)
                            st.markdown(pills, unsafe_allow_html=True)
                        elif kind == "ix":
                            for ix in items[:10]:
                                sev = ix.get("_severity", "mild")
                                desc = ix.get("description", "")
                                s = (desc[:120] + "...") if len(desc) > 120 else desc
                                st.markdown(
                                    f"<span class='kg-pill interaction'>{ix['drug_name']}</span> "
                                    f"<span class='kg-risk-badge {sev}'>{sev}</span>"
                                    + (f"&nbsp; {s}" if s else ""),
                                    unsafe_allow_html=True)
                        elif kind == "co":
                            import pandas as pd
                            df = pd.DataFrame([
                                {"Drug": c["drug_name"], "Reports": c.get("report_count", 0)}
                                for c in items[:10]
                            ]).sort_values("Reports", ascending=True)
                            st.bar_chart(df, x="Drug", y="Reports", horizontal=True, color="#1976d2")
                        else:
                            import pandas as pd
                            df = pd.DataFrame([
                                {"Reaction": rx["reaction"], "Reports": rx.get("report_count", 0),
                                 "Severity": rx.get("_severity", "—").title()}
                                for rx in items[:10]
                            ]).sort_values("Reports", ascending=True)
                            st.bar_chart(df, x="Reaction", y="Reports", horizontal=True, color="#c62828")

    st.markdown("</div>", unsafe_allow_html=True)


def render_metrics():
    st.markdown(
        "<div class='card card-metrics'><div class='card-title metrics'>Metrics & Monitoring</div>",
        unsafe_allow_html=True,
    )
    r = st.session_state.result
    if r:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latency", f"{r['latency_ms']:.0f} ms")
        m2.metric("Evidence Ct.", len(r["evidence"]))
        m3.metric("Confidence", f"{r['confidence']:.0%}")
        m4.metric("Records Fetched", r["num_records"])

        enriched_n = r.get("graph_enriched_chunks", 0)
        total_n = r.get("total_chunks", 0)
        if enriched_n > 0:
            st.markdown(
                f"<div style='padding:8px 12px;margin:8px 0;background:rgba(22,163,106,0.08);"
                f"border-left:4px solid #16a34a;border-radius:6px;font-size:13px;color:#86efac'>"
                f"<b>Graph Enrichment Active</b> — "
                f"{enriched_n}/{total_n} chunks enriched with KG context "
                f"(interactions, reactions, ingredients, FAERS signals)</div>",
                unsafe_allow_html=True,
            )
        elif r.get("kg_available"):
            st.markdown(
                f"<div style='padding:8px 12px;margin:8px 0;background:rgba(202,138,4,0.08);"
                f"border-left:4px solid #ca8a04;border-radius:6px;font-size:13px;color:#fcd34d'>"
                f"<b>Graph Enrichment</b> — KG available but no chunks matched "
                f"graph data for this drug</div>",
                unsafe_allow_html=True,
            )

        st.markdown(f"- **Retrieval method:** {r['method']}")
        st.markdown(f"- **Embedding model:** Medical BERT (PubMedBERT via S-PubMedBert-MS-MARCO)")
        st.markdown(f"- **LLM used:** {'Gemini 2.0 Flash' if r['llm_used'] else 'Extractive fallback'}")
        st.markdown(f"- **openFDA search:** `{r['search_query'][:120]}`")
        gemini_err = r.get("gemini_error")
        if gemini_err:
            st.markdown(f"- **Gemini Error:** {gemini_err}")
        else:
            st.markdown(f"- **Errors / Fallbacks:** None")
    else:
        st.info("Run a query to see metrics.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_logs():
    st.markdown(
        "<div class='card card-logs'><div class='card-title logs'>Logs</div>",
        unsafe_allow_html=True,
    )

    # Session logs (in-memory)
    st.markdown("**Session Log**")
    if not st.session_state.logs:
        st.write("No queries run yet this session.")
    else:
        for line in reversed(st.session_state.logs[-10:]):
            st.write(line)

    # CSV log (persistent)
    st.markdown("---")
    st.markdown("**Product Metrics CSV** (`logs/product_metrics.csv`)")
    csv_rows = read_logs(last_n=10)
    if csv_rows:
        import pandas as pd
        df = pd.DataFrame(csv_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.write("No CSV log entries yet.")

    st.markdown("</div>", unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
#  BODY-REGION HEATMAP
# ──────────────────────────────────────────────────────────────

_SYMPTOM_REGION_MAP: dict[str, str] = {}

_REGION_KEYWORDS: dict[str, list[str]] = {
    "head": [
        "headache", "migraine", "dizziness", "vertigo", "syncope", "tinnitus",
        "blurred vision", "vision", "visual", "eye", "ear", "hearing",
        "somnolence", "insomnia", "confusion", "seizure", "tremor",
        "anxiety", "depression", "hallucination", "amnesia", "coma",
        "cerebral", "encephalopathy", "meningitis", "stroke",
    ],
    "chest": [
        "chest pain", "palpitation", "tachycardia", "bradycardia", "arrhythmia",
        "dyspnoea", "dyspnea", "cough", "bronchospasm", "asthma",
        "pneumonia", "pulmonary", "respiratory", "cardiac", "myocardial",
        "heart", "angina", "hypertension", "hypotension", "oedema",
        "edema", "pleural", "wheezing",
    ],
    "abdomen": [
        "nausea", "vomiting", "diarrhoea", "diarrhea", "constipation",
        "abdominal", "stomach", "gastro", "gi ", "hepat", "liver",
        "pancreat", "intestin", "colitis", "dyspepsia", "flatulence",
        "rectal", "jaundice", "biliary", "spleen", "ascites",
    ],
    "arms": [
        "arm", "hand", "wrist", "elbow", "shoulder", "upper extremity",
        "carpal", "finger", "grip",
    ],
    "legs": [
        "leg", "foot", "feet", "ankle", "knee", "hip", "lower extremity",
        "gait", "claudication", "deep vein", "dvt", "toe",
    ],
    "skin": [
        "rash", "pruritus", "urticaria", "dermatitis", "erythema",
        "skin", "alopecia", "acne", "photosensitivity", "blister",
        "stevens-johnson", "toxic epidermal", "angioedema", "injection site",
        "swelling", "bruising", "petechiae", "purpura", "cellulitis",
    ],
    "systemic": [
        "fatigue", "fever", "pyrexia", "malaise", "weight", "anaphyla",
        "death", "multi-organ", "sepsis", "infection", "anaemia", "anemia",
        "thrombocytopenia", "leukopenia", "neutropenia", "lymph",
        "blood", "coagul", "haemorrhage", "hemorrhage", "pain",
        "arthralgia", "myalgia", "back pain", "muscle",
    ],
}

for _region, _kws in _REGION_KEYWORDS.items():
    for _kw in _kws:
        _SYMPTOM_REGION_MAP[_kw] = _region


def map_symptoms_to_regions(symptoms: list[str]) -> dict[str, int]:
    """Map symptom strings to body regions and return counts per region."""
    counts: dict[str, int] = {r: 0 for r in _REGION_KEYWORDS}
    counts["unknown"] = 0
    for sym in symptoms:
        low = sym.lower().strip()
        matched = False
        for kw, region in _SYMPTOM_REGION_MAP.items():
            if kw in low:
                counts[region] += 1
                matched = True
                break
        if not matched:
            counts["unknown"] += 1
    return counts


def _build_body_heatmap_html(region_counts: dict[str, int], symptoms: list[str]) -> str:
    """Return HTML with the human body image overlaid with radial gradient circles."""
    img_path = Path(__file__).resolve().parent.parent / "assets" / "images" / "humanbody.jpg"
    img_b64 = base64.b64encode(img_path.read_bytes()).decode()

    body_max = max(
        (v for k, v in region_counts.items() if k not in ("unknown", "skin", "systemic")),
        default=1,
    ) or 1
    total = sum(region_counts.values())
    unknown = region_counts.get("unknown", 0)

    def _rgb(region: str) -> str | None:
        c = region_counts.get(region, 0)
        if c == 0:
            return None
        frac = c / body_max
        if frac > 0.66:
            return "220,38,38"
        elif frac > 0.33:
            return "245,158,11"
        return "59,130,246"


@st.dialog("Personalized Risk Assessment", width="large")
def _show_risk_dialog(enriched, drug_name):
    """Lightbox modal for the personalized risk assessment calculator."""
    _render_risk_calculator(enriched, drug_name)


# ══════════════════════════════════════════════════════════════
#  SIDE-PANEL RENDERERS (Phase 2C)
# ══════════════════════════════════════════════════════════════

def _render_evidence_panel(result):
    """Render the evidence sources in the right panel."""
    evidence = result.get("evidence", [])
    if not evidence:
        st.info("No evidence chunks available for this query.")
        return

    st.markdown(f"### Evidence Sources ({len(evidence)})")
    for i, ev in enumerate(evidence, 1):
        badge = _get_source_badge(ev.get("field", ""))
        st.markdown(
            f"<div class='evidence-chunk'>"
            f"<div class='evidence-chunk-header'>"
            f"<span class='cite-pill'>{i}</span> {badge} "
            f"<code>{ev.get('field', '')}</code>"
            f"</div>"
            f"<div class='evidence-chunk-text'>"
            f"{ev.get('content', '')}"
            f"</div><div style='font-size:10px; color:var(--text-muted); margin-top:4px;'>"
            f"Doc ID: {ev.get('doc_id', 'N/A')}</div></div>",
            unsafe_allow_html=True,
        )

def _render_kg_panel(result):
    """Render Knowledge Graph visualization and data in the right panel."""
    if not result.get("kg_available"):
        st.info("Knowledge Graph data not available for this query.")
        return

    raw_ix = result.get("kg_interactions", [])
    raw_co = result.get("kg_co_reported", [])
    raw_rx = result.get("kg_reactions", [])
    raw_ing = result.get("kg_ingredients", [])

    enriched = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)

    kg_id = result.get("kg_identity") or {}
    generic = kg_id.get("generic_name", "")
    if generic:
        st.markdown(f"### Knowledge Graph: {generic.title()}")
    else:
        st.markdown("### Knowledge Graph")

    drug_name = result.get("drug_name") or "Drug"
    html = _build_kg_network_html(
        drug_name,
        enriched["ingredients"],
        enriched["interactions"],
        enriched["co_reported"],
        enriched["reactions"],
        compact=True,
    )
    components.html(html, height=390, scrolling=False)

    # Compact pill summaries — inline flow to save vertical space
    pill_html = ""
    if raw_ing:
        pill_html += "<div style='margin:6px 0 2px;font-size:11px;font-weight:700;color:#7a9bbf'>Ingredients</div>"
        pill_html += "".join(
            f"<span class='kg-pill ingredient' style='padding:3px 10px;font-size:11px;margin:2px 3px'>"
            f"{i['ingredient']}</span>"
            for i in raw_ing[:6]
        )
    if raw_ix:
        pill_html += "<div style='margin:8px 0 2px;font-size:11px;font-weight:700;color:#7a9bbf'>Interactions</div>"
        for ix in enriched["interactions"][:4]:
            sev = ix.get("_severity", "mild")
            pill_html += (
                f"<span class='kg-pill interaction' style='padding:3px 10px;font-size:11px;margin:2px 3px'>"
                f"{ix['drug_name']}</span>"
                f"<span class='kg-risk-badge {sev}' style='font-size:9px'>{sev}</span> "
            )
    if raw_rx:
        pill_html += "<div style='margin:8px 0 2px;font-size:11px;font-weight:700;color:#7a9bbf'>Top Reactions</div>"
        for rx in enriched["reactions"][:4]:
            sev = rx.get("_severity", "mild")
            pill_html += (
                f"<span class='kg-pill reaction' style='padding:3px 10px;font-size:11px;margin:2px 3px'>"
                f"{rx['reaction']}</span>"
                f"<span class='kg-risk-badge {sev}' style='font-size:9px'>{sev}</span> "
            )
    if pill_html:
        st.markdown(pill_html, unsafe_allow_html=True)

def _render_bodymap_panel(result):
    """Render the body map heatmap in the right panel."""
    symptoms = _extract_symptoms_from_result(result)
    if not symptoms:
        st.info("No symptoms identified for body mapping.")
        return

    region_counts = map_symptoms_to_regions(symptoms)
    if sum(v for k, v in region_counts.items() if k != "unknown") == 0:
        st.info("Symptoms could not be mapped to specific body regions.")
        return

    st.markdown("### Adverse-Event Body Map")
    html = _build_body_heatmap_html(region_counts, symptoms)
    components.html(html, height=530, scrolling=False)

def _render_metrics_panel(result):
    """Render query performance metrics in the right panel."""
    st.markdown("### Query Metrics")
    m1, m2 = st.columns(2)
    m1.metric("Latency", f"{result.get('latency_ms', 0):.0f} ms")
    m2.metric("Confidence", f"{result.get('confidence', 0):.0%}")

    st.divider()
    evidence = result.get("evidence", [])
    st.markdown(f"**Evidence chunks:** {len(evidence)}")
    st.markdown(f"**Records analyzed:** {result.get('num_records', 0)}")

    try:
        from src.config import is_vertex_available
        vertex_ok = is_vertex_available()
    except Exception:
        vertex_ok = False

    llm_label = "Gemini 2.5 Flash"
    if result.get("llm_used"):
        llm_label += " (Vertex AI)" if vertex_ok else " (Direct API)"
    else:
        llm_label = "Extractive fallback"

    st.markdown(f"**Generator:** {llm_label}")
    st.markdown(f"**Method:** {result.get('method', 'hybrid')}")

    enriched_n = result.get("graph_enriched_chunks", 0)
    total_n = result.get("total_chunks", 0)
    if enriched_n > 0:
        st.success(f"Graph Enrichment Active: {enriched_n}/{total_n} chunks")


# ══════════════════════════════════════════════════════════════
#  RENDER MESSAGE DETAILS (Perplexity-style expandable cards)
# ══════════════════════════════════════════════════════════════

def render_message_details(result: dict, msg_idx: int):
    """Render pill buttons that open details in the right side panel."""
    if not result:
        return

    # Source type badges row (optional, keeps context)
    evidence = result.get("evidence", [])
    if evidence:
        badges_html = ""
        fields_seen = set()
        for ev in evidence:
            field = ev.get("field", "")
            if field not in fields_seen:
                badges_html += _get_source_badge(field)
                fields_seen.add(field)
        if result.get("kg_available"):
            badges_html += "<span class='source-badge kg'>Knowledge Graph</span>"
        st.markdown(f"<div style='margin-top:8px;'>{badges_html}</div>", unsafe_allow_html=True)

    # Pill buttons for right panel (centered)
    cols = st.columns([2, 1, 1, 1, 1, 2])
    with cols[1]:
        if st.button("📊 KG", key=f"kg_btn_{msg_idx}", help="View Knowledge Graph", disabled=not result.get("kg_available")):
            st.session_state.active_detail = {"msg_idx": msg_idx, "panel": "kg"}
            st.rerun()
    with cols[2]:
        if st.button("📋 Evidence", key=f"ev_btn_{msg_idx}", help="View Source Evidence", disabled=not evidence):
            st.session_state.active_detail = {"msg_idx": msg_idx, "panel": "evidence"}
            st.rerun()
    with cols[3]:
        symptoms = _extract_symptoms_from_result(result)
        has_symptoms = len(symptoms) > 0
        if st.button("🫁 Body Map", key=f"bm_btn_{msg_idx}", help="View Symptom Heatmap", disabled=not has_symptoms):
            st.session_state.active_detail = {"msg_idx": msg_idx, "panel": "bodymap"}
            st.rerun()
    with cols[4]:
        if st.button("📈 Metrics", key=f"mt_btn_{msg_idx}", help="View Query Metrics"):
            st.session_state.active_detail = {"msg_idx": msg_idx, "panel": "metrics"}
            st.rerun()


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT INTERFACE
# ══════════════════════════════════════════════════════════════

# ── Layout: Two-Column Architecture (Phase 2A) ──
if st.session_state.get("active_detail"):
    chat_col, detail_col = st.columns([6, 4], gap="medium")
else:
    chat_col, detail_col = st.columns([10, 0.01], gap="small")

with chat_col:
    render_topbar("Safety Chat", badge_text="CLINICAL INTELLIGENCE")

    # Disclaimer
    st.markdown(
        "<div class='disclaimer-banner'>"
        "AI-powered tool for informational purposes only. "
        "Not a substitute for professional medical advice, diagnosis, or treatment. "
        "Always consult a qualified healthcare provider."
        "</div>",
        unsafe_allow_html=True,
    )

    # ── Welcome state (empty chat) ──
    if len(st.session_state.messages) == 0:
        _WELCOME_EXAMPLES = [
            {"icon": "💊", "query": "What are the drug interactions for ibuprofen?",
             "desc": "FDA label interactions, severity, and clinical guidance"},
            {"icon": "⚠️", "query": "Can I take aspirin with warfarin?",
             "desc": "Contraindications and co-prescribing risks"},
            {"icon": "🔬", "query": "What safety warnings exist for metformin?",
             "desc": "Boxed warnings, precautions, and monitoring"},
            {"icon": "📊", "query": "What are the side effects of omeprazole?",
             "desc": "FAERS adverse event reports and frequencies"},
            {"icon": "🔄", "query": "Compare adverse reactions of ibuprofen and naproxen",
             "desc": "Head-to-head safety profile comparison"},
            {"icon": "🧬", "query": "What drugs are co-reported with prednisone in FAERS?",
             "desc": "Real-world co-prescribing patterns from FDA data"},
        ]

        st.markdown(
            "<div class='welcome-hero' style='padding-top: 10px;'>"
            "<div class='welcome-title'><span>Tru</span>Pharma</div>"
            "<div class='welcome-subtitle' style='margin-bottom: 20px;'>AI-powered drug safety intelligence</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        
        # Phase 3E: Animated Counters
        components.html("""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Quicksand:wght@700;800&family=JetBrains+Mono:wght@700&display=swap');
            .t-row { display: flex; justify-content: center; gap: 16px; flex-wrap: wrap; font-family: 'Quicksand', sans-serif; background: transparent; }
            .t-card { background: #182840; border: 1px solid #1a2f45; border-radius: 10px; padding: 12px 16px; min-width: 140px; text-align: center; }
            .t-val { font-size: 1.2rem; font-weight: 800; color: #3df5c8; font-family: 'JetBrains Mono', monospace; }
            .t-label { font-size: 0.7rem; color: #7a9bbf; margin-top: 2px; text-transform: uppercase; letter-spacing: 0.05em; }
            .pulse { display: inline-block; width: 8px; height: 8px; background: #22c55e; border-radius: 50%; margin-right: 4px; position: relative; }
            .pulse::after { content: ''; position: absolute; inset: -4px; border-radius: 50%; border: 2px solid #22c55e; animation: p 2s infinite; }
            @keyframes p { 0% { transform: scale(0.5); opacity: 1; } 100% { transform: scale(2.2); opacity: 0; } }
        </style>
        <div class="t-row">
            <div class="t-card"><div class="t-val" id="val1">0</div><div class="t-label">Drug Labels</div></div>
            <div class="t-card"><div class="t-val" id="val2">0</div><div class="t-label">FAERS Reports</div></div>
            <div class="t-card"><div class="t-val"><span class="pulse"></span>Real-time</div><div class="t-label">Knowledge Graph</div></div>
            <div class="t-card"><div class="t-val" id="val3">0</div><div class="t-label">Flash 2.5</div></div>
        </div>
        <script>
            function animate(id, start, end, duration, suffix='') {
                let obj = document.getElementById(id);
                let range = end - start;
                let startTime = null;
                function step(timestamp) {
                    if (!startTime) startTime = timestamp;
                    let progress = Math.min((timestamp - startTime) / duration, 1);
                    let val = Math.floor(progress * range + start);
                    obj.innerHTML = (val >= 1000 ? (val/1000).toFixed(1) + 'K+' : val) + suffix;
                    if (progress < 1) window.requestAnimationFrame(step);
                    else obj.innerHTML = (end >= 1000000 ? (end/1000000).toFixed(1) + 'M+' : (end >= 1000 ? (end/1000).toFixed(0) + 'K+' : end)) + suffix;
                }
                window.requestAnimationFrame(step);
            }
            setTimeout(() => {
                animate('val1', 0, 150000, 1500);
                animate('val2', 0, 4200000, 2000);
                animate('val3', 0, 2.5, 1000, '');
                // Correct for val3
                document.getElementById('val3').innerHTML = 'Gemini';
            }, 300);
        </script>
        """, height=100)

        # Render clickable example cards
        cols = st.columns(2)
        for idx, ex in enumerate(_WELCOME_EXAMPLES):
            with cols[idx % 2]:
                if st.button(
                    f"{ex['icon']}  {ex['query']}",
                    key=f"welcome_ex_{idx}",
                    use_container_width=True,
                    help=ex["desc"],
                ):
                    st.session_state["_pending_example"] = ex["query"]
                    st.rerun()

        st.markdown(
            "<div class='welcome-prompt'>Ask any drug safety question below ↓</div>",
            unsafe_allow_html=True,
        )

        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            method = st.selectbox(
                "Retrieval method",
                ["hybrid", "dense", "sparse"],
                index=0,
            )
            top_k = st.slider("Top-K evidence", 3, 10, 5)
            gemini_key = st.text_input(
                "Google Gemini API key (optional)",
                value=st.session_state.gemini_key,
                type="password",
                help="If provided, answers are generated by Gemini 2.0 Flash. "
                     "Otherwise, a rule-based extractive fallback is used.",
            )
            if gemini_key != st.session_state.gemini_key:
                st.session_state.gemini_key = gemini_key

    # Handle pending example query
    query_text = st.chat_input("Ask a drug-safety question...")
    if not query_text and st.session_state.get("_pending_example"):
        query_text = st.session_state.pop("_pending_example")

    if query_text:
        if len(query_text.strip()) < 3:
            st.warning("Please enter a more specific question.")
        else:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": query_text})
            with st.chat_message("user", avatar="👤"):
                st.markdown(query_text)

            # Build conversation history (last 10 messages for Gemini context)
            conv_history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ][-10:]

            # Run RAG query
            with st.chat_message("assistant", avatar="🧪"):
                # Phase 3A: Typing Indicator
                status_placeholder = st.empty()
                status_placeholder.markdown("""
                    <div class='typing-dots'>
                        <div class='dot-bounce'></div>
                        <div class='dot-bounce'></div>
                        <div class='dot-bounce'></div>
                        <span style='margin-left:10px; font-size:12px; color:var(--text-secondary);'>Analyzing drug safety data...</span>
                    </div>
                """, unsafe_allow_html=True)

                result = run_rag_query(
                    query_text,
                    gemini_key=gemini_key,
                    method=method,
                    top_k=top_k,
                    use_rerank=False,
                    conversation_history=conv_history if conv_history else None,
                )
                
                status_placeholder.empty()

                # Format answer with citation pills
                answer = _normalize_citations(result["answer"], result.get("evidence", []))
                
                # Phase 3B: Typewriter streaming effect
                answer_placeholder = st.empty()
                words = answer.split(" ")
                for i in range(len(words)):
                    partial = " ".join(words[:i+1])
                    display_partial = _citations_to_pills(partial, result.get("evidence"))
                    answer_placeholder.markdown(f"<div class='streaming-glow'>{display_partial} ▌</div>", unsafe_allow_html=True)
                    time.sleep(0.01)
                
                display_answer = _citations_to_pills(answer, result.get("evidence"))
                answer_placeholder.markdown(display_answer, unsafe_allow_html=True)

                # Phase 3C: Source confidence bar
                if result.get("evidence"):
                    st.markdown(_render_confidence_bar(result["evidence"]), unsafe_allow_html=True)

                # Render expandable details
                try:
                    render_message_details(result, len(st.session_state.messages))
                except Exception:
                    st.caption("⚠ Details unavailable")

                # Store assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "result": result,
                })

                # Persist last run for stress test comparison
                st.session_state.primary_last_run = {
                    "query": query_text,
                    "confidence": result.get("confidence", 0),
                    "evidence_count": len(result.get("evidence", [])),
                    "latency_ms": result.get("latency_ms", 0),
                    "method": result.get("method", "hybrid"),
                    "num_records": result.get("num_records", 0),
                    "llm_used": result.get("llm_used", False),
                    "answer": answer,
                    "evidence": result.get("evidence", []),
                }
                st.rerun()

with detail_col:
    if st.session_state.get("active_detail"):
        det = st.session_state.active_detail
        msg_idx = det["msg_idx"]
        panel = det["panel"]
        
        # Get the result from session state messages
        # Note: messages list has [user, assistant, user, assistant...]
        # so assistant results are at 1, 3, 5...
        # Wait, the msg_idx passed to render_message_details is the index in st.session_state.messages
        if msg_idx < len(st.session_state.messages):
            res = st.session_state.messages[msg_idx].get("result")
            if not res and msg_idx == len(st.session_state.messages) - 1:
                 # This might be the latest result not yet stored? 
                 # Actually we just stored it and reran, so it should be there.
                 pass
            
            if res:
                # Top header for detail panel
                st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>"
                            f"<div style='font-weight:800; color:var(--teal-bright); font-size:14px;'>DETAILS PANEL</div>"
                            f"</div>", unsafe_allow_html=True)
                if st.button("✕ Close Panel", use_container_width=True):
                    st.session_state.active_detail = None
                    st.rerun()
                
                st.divider()
                
                if panel == "kg":
                    _render_kg_panel(res)
                elif panel == "evidence":
                    _render_evidence_panel(res)
                elif panel == "bodymap":
                    _render_bodymap_panel(res)
                elif panel == "metrics":
                    _render_metrics_panel(res)
            else:
                st.warning("Selected result data not found.")
                if st.button("Clear Selection"):
                    st.session_state.active_detail = None
                    st.rerun()

with st.sidebar:
    # Phase 2D: Risk Assessment — lightbox button
    st.divider()
    st.markdown("<div style='font-family:var(--font-body); font-size:0.72rem; "
                "font-weight:600; letter-spacing:0.08em; text-transform:uppercase; "
                "color:var(--text-muted); margin-bottom:0.4rem;'>Risk Assessment</div>", unsafe_allow_html=True)

    latest_kg_result = None
    if "messages" in st.session_state:
        for m in reversed(st.session_state.messages):
            if m.get("role") == "assistant" and m.get("result", {}).get("kg_available"):
                latest_kg_result = m["result"]
                break

    if latest_kg_result:
        raw_ix = latest_kg_result.get("kg_interactions", [])
        raw_rx = latest_kg_result.get("kg_reactions", [])
        raw_ing = latest_kg_result.get("kg_ingredients", [])
        raw_co = latest_kg_result.get("kg_co_reported", [])
        enriched_rc = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)
        _drug = latest_kg_result.get("drug_name", "Drug")
        if st.button(f"⚕️ Open Risk Calculator — {_drug.title()}", use_container_width=True):
            _show_risk_dialog(enriched_rc, _drug)
    else:
        st.caption("Submit a query to enable risk assessment")

    # Phase 2E: Query history in sidebar
    st.divider()
    st.markdown("<div style='font-family:var(--font-body); font-size:0.72rem; "
                "font-weight:600; letter-spacing:0.08em; text-transform:uppercase; "
                "color:var(--text-muted); margin-bottom:0.4rem;'>Query History</div>", unsafe_allow_html=True)
    user_queries = []
    if "messages" in st.session_state:
        # Get unique queries to avoid duplicates in display
        seen = set()
        for m in reversed(st.session_state.messages):
            if m["role"] == "user" and m["content"] not in seen:
                user_queries.append(m["content"])
                seen.add(m["content"])
            if len(user_queries) >= 8: break
            
    for q in user_queries:
        truncated = (q[:30] + "...") if len(q) > 30 else q
        if st.button(f"💊 {truncated}", key=f"hist_{hash(q)}", use_container_width=True):
             st.session_state["_pending_example"] = q
             st.rerun()

    st.divider()

    # System Status
    has_results = len(st.session_state.messages) > 0 and any(
        m.get("result") for m in st.session_state.messages if m.get("role") == "assistant"
    )

    # Check Vertex AI availability
    try:
        from src.config import is_vertex_available
        vertex_ok = is_vertex_available()
    except Exception:
        vertex_ok = False

    # Check Pinecone availability
    import os
    try:
        pinecone_ok = bool(os.environ.get("PINECONE_API_KEY") or
                           (hasattr(st, "secrets") and st.secrets.get("PINECONE_API_KEY", "")))
    except Exception:
        pinecone_ok = bool(os.environ.get("PINECONE_API_KEY"))

    status_html = (
        _status_row("RAG Engine", "Online", True)
        + _status_row("Knowledge Graph", "Active" if has_results else "Standby", has_results)
        + _status_row("FAERS Data", "Connected", True)
        + _status_row("Vertex AI", "Connected" if vertex_ok else "Fallback", vertex_ok)
        + _status_row("Pinecone", "Connected" if pinecone_ok else "Local FAISS", pinecone_ok)
    )
    st.markdown(
        f"<div style='font-family:var(--font-body); font-size:0.72rem; "
        f"font-weight:600; letter-spacing:0.08em; text-transform:uppercase; "
        f"color:var(--text-muted); margin-bottom:0.4rem;'>System Status</div>"
        + status_html,
        unsafe_allow_html=True,
    )

