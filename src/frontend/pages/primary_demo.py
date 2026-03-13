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
}
</style>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
if "messages" not in st.session_state:
    st.session_state.messages = []
if "kg_poll_count" not in st.session_state:
    st.session_state.kg_poll_count = 0


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
    # Home button
    if st.button("< Return to Home", key="go_home", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k not in ("_stcore",):
                st.session_state.pop(k, None)
        st.switch_page("app.py")

    st.divider()
    render_brand()
    st.divider()

    # New Chat / Clear
    col_new, col_clear = st.columns(2)
    with col_new:
        if st.button("+ New Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_clear:
        if st.button("Clear All", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.divider()

    # Example queries
    st.markdown(
        "<div style='font-size:0.72rem; font-weight:600; letter-spacing:0.08em; "
        "text-transform:uppercase; color:var(--text-muted); margin-bottom:6px; "
        "font-family:var(--font-body);'>Example Queries</div>",
        unsafe_allow_html=True,
    )
    for ex in EXAMPLES:
        if st.button(ex, key=f"ex_{ex[:20]}", use_container_width=True):
            st.session_state["_pending_example"] = ex
            st.rerun()

    st.divider()

    # Advanced settings
    with st.expander("Advanced Settings", expanded=False):
        method = st.selectbox("Retrieval method", ["hybrid", "dense", "sparse"], index=0)
        top_k = st.slider("Top-K evidence chunks", 3, 15, 5)
        gemini_key = st.text_input("Gemini API key (optional)", type="password",
                                    value=st.session_state.get("_gemini_key", ""))
        if gemini_key:
            st.session_state["_gemini_key"] = gemini_key

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
    pinecone_ok = bool(os.environ.get("PINECONE_API_KEY") or
                       (hasattr(st, "secrets") and st.secrets.get("PINECONE_API_KEY", "")))

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

    # #region agent log f1239c
    with st.expander("🔧 Debug Info (f1239c)", expanded=False):
        try:
            from src.config import _debug_init_info
            st.write("**config.py init state:**", _debug_init_info)
        except Exception as e:
            st.write(f"config debug unavailable: {e}")
        try:
            from src.rag.engine import _last_gemini_debug
            st.write("**Last Gemini call debug:**", _last_gemini_debug)
        except Exception as e:
            st.write(f"engine debug unavailable: {e}")
        import os
        st.write("**os.environ GCP_PROJECT_ID:**", "SET" if os.environ.get("GCP_PROJECT_ID") else "NOT SET")
        st.write("**os.environ GCP_LOCATION:**", os.environ.get("GCP_LOCATION", "NOT SET"))
        st.write("**os.environ GOOGLE_APPLICATION_CREDENTIALS:**", "SET" if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") else "NOT SET")
        try:
            gcp_secret = st.secrets.get("GCP_PROJECT_ID", "")
            st.write("**st.secrets GCP_PROJECT_ID:**", "FOUND" if gcp_secret else "MISSING")
        except Exception as e:
            st.write(f"st.secrets check error: {e}")
        try:
            from google import genai as _genai_check
            st.write("**google.genai importable:**", True)
            st.write("**google.genai.Client exists:**", hasattr(_genai_check, "Client"))
        except Exception as e:
            st.write(f"**google.genai import error:** {e}")
    # #endregion

    st.divider()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.markdown(
        f"<div style='font-family:var(--font-data); font-size:0.62rem; "
        f"color:var(--text-muted); letter-spacing:0.04em;'>"
        f"Session: {now}</div>",
        unsafe_allow_html=True,
    )

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


def _citations_to_pills(answer: str) -> str:
    """Convert [N] references to styled HTML citation pills."""
    def _pill(m):
        n = m.group(1)
        return f'<span class="cite-pill">{n}</span>'
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

def _build_kg_network_html(drug_name, ingredients, interactions, co_reported, reactions):
    """Build a decision-support KG visualization with vis.js in dark theme."""
    nodes, edges, details_map = [], [], {}
    nid = 0
    RADIUS = 210

    # Center node
    center_id = nid
    nodes.append({
        "id": center_id, "label": drug_name.upper(),
        "x": 0, "y": 0, "fixed": {"x": True, "y": True},
        "color": {"background": "#7c3aed", "border": "#5b21b6",
                  "highlight": {"background": "#8b5cf6", "border": "#5b21b6"}},
        "font": {"color": "#fff", "size": 16, "face": "Quicksand", "bold": True},
        "shape": "box", "borderWidth": 2,
        "margin": {"top": 10, "bottom": 10, "left": 14, "right": 14},
    })
    details_map[center_id] = {
        "name": drug_name.title(), "type_label": "Queried Drug", "color": "#7c3aed",
        "fields": [{"label": "Role", "value": "Central query subject"},
                    {"label": "Data sources", "value": "FDA labels, FAERS, openFDA"}],
    }

    # Category definitions (dark theme colors)
    categories = []
    if ingredients:
        categories.append(("ingredient", ingredients[:8],
                           "rgba(0,137,123,0.2)", "#00897b", "contains"))
    if interactions:
        categories.append(("interaction", interactions[:8],
                           "rgba(245,124,0,0.2)", "#f57c00", "interacts"))
    if co_reported:
        categories.append(("co_reported", co_reported[:8],
                           "rgba(25,118,210,0.2)", "#1976d2", "co-reported"))
    if reactions:
        categories.append(("reaction", reactions[:8],
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
            font_sz = round(11 + importance * 5)
            margin_v = round(6 + importance * 5)
            margin_h = round(10 + importance * 4)
            bw = round(1 + importance * 2, 1)
            edge_w = round(1.0 + importance * 2.5, 1)
            sev = item.get("_severity", "")
            dashes = (sev == "mild") if sev else False

            if cat == "ingredient":
                label = item["ingredient"]
                if item.get("strength"):
                    label += f"\n({item['strength']})"
                det_fields = [
                    {"label": "Dosage / Strength", "value": item.get("strength") or "See label"},
                    {"label": "Source", "value": "FDA drug label"},
                ]
            elif cat == "interaction":
                label = item["drug_name"]
                desc = item.get("description") or "No description available"
                det_fields = [
                    {"label": "Clinical severity", "value": sev.title(), "badge": sev},
                    {"label": "Mechanism", "value": (desc[:160] + "...") if len(desc) > 160 else desc},
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
            edges.append({
                "id": f"e{nid}", "from": center_id, "to": nid,
                "label": edge_label, "width": edge_w,
                "font": {"size": 9, "color": "#3d5a74"},
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

    return f"""<html><head>
<script src="https://unpkg.com/vis-network@9.1.6/standalone/umd/vis-network.min.js"></script>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:0;background:transparent;font-family:"Quicksand",sans-serif}}
#kg-root{{position:relative;width:100%}}
#kg-toolbar{{display:flex;gap:6px;align-items:center;padding:6px 8px;
  background:#111e2e;border:1px solid #1f3d5a;border-radius:10px 10px 0 0}}
#kg-search{{flex:1;max-width:220px;padding:5px 10px;border:1px solid #1f3d5a;border-radius:7px;
  font-size:12px;font-family:inherit;outline:none;background:#182840;color:#e8f0f8}}
#kg-search:focus{{border-color:#7c3aed;box-shadow:0 0 0 2px rgba(124,58,237,.15)}}
.tb-btn{{padding:5px 11px;border:1px solid #1f3d5a;border-radius:7px;background:#182840;
  font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;color:#7a9bbf;
  transition:background .12s,box-shadow .12s}}
.tb-btn:hover{{background:#1e3450;box-shadow:0 1px 4px rgba(0,0,0,.2)}}
.tb-btn.active{{background:rgba(124,58,237,0.15);border-color:#7c3aed;color:#c4b5fd}}
#kg-net{{width:100%;height:470px;border-left:1px solid #1f3d5a;border-right:1px solid #1f3d5a;
  background:#0b1622}}
#kg-detail{{position:absolute;top:40px;right:0;width:260px;height:calc(100% - 40px);
  background:rgba(17,30,46,.97);border-left:2px solid #2a5278;
  padding:14px;overflow-y:auto;transform:translateX(100%);
  transition:transform .25s ease;z-index:20;font-size:13px;color:#e8f0f8}}
#kg-detail.visible{{transform:translateX(0)}}
#kg-detail h3{{margin:0 0 2px;font-size:15px}}
.det-type{{font-size:11px;color:#7a9bbf;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #1f3d5a}}
.det-row{{display:flex;justify-content:space-between;align-items:baseline;padding:5px 0;
  border-bottom:1px solid #1a2f45}}
.det-label{{font-size:11px;color:#7a9bbf;font-weight:700;flex-shrink:0;margin-right:8px}}
.det-value{{font-size:12px;color:#e8f0f8;text-align:right}}
.det-badge{{font-size:10px;font-weight:800;padding:2px 8px;border-radius:6px;text-transform:uppercase}}
.det-badge.severe{{background:rgba(153,27,27,0.3);color:#fca5a5}}
.det-badge.moderate{{background:rgba(146,64,14,0.3);color:#fcd34d}}
.det-badge.mild{{background:rgba(6,95,70,0.3);color:#86efac}}
#kg-detail-close{{position:absolute;top:8px;right:10px;background:none;border:none;
  font-size:16px;cursor:pointer;color:#3d5a74;font-family:inherit}}
#kg-detail-close:hover{{color:#e8f0f8}}
#kg-hint{{position:absolute;bottom:8px;left:8px;z-index:15;
  background:rgba(17,30,46,.95);border:1px solid #1f3d5a;border-radius:10px;
  padding:9px 14px;font-size:11.5px;color:#7a9bbf;line-height:1.45;
  box-shadow:0 2px 8px rgba(0,0,0,.2);max-width:260px;transition:opacity .3s}}
#kg-hint b{{color:#e8f0f8}}
#kg-hint-close{{position:absolute;top:3px;right:7px;cursor:pointer;font-size:13px;
  color:#3d5a74;background:none;border:none;padding:0;font-family:inherit}}
#kg-hint-close:hover{{color:#e8f0f8}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;padding:6px 8px;font-size:11.5px;
  background:#111e2e;border:1px solid #1f3d5a;border-radius:0 0 10px 10px;color:#7a9bbf}}
.legend span{{display:inline-flex;align-items:center;gap:4px}}
.dot{{width:11px;height:11px;border-radius:3px;display:inline-block}}
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
    <b>Click a node</b> for detailed clinical info.
    <b>Drag nodes</b> to rearrange the layout.
  </div>
</div>
<div class="legend">
  <span><span class="dot" style="background:rgba(0,137,123,0.4);border:1px solid #00897b"></span> Ingredient</span>
  <span><span class="dot" style="background:rgba(245,124,0,0.4);border:1px solid #f57c00"></span> Interaction</span>
  <span><span class="dot" style="background:rgba(25,118,210,0.4);border:1px solid #1976d2"></span> Co-reported</span>
  <span><span class="dot" style="background:rgba(198,40,40,0.4);border:1px solid #c62828"></span> Adverse Rxn</span>
  <span class="sep"></span>
  <span class="dash-label">Dashed = milder evidence</span>
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
    forceAtlas2Based:{{gravitationalConstant:-38,centralGravity:0.006,
      springLength:145,springConstant:0.04,damping:0.45}},
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
#  RENDER MESSAGE DETAILS (Perplexity-style expandable cards)
# ══════════════════════════════════════════════════════════════

def render_message_details(result: dict, msg_idx: int):
    """Render expandable evidence/KG/metrics below each assistant message."""
    if not result:
        return

    evidence = result.get("evidence", [])

    # Source type badges row
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
        st.markdown(f"**Sources:** {badges_html}", unsafe_allow_html=True)

    # Evidence expander
    if evidence:
        with st.expander(f"Evidence Sources ({len(evidence)} chunks)", expanded=False):
            for i, ev in enumerate(evidence, 1):
                badge = _get_source_badge(ev.get("field", ""))
                st.markdown(
                    f"<div class='evidence-chunk'>"
                    f"<div class='evidence-chunk-header'>"
                    f"<span class='cite-pill'>{i}</span> {badge} "
                    f"<code>{ev.get('field', '')}</code> &middot; "
                    f"Doc: <code>{ev.get('doc_id', 'N/A')}</code>"
                    f"</div>"
                    f"<div class='evidence-chunk-text'>"
                    f"{ev.get('content', '')[:500]}"
                    f"</div></div>",
                    unsafe_allow_html=True,
                )

    # KG expander
    if result.get("kg_available"):
        raw_ix = result.get("kg_interactions", [])
        raw_co = result.get("kg_co_reported", [])
        raw_rx = result.get("kg_reactions", [])
        raw_ing = result.get("kg_ingredients", [])

        if raw_ix or raw_co or raw_rx or raw_ing:
            with st.expander("Knowledge Graph", expanded=False):
                enriched = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)

                # KG identity
                kg_id = result.get("kg_identity") or {}
                generic = kg_id.get("generic_name", "")
                brands = kg_id.get("brand_names", [])
                if generic:
                    brand_str = ", ".join(brands[:5]) if brands else "--"
                    st.markdown(f"**Drug:** {generic.title()} | **Brands:** {brand_str}")

                # Summary metrics
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.metric("Interactions", len(raw_ix))
                with s2:
                    st.metric("Adverse Reactions", len(raw_rx))
                with s3:
                    st.metric("Co-reported Drugs", len(raw_co))

                # Interactive vis.js network
                drug_name = result.get("drug_name") or "Drug"
                f_ing = enriched["ingredients"]
                f_ix = enriched["interactions"]
                f_co = enriched["co_reported"]
                f_rx = enriched["reactions"]
                if f_ing or f_ix or f_co or f_rx:
                    html = _build_kg_network_html(drug_name, f_ing, f_ix, f_co, f_rx)
                    components.html(html, height=560, scrolling=False)

                # Pill summaries
                if raw_ing:
                    st.markdown("**Ingredients:**")
                    pills = "".join(
                        f"<span class='kg-pill ingredient'>{i['ingredient']}"
                        f"{(' &middot; ' + i['strength']) if i.get('strength') else ''}</span>"
                        for i in raw_ing[:8])
                    st.markdown(pills, unsafe_allow_html=True)

                if raw_ix:
                    st.markdown("**Drug Interactions:**")
                    for ix in enriched["interactions"][:6]:
                        sev = ix.get("_severity", "mild")
                        st.markdown(
                            f"<span class='kg-pill interaction'>{ix['drug_name']}</span> "
                            f"<span class='kg-risk-badge {sev}'>{sev}</span>",
                            unsafe_allow_html=True)

                if raw_rx:
                    st.markdown("**Top Adverse Reactions:**")
                    for rx in enriched["reactions"][:6]:
                        sev = rx.get("_severity", "mild")
                        cnt = rx.get("report_count", 0)
                        st.markdown(
                            f"<span class='kg-pill reaction'>{rx['reaction']}</span> "
                            f"({cnt:,} reports) "
                            f"<span class='kg-risk-badge {sev}'>{sev}</span>",
                            unsafe_allow_html=True)

    # Metrics expander
    with st.expander("Query Metrics", expanded=False):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latency", f"{result.get('latency_ms', 0):.0f} ms")
        m2.metric("Evidence", len(evidence))
        m3.metric("Confidence", f"{result.get('confidence', 0):.0%}")
        m4.metric("Records", result.get("num_records", 0))

        llm_label = "Gemini 2.5 Flash"
        if result.get("llm_used"):
            if vertex_ok:
                llm_label += " (Vertex AI)"
            else:
                llm_label += " (Direct API)"
        else:
            llm_label = "Extractive fallback"
        st.markdown(
            f"**Generator:** {llm_label} | "
            f"**Method:** {result.get('method', 'hybrid')}"
        )

        enriched_n = result.get("graph_enriched_chunks", 0)
        total_n = result.get("total_chunks", 0)
        if enriched_n > 0:
            st.success(
                f"Graph Enrichment Active -- {enriched_n}/{total_n} chunks "
                f"enriched with KG context"
            )


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT INTERFACE
# ══════════════════════════════════════════════════════════════

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

# Display conversation history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            display_text = _citations_to_pills(msg["content"])
            st.markdown(display_text, unsafe_allow_html=True)
            render_message_details(msg.get("result", {}), i)
        else:
            st.markdown(msg["content"])

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
        with st.chat_message("user"):
            st.markdown(query_text)

        # Build conversation history (last 10 messages for Gemini context)
        conv_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ][-10:]

        # Run RAG query
        with st.chat_message("assistant"):
            with st.spinner("Searching FDA labels and knowledge graph..."):
                result = run_rag_query(
                    query_text,
                    gemini_key=gemini_key,
                    method=method,
                    top_k=top_k,
                    use_rerank=False,
                    conversation_history=conv_history if conv_history else None,
                )

            # Format answer with citation pills
            answer = _normalize_citations(result["answer"], result.get("evidence", []))
            display_answer = _citations_to_pills(answer)
            st.markdown(display_answer, unsafe_allow_html=True)

            # Render expandable details
            render_message_details(result, len(st.session_state.messages))

            # Store assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "result": result,
            })
