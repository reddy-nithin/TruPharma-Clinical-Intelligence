"""
TruPharma GenAI Assistant  ·  Conversational Safety Chat
=========================================================
Streamlit page: conversational drug-safety RAG with knowledge graph,
source citations, and expandable evidence/metrics panels.
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

from src.rag.engine import run_rag_query, read_logs

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Safety Chat | TruPharma RAG",
    page_icon="🩺",
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

# ─── Hide built-in page nav ──────────────────────────────────
st.markdown("""
<style>
div[data-testid="stSidebarNav"] { display: none !important; }
section[data-testid="stSidebar"] nav { display: none !important; }
section[data-testid="stSidebar"] ul[role="list"] { display: none !important; }
section[data-testid="stSidebar"] > div:first-child { padding-top: 0rem !important; }
section[data-testid="stSidebar"] ul[data-testid="stSidebarNavItems"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ─── App styling ──────────────────────────────────────────────
st.markdown("""<style>
.main-header-bar {
    background: linear-gradient(90deg, #F2994A, #EB5757);
    color: white; padding: 12px 16px; border-radius: 10px;
    font-weight: 600; margin-bottom: 14px;
}
.disclaimer-banner {
    background: #fefce8; border: 1px solid #fbbf24;
    border-radius: 8px; padding: 8px 14px;
    font-size: 12px; color: #92400e; margin-bottom: 14px;
    text-align: center;
}
.scenario-card {
    padding: 10px 12px; border-radius: 10px;
    margin-bottom: 8px; font-weight: 700; line-height: 1.2;
}
.primary-active {
    background-color: #E8F5E9; border-left: 6px solid #2E7D32;
}
.card {
    background: #FFFFFF; border: 1px solid #D1D5DB;
    border-radius: 14px; padding: 14px 16px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08); margin-bottom: 14px;
}
.card-title { font-weight: 800; font-size: 16px; margin-bottom: 8px; }
.card-title.response { color: #1f7a8c; }
.card-title.evidence { color: #d35400; }
.card-title.metrics  { color: #2e7d32; }
.card-title.logs     { color: #6b7280; }
.card.card-response  { border-left: 4px solid #1f7a8c; }
.card.card-evidence  { border-left: 4px solid #d35400; }
.card.card-metrics   { border-left: 4px solid #2e7d32; }
.card.card-logs      { border-left: 4px solid #6b7280; }
.card.card-kg        { border-left: 4px solid #7c3aed; }
.card.card-bodymap   { border-left: 4px solid #7c3aed; }
.kg-pill {
    display: inline-block; padding: 5px 14px; margin: 3px 4px;
    border-radius: 20px; font-size: 13px; font-weight: 700;
    line-height: 1.4;
}
.kg-pill.ingredient { background: #e0f2f1; color: #00695c; border: 1px solid #b2dfdb; }
.kg-pill.interaction { background: #fff3e0; color: #e65100; border: 1px solid #ffe0b2; }
.kg-pill.co-reported { background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }
.kg-pill.reaction { background: #fce4ec; color: #b71c1c; border: 1px solid #f8bbd0; }
.kg-section-label {
    font-weight: 800; font-size: 14px; margin: 12px 0 6px 0;
    padding-bottom: 4px; border-bottom: 2px solid #ede9fe;
    color: #5b21b6;
}
.kg-summary-card {
    background: linear-gradient(135deg, #faf5ff 0%, #ffffff 100%);
    border: 1px solid #ede9fe; border-radius: 12px;
    padding: 10px 14px; text-align: center;
}
.kg-summary-card .label { font-size: 11px; color: #6b7280; font-weight: 700; text-transform: uppercase; }
.kg-summary-card .value { font-size: 18px; font-weight: 800; color: #1f2937; margin: 2px 0; }
.kg-summary-card .sub { font-size: 11px; color: #9ca3af; }
.kg-risk-badge {
    display: inline-block; padding: 3px 10px; border-radius: 8px;
    font-weight: 800; font-size: 13px;
}
.kg-risk-badge.low { background: #d1fae5; color: #065f46; }
.kg-risk-badge.moderate { background: #fef3c7; color: #92400e; }
.kg-risk-badge.high { background: #fee2e2; color: #991b1b; }
.source-badge {
    display: inline-block; padding: 2px 8px; margin: 2px 3px;
    border-radius: 12px; font-size: 11px; font-weight: 700;
}
.source-badge.fda-label { background: #dbeafe; color: #1e40af; }
.source-badge.faers { background: #fce7f3; color: #9d174d; }
.source-badge.kg { background: #ede9fe; color: #5b21b6; }
.bullets { margin: 0; padding-left: 18px; }
.bullets li { margin: 6px 0; }
/* Apply custom font but exclude Streamlit icon elements */
html, body,
p, h1, h2, h3, h4, h5, h6,
span, div, li, td, th, label, a,
input, textarea, select, button,
.stMarkdown, .stText, .stCaption,
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"] {
    font-family: "Times New Roman", Times, serif !important;
    line-height: 1.4;
}
/* Restore Streamlit's icon font for Material Icons */
[data-testid="stIconMaterial"],
.material-symbols-rounded,
[data-testid="collapsedControl"] span,
span[class*="icon"] {
    font-family: "Material Symbols Rounded" !important;
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
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
if st.sidebar.button("⬅ Return to Home", key="go_home"):
    for k in list(st.session_state.keys()):
        if k not in ("_"):
            st.session_state.pop(k, None)
    st.switch_page("app.py")

st.sidebar.title("Scenario Mode")
st.sidebar.markdown(
    "<div class='scenario-card primary-active'>"
    "🟢 Safety Chat<br><small>Conversational drug-safety assistant</small></div>",
    unsafe_allow_html=True,
)
if st.sidebar.button("⚠️ Go to Stress Test", key="go_stress"):
    st.switch_page("pages/stress_test.py")

st.sidebar.markdown("---")

# Example queries for convenience
st.sidebar.subheader("Example Queries")
EXAMPLES = [
    "-- Select an example --",
    "What are the drug interactions for ibuprofen?",
    "Can I take aspirin with warfarin?",
    "What drugs interact with metformin?",
    "What is the recommended dosage for acetaminophen and are there any warnings?",
    "What safety warnings exist for caffeine-containing products?",
    "Are there any boxed warnings for lisinopril?",
    "What are the most commonly reported side effects of omeprazole?",
    "What adverse reactions are associated with atorvastatin?",
    "How serious are adverse events reported for metoprolol?",
    "What are the active ingredients in Tylenol and what are the drug interactions?",
    "What drugs contain acetaminophen as an active ingredient?",
    "I am taking aspirin daily. What should I know about overdosage and when to stop use?",
    "What happens if I take too much gabapentin?",
    "Compare the adverse reaction profiles of ibuprofen and naproxen.",
    "What drugs are commonly co-reported with prednisone in adverse event reports?",
    "What is the projected cost of antimicrobial resistance to GDP in 2050?",
]
example = st.sidebar.selectbox("Pick a sample question:", EXAMPLES, index=0)

# ── Advanced settings (collapsible) ──
with st.sidebar.expander("Advanced Settings"):
    method = st.selectbox(
        "Retrieval method",
        ["hybrid", "dense", "sparse"],
        index=0,
    )
    top_k = st.slider("Top-K evidence", 3, 10, 5)
    # Auto-load Gemini key from secrets or environment
    _default_key = ""
    try:
        _default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    if not _default_key:
        import os as _os
        _default_key = _os.environ.get("GEMINI_API_KEY", "") or _os.environ.get("GOOGLE_API_KEY", "")

    gemini_key = st.text_input(
        "Google Gemini API key",
        value=_default_key,
        type="password",
        help="Used for Gemini 2.5 Flash answer generation. "
             "Auto-loaded from secrets/environment if available.",
    )

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Clear Conversation"):
    st.session_state.messages = []
    st.rerun()


# ══════════════════════════════════════════════════════════════
#  HELPER: Citation normalization
# ══════════════════════════════════════════════════════════════

def _normalize_citations(answer: str, evidence: list) -> str:
    """Replace any leftover raw chunk-ID citations with [Evidence N] labels."""
    import re
    for i, ev in enumerate(evidence, 1):
        raw_id = ev.get("_raw_id", "")
        if raw_id:
            answer = answer.replace(f"[{raw_id}]", f"[Evidence {i}]")
    def _replace_unknown(m):
        inner = m.group(1)
        if re.match(r"Evidence \d+", inner):
            return m.group(0)
        if re.match(r"FDA Label \d+", inner) or inner in ("FAERS", "KG"):
            return m.group(0)
        for j, ev in enumerate(evidence, 1):
            if ev.get("doc_id", "") in inner or ev.get("field", "") in inner:
                return f"[Evidence {j}]"
        return m.group(0)
    answer = re.sub(r"\[([^\]]+)\]", _replace_unknown, answer)
    return answer


def _get_source_badge(field: str) -> str:
    """Return an HTML source badge based on the evidence field type."""
    field_lower = field.lower()
    if any(kw in field_lower for kw in ("faers", "adverse_event", "co_reported")):
        return "<span class='source-badge faers'>FAERS</span>"
    return "<span class='source-badge fda-label'>FDA Label</span>"


# ══════════════════════════════════════════════════════════════
#  KG VISUALIZATION HELPERS (preserved from original)
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

    most_common_rxn = max(enriched_rx, key=lambda r: r.get("report_count", 0)) if enriched_rx else None
    most_severe_ix = next(
        (ix for ix in enriched_ix if ix["_severity"] == "severe"),
        enriched_ix[0] if enriched_ix else None,
    )
    return {
        "ingredients": ingredients,
        "interactions": enriched_ix,
        "co_reported": enriched_co,
        "reactions": enriched_rx,
        "most_common_rxn": most_common_rxn,
        "most_severe_ix": most_severe_ix,
    }


def _build_kg_network_html(drug_name, ingredients, interactions, co_reported, reactions):
    """Build a full decision-support KG visualization with vis.js."""
    nodes, edges, details_map = [], [], {}
    nid = 0
    RADIUS = 210

    center_id = nid
    nodes.append({
        "id": center_id, "label": drug_name.upper(),
        "x": 0, "y": 0, "fixed": {"x": True, "y": True},
        "color": {"background": "#7c3aed", "border": "#5b21b6",
                  "highlight": {"background": "#8b5cf6", "border": "#5b21b6"}},
        "font": {"color": "#fff", "size": 16, "face": "Times New Roman", "bold": True},
        "shape": "box", "borderWidth": 2,
        "margin": {"top": 10, "bottom": 10, "left": 14, "right": 14},
    })
    details_map[center_id] = {
        "name": drug_name.title(), "type_label": "Queried Drug", "color": "#7c3aed",
        "fields": [{"label": "Role", "value": "Central query subject"},
                    {"label": "Data sources", "value": "FDA labels, FAERS, openFDA"}],
    }

    categories = []
    if ingredients:
        categories.append(("ingredient", ingredients[:8], "#e0f2f1", "#00897b", "contains"))
    if interactions:
        categories.append(("interaction", interactions[:8], "#fff3e0", "#f57c00", "interacts"))
    if co_reported:
        categories.append(("co_reported", co_reported[:8], "#e3f2fd", "#1976d2", "co-reported"))
    if reactions:
        categories.append(("reaction", reactions[:8], "#fce4ec", "#c62828", "adverse rxn"))

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
                    {"label": "Clinical relevance", "value": "Check for sodium load, allergens, or inactive excipients"},
                    {"label": "Source", "value": "FDA drug label"},
                ]
            elif cat == "interaction":
                label = item["drug_name"]
                desc = item.get("description") or "No description available"
                det_fields = [
                    {"label": "Clinical severity", "value": sev.title(), "badge": sev},
                    {"label": "Mechanism", "value": (desc[:160] + "...") if len(desc) > 160 else desc},
                    {"label": "Recommendation", "value": "Consult prescribing information"},
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
                    {"label": "Onset timing", "value": "Data not available"},
                    {"label": "Source", "value": "FAERS"},
                ]

            nodes.append({
                "id": nid, "label": label, "x": x, "y": y,
                "color": {"background": bg, "border": border},
                "font": {"size": font_sz, "face": "Times New Roman"},
                "shape": "box", "borderWidth": bw,
                "margin": {"top": margin_v, "bottom": margin_v,
                           "left": margin_h, "right": margin_h},
            })
            edges.append({
                "id": f"e{nid}", "from": center_id, "to": nid,
                "label": edge_label, "width": edge_w,
                "font": {"size": 9, "color": "#999"},
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
body{{margin:0;padding:0;background:transparent;font-family:"Times New Roman",serif}}
#kg-root{{position:relative;width:100%}}
#kg-toolbar{{display:flex;gap:6px;align-items:center;padding:6px 8px;
  background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px 10px 0 0}}
#kg-search{{flex:1;max-width:220px;padding:5px 10px;border:1px solid #d1d5db;border-radius:7px;
  font-size:12px;font-family:inherit;outline:none}}
#kg-search:focus{{border-color:#7c3aed;box-shadow:0 0 0 2px rgba(124,58,237,.15)}}
.tb-btn{{padding:5px 11px;border:1px solid #d1d5db;border-radius:7px;background:#fff;
  font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;color:#374151;
  transition:background .12s,box-shadow .12s}}
.tb-btn:hover{{background:#f3f4f6;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
.tb-btn.active{{background:#ede9fe;border-color:#7c3aed;color:#5b21b6}}
#kg-net{{width:100%;height:420px;border-left:1px solid #e5e7eb;border-right:1px solid #e5e7eb;
  background:#faf9fb}}
#kg-detail{{position:absolute;top:40px;right:0;width:260px;height:calc(100% - 40px);
  background:rgba(255,255,255,.97);border-left:2px solid #ede9fe;
  padding:14px;overflow-y:auto;transform:translateX(100%);
  transition:transform .25s ease;z-index:20;font-size:13px}}
#kg-detail.visible{{transform:translateX(0)}}
#kg-detail h3{{margin:0 0 2px;font-size:15px}}
.det-type{{font-size:11px;color:#6b7280;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid #e5e7eb}}
.det-row{{display:flex;justify-content:space-between;align-items:baseline;padding:5px 0;
  border-bottom:1px solid #f3f4f6}}
.det-label{{font-size:11px;color:#6b7280;font-weight:700;flex-shrink:0;margin-right:8px}}
.det-value{{font-size:12px;color:#1f2937;text-align:right}}
.det-badge{{font-size:10px;font-weight:800;padding:2px 8px;border-radius:6px;text-transform:uppercase}}
.det-badge.severe{{background:#fee2e2;color:#991b1b}}
.det-badge.moderate{{background:#fef3c7;color:#92400e}}
.det-badge.mild{{background:#d1fae5;color:#065f46}}
#kg-detail-close{{position:absolute;top:8px;right:10px;background:none;border:none;
  font-size:16px;cursor:pointer;color:#9ca3af;font-family:inherit}}
#kg-detail-close:hover{{color:#374151}}
#kg-hint{{position:absolute;bottom:8px;left:8px;z-index:15;
  background:rgba(255,255,255,.95);border:1px solid #e5e7eb;border-radius:10px;
  padding:9px 14px;font-size:11.5px;color:#6b7280;line-height:1.45;
  box-shadow:0 2px 8px rgba(0,0,0,.05);max-width:260px;transition:opacity .3s}}
#kg-hint b{{color:#374151}}
#kg-hint-close{{position:absolute;top:3px;right:7px;cursor:pointer;font-size:13px;
  color:#9ca3af;background:none;border:none;padding:0;font-family:inherit}}
#kg-hint-close:hover{{color:#374151}}
.legend{{display:flex;gap:14px;flex-wrap:wrap;padding:6px 8px;font-size:11.5px;
  background:#f9fafb;border:1px solid #e5e7eb;border-radius:0 0 10px 10px}}
.legend span{{display:inline-flex;align-items:center;gap:4px}}
.dot{{width:11px;height:11px;border-radius:3px;display:inline-block}}
.legend .sep{{border-left:1px solid #d1d5db;height:14px;margin:0 2px}}
.legend .dash-label{{color:#9ca3af;font-style:italic}}
</style></head><body>
<div id="kg-root">
  <div id="kg-toolbar">
    <input id="kg-search" placeholder="Search nodes..." autocomplete="off"/>
    <button class="tb-btn" id="kg-focus-btn">Focus</button>
    <button class="tb-btn" id="kg-reset-btn">Reset</button>
    <button class="tb-btn" id="kg-fit-btn">Fit</button>
  </div>
  <div id="kg-net"></div>
  <div id="kg-detail">
    <button id="kg-detail-close">&times;</button>
    <div id="kg-detail-content"></div>
  </div>
  <div id="kg-hint">
    <button id="kg-hint-close">&times;</button>
    <b>Click a node</b> for detailed clinical info.
    <b>Drag nodes</b> to rearrange.
  </div>
</div>
<div class="legend">
  <span><span class="dot" style="background:#e0f2f1;border:1px solid #00897b"></span> Ingredient</span>
  <span><span class="dot" style="background:#fff3e0;border:1px solid #f57c00"></span> Interaction</span>
  <span><span class="dot" style="background:#e3f2fd;border:1px solid #1976d2"></span> Co-reported</span>
  <span><span class="dot" style="background:#fce4ec;border:1px solid #c62828"></span> Adverse Rxn</span>
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
      nu.push({{id:n.id,color:{{background:"#f3f4f6",border:"#e5e7eb"}},
        font:{{color:"#d1d5db",size:10}}}});
  }});
  edges.forEach(function(e){{
    if(keepIds.indexOf(e.from)===-1||keepIds.indexOf(e.to)===-1)
      eu.push({{id:e.id,color:{{color:"#f0f0f0"}},font:{{color:"#f0f0f0"}}}});
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
#  BODY HEATMAP HELPERS (preserved from original)
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


# ══════════════════════════════════════════════════════════════
#  RENDER ASSISTANT MESSAGE DETAILS
# ══════════════════════════════════════════════════════════════

def render_message_details(result: dict, msg_idx: int):
    """Render expandable sections for evidence, KG data, and metrics within a chat message."""
    if not result:
        return

    # Source badges for the answer
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
        st.markdown(f"**Sources:** {badges_html}", unsafe_allow_html=True)

    # Evidence expander
    if evidence:
        with st.expander(f"Evidence ({len(evidence)} chunks)", expanded=False):
            for i, ev in enumerate(evidence, 1):
                badge = _get_source_badge(ev.get("field", ""))
                st.markdown(
                    f"**[Evidence {i}]** {badge} Field: `{ev['field']}` · Doc: `{ev['doc_id']}`",
                    unsafe_allow_html=True,
                )
                st.text(ev["content"][:500])
                st.markdown("---")

    # KG expander
    if result.get("kg_available"):
        raw_ix = result.get("kg_interactions", [])
        raw_co = result.get("kg_co_reported", [])
        raw_rx = result.get("kg_reactions", [])
        raw_ing = result.get("kg_ingredients", [])

        if raw_ix or raw_co or raw_rx or raw_ing:
            with st.expander("Knowledge Graph Data", expanded=False):
                enriched = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)

                # KG identity
                kg_id = result.get("kg_identity") or {}
                generic = kg_id.get("generic_name", "")
                brands = kg_id.get("brand_names", [])
                if generic:
                    brand_str = ", ".join(brands[:5]) if brands else "—"
                    st.markdown(f"**Drug:** {generic.title()} · **Brands:** {brand_str}")

                # Summary metrics
                s1, s2, s3 = st.columns(3)
                with s1:
                    st.metric("Interactions", len(raw_ix))
                with s2:
                    st.metric("Adverse Reactions", len(raw_rx))
                with s3:
                    st.metric("Co-reported Drugs", len(raw_co))

                # Interactive KG visualization
                drug_name = result.get("drug_name") or "Drug"
                f_ing = enriched["ingredients"]
                f_ix = enriched["interactions"]
                f_co = enriched["co_reported"]
                f_rx = enriched["reactions"]
                if f_ing or f_ix or f_co or f_rx:
                    html = _build_kg_network_html(drug_name, f_ing, f_ix, f_co, f_rx)
                    components.html(html, height=500, scrolling=False)

                # Pill-based summaries
                if raw_ing:
                    st.markdown("**Ingredients:**")
                    pills = "".join(
                        f"<span class='kg-pill ingredient'>{i['ingredient']}"
                        f"{(' · ' + i['strength']) if i.get('strength') else ''}</span>"
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
    with st.expander("Metrics", expanded=False):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Latency", f"{result.get('latency_ms', 0):.0f} ms")
        m2.metric("Evidence", len(evidence))
        m3.metric("Confidence", f"{result.get('confidence', 0):.0%}")
        m4.metric("Records", result.get("num_records", 0))
        llm_label = "Gemini 2.0 Flash (Vertex AI)" if result.get("llm_used") else "Extractive fallback"
        st.markdown(f"**Generator:** {llm_label} · **Method:** {result.get('method', 'hybrid')}")

        enriched_n = result.get("graph_enriched_chunks", 0)
        total_n = result.get("total_chunks", 0)
        if enriched_n > 0:
            st.success(f"Graph Enrichment Active — {enriched_n}/{total_n} chunks enriched with KG context")


# ══════════════════════════════════════════════════════════════
#  MAIN CHAT INTERFACE
# ══════════════════════════════════════════════════════════════

st.markdown("## TruPharma GenAI Assistant")
st.markdown(
    "<div class='main-header-bar'>Safety Chat — Conversational Drug-Safety RAG</div>",
    unsafe_allow_html=True,
)
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
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("result"):
            render_message_details(msg["result"], i)

# Handle example query selection
if example != EXAMPLES[0]:
    # Use the example as the next query if user selected one
    if not st.session_state.messages or st.session_state.messages[-1].get("content") != example:
        st.session_state["_pending_example"] = example

# Chat input
user_input = st.chat_input("Ask a drug-safety question...")

# Process pending example or new input
query_text = user_input
if not query_text and st.session_state.get("_pending_example"):
    query_text = st.session_state.pop("_pending_example")

if query_text:
    # Validate input
    if len(query_text.strip()) < 3:
        st.warning("Please enter a more specific question.")
    else:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": query_text})
        with st.chat_message("user"):
            st.markdown(query_text)

        # Build conversation history for context
        conv_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[:-1]  # exclude current query
        ]

        # Run RAG query
        with st.chat_message("assistant"):
            with st.spinner("Fetching FDA drug labels and running RAG pipeline..."):
                result = run_rag_query(
                    query_text,
                    gemini_key=gemini_key,
                    method=method,
                    top_k=top_k,
                    use_rerank=False,
                    conversation_history=conv_history if conv_history else None,
                )

            # Format answer with citations
            answer = _normalize_citations(result["answer"], result.get("evidence", []))
            st.markdown(answer)

            # Render expandable details
            render_message_details(result, len(st.session_state.messages))

            # Store assistant message with full result
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "result": result,
            })
