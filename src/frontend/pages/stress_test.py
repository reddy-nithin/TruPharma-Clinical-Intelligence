"""
TruPharma  ·  Stress Test / Scenario Validation
=================================================
Runs edge-case queries through the real RAG pipeline and compares
behaviour against the Safety Chat baseline.
"""

import sys
from pathlib import Path

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
import streamlit.components.v1 as components

from src.rag.engine import run_rag_query
from src.frontend.theme import inject_theme, render_topbar, render_brand

# ─── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="Stress Test | Scenario Validation",
    page_icon="⚠️",
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

# ─── Inject theme ────────────────────────────────────────────
inject_theme()


# ══════════════════════════════════════════════════════════════
#  SIDEBAR
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    render_brand()
    st.divider()

st.sidebar.markdown(
    "<div class='tp-section-header'>Scenario Mode</div>",
    unsafe_allow_html=True,
)
if st.sidebar.button("⬅ Return to Safety Chat", key="go_safety_chat"):
    st.switch_page("pages/primary_demo.py")

st.sidebar.markdown(
    "<div class='scenario-card stress-active'>"
    "🟠 Stress Test<br><small>Edge case / robustness validation</small></div>",
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")

STRESS_QUERIES = {
    "Rare input": "What are the precautions for orphenadrine citrate injection?",
    "Large doc": "drug interactions and warnings for any medication",
    "Heavy traffic": "What are the side effects of ibuprofen?",
    "Conflicting evidence": "Should I take aspirin or ibuprofen for pain relief? Compare their warnings.",
}

stress_condition = st.sidebar.radio(
    "Stress Condition (choose one)",
    list(STRESS_QUERIES.keys()),
)

st.sidebar.caption(f"**Query:** {STRESS_QUERIES[stress_condition]}")
run = st.sidebar.button("Run Stress Test", type="primary", width="stretch")


# ══════════════════════════════════════════════════════════════
#  SESSION STATE
# ══════════════════════════════════════════════════════════════
if "primary_last_run" not in st.session_state:
    st.session_state.primary_last_run = None

if "stress_result" not in st.session_state:
    st.session_state.stress_result = None
if "stress_condition" not in st.session_state:
    st.session_state.stress_condition = None


# ══════════════════════════════════════════════════════════════
#  RUN STRESS TEST
# ══════════════════════════════════════════════════════════════
if run:
    stress_query = STRESS_QUERIES[stress_condition]

    stress_config = {
        "Rare input":           {"api_limit": 20, "max_records": 20, "top_k": 3},
        "Large doc":            {"api_limit": 20, "max_records": 20, "top_k": 5},
        "Heavy traffic":        {"api_limit": 20, "max_records": 20, "top_k": 3},
        "Conflicting evidence": {"api_limit": 20, "max_records": 20, "top_k": 5},
    }[stress_condition]

    with st.spinner(f"Running stress test: **{stress_condition}** ..."):
        result = run_rag_query(
            stress_query,
            method="hybrid",
            **stress_config,
        )

    st.session_state.stress_result = result
    st.session_state.stress_condition = stress_condition


# ══════════════════════════════════════════════════════════════
#  PAGE HEADER
# ══════════════════════════════════════════════════════════════
render_topbar("Scenario Validation")

st.markdown(
    "<div class='tp-page-header'>Scenario <span>Validation</span> View</div>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div class='main-header-bar'>Stress Test: TruPharma RAG vs Edge Case Scenarios</div>",
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
import re as _re

def _clean_answer_citations(answer, evidence):
    """Normalise raw citation IDs to [Evidence N] form."""
    for j, ev in enumerate(evidence, 1):
        raw = ev.get("_raw_id", "")
        if raw:
            answer = answer.replace(f"[{raw}]", f"[Evidence {j}]")
    def _repl(m):
        inner = m.group(1)
        if _re.match(r"Evidence \d+", inner) or _re.match(r"\d+$", inner):
            return m.group(0)
        for k, e in enumerate(evidence, 1):
            if e.get("doc_id", "") in inner or e.get("field", "") in inner:
                return f"[Evidence {k}]"
        return m.group(0)
    return _re.sub(r"\[([^\]]+)\]", _repl, answer)


def _render_result_panel(label, sublabel, header_cls, data):
    """Render a unified result panel for either baseline or stress-test data."""
    st.markdown(f"<div class='panel'>", unsafe_allow_html=True)
    st.markdown(f"<div class='panel-header {header_cls}'>{label}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='panel-subheader'>{sublabel}</div>", unsafe_allow_html=True)

    if data is None:
        st.info("No data yet — run a query to populate this panel.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Input
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Input</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='mini'><b>Query:</b> {data['query']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Metrics row
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Monitoring / Metrics</div>", unsafe_allow_html=True)
    latency = data.get("latency_ms", 0)
    confidence = data.get("confidence", 0)
    evidence = data.get("evidence", [])
    ev_count = data.get("evidence_count", len(evidence))
    st.markdown(f"- **Latency:** {latency:.0f} ms")
    st.markdown(f"- **Confidence:** {confidence:.0%}")
    st.markdown(f"- **Evidence count:** {ev_count}")
    st.markdown(f"- **Records fetched:** {data.get('num_records', '—')}")
    st.markdown(f"- **Method:** {data.get('method', '—')}")
    st.markdown(f"- **LLM used:** {'Gemini' if data.get('llm_used') else 'Extractive fallback'}")
    st.markdown("</div>", unsafe_allow_html=True)

    # Answer preview
    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Answer Preview</div>", unsafe_allow_html=True)
    ans = data.get("answer", "")
    if ans and evidence:
        ans = _clean_answer_citations(ans, evidence)
    if ans:
        st.write(ans[:500] + ("…" if len(ans) > 500 else ""))
    else:
        st.caption("No answer available.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  TWO SIDE-BY-SIDE PANELS
# ══════════════════════════════════════════════════════════════
left, right = st.columns(2, gap="large")

p = st.session_state.primary_last_run
sr = st.session_state.stress_result
sc = st.session_state.stress_condition

# ── Safety Chat Scenario (from last Safety Chat run) ──
with left:
    _render_result_panel(
        "Safety Chat Baseline",
        "Last query from Safety Chat",
        "primary",
        p,
    )

# ── Stress-Test Scenario (real RAG results) ──
with right:
    if sr and sc:
        stress_data = {
            "query": STRESS_QUERIES[sc],
            "latency_ms": sr.get("latency_ms", 0),
            "confidence": sr.get("confidence", 0),
            "evidence": sr.get("evidence", []),
            "evidence_count": len(sr.get("evidence", [])),
            "num_records": sr.get("num_records", 0),
            "method": sr.get("method", "hybrid"),
            "llm_used": sr.get("llm_used", False),
            "answer": sr.get("answer", ""),
        }
        _render_result_panel(
            f"Stress Test — {sc}",
            "Edge case / robustness check",
            "stress",
            stress_data,
        )
    else:
        _render_result_panel(
            "Stress-Test Scenario",
            "Select a condition and run",
            "stress",
            None,
        )

# ══════════════════════════════════════════════════════════════
#  COMPARISON DELTA (shown when both panels have data)
# ══════════════════════════════════════════════════════════════
if p and sr:
    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='main-header-bar'>Comparison: Baseline vs Stress Test</div>",
        unsafe_allow_html=True,
    )
    d1, d2, d3, d4 = st.columns(4)
    base_lat = p.get("latency_ms", 0)
    stress_lat = sr.get("latency_ms", 0)
    d1.metric("Baseline Latency", f"{base_lat:.0f} ms")
    d2.metric("Stress Latency", f"{stress_lat:.0f} ms",
              delta=f"{stress_lat - base_lat:+.0f} ms",
              delta_color="inverse")

    base_conf = p.get("confidence", 0)
    stress_conf = sr.get("confidence", 0)
    d3.metric("Baseline Confidence", f"{base_conf:.0%}")
    d4.metric("Stress Confidence", f"{stress_conf:.0%}",
              delta=f"{(stress_conf - base_conf):+.1%}",
              delta_color="normal")


# ══════════════════════════════════════════════════════════════
#  SUCCESS / PASS CRITERIA
# ══════════════════════════════════════════════════════════════
st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
c1, c2 = st.columns(2, gap="large")

with c1:
    st.markdown("<div class='criteria'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-header primary'>Success Criteria</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='criteria-body'>
      ✅ Safety Chat returns evidence-backed answers with citations.<br>
      ✅ Latency under 30 seconds per query.<br>
      ✅ Confidence and evidence IDs logged to CSV.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c2:
    st.markdown("<div class='criteria'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-header stress'>Pass Criteria</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='criteria-body'>
      ✅ Stress conditions return a response (no crash).<br>
      ✅ Rare/conflicting inputs degrade gracefully with lower confidence.<br>
      ✅ All interactions logged to product_metrics.csv.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
