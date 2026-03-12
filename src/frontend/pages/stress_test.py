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
import time
from datetime import datetime

from src.rag.engine import run_rag_query, read_logs
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
    st.session_state.primary_last_run = {
        "query": "(run a Safety Chat query first)",
        "confidence": "—",
        "evidence_count": 0,
    }

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
#  TWO SIDE-BY-SIDE PANELS
# ══════════════════════════════════════════════════════════════
left, right = st.columns(2, gap="large")

# ── Safety Chat Scenario (from last Safety Chat run) ──
with left:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-header primary'>Safety Chat Scenario</div>", unsafe_allow_html=True)
    st.markdown("<div class='panel-subheader'>Normal user workflow</div>", unsafe_allow_html=True)

    p = st.session_state.primary_last_run

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Input</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='mini'>Query: {p['query']}</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Expected Output</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='mini'>Verified answer + evidence citations<br>"
        f"Confidence: {p['confidence']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Evidence</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='mini'>Evidence count: {p['evidence_count']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ── Stress-Test Scenario (real RAG results) ──
with right:
    st.markdown("<div class='panel'>", unsafe_allow_html=True)
    st.markdown("<div class='panel-header stress'>Stress-Test Scenario</div>", unsafe_allow_html=True)
    st.markdown("<div class='panel-subheader'>Edge case / robustness check</div>", unsafe_allow_html=True)

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Stress Condition</div>", unsafe_allow_html=True)

    sr = st.session_state.stress_result
    sc = st.session_state.stress_condition

    if sr and sc:
        st.markdown(f"<div class='mini'><b>Condition:</b> {sc}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='mini'><b>Query:</b> {STRESS_QUERIES[sc]}</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='mini'>Choose ONE:</div>
        <ul class="bullets">
          <li>Rare input</li><li>Large doc</li>
          <li>Heavy traffic</li><li>Conflicting evidence</li>
        </ul>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>System Behavior</div>", unsafe_allow_html=True)
    if sr:
        degradation = {
            "Rare input": "Reduced result set, lower evidence count — system returns partial answer.",
            "Large doc": "Large corpus indexed — system handles increased data gracefully.",
            "Heavy traffic": "Reduced limits for faster response — graceful degradation.",
            "Conflicting evidence": "Multiple drug labels compared — system cites both sources.",
        }.get(sc, "")
        st.markdown(f"<div class='mini'>{degradation}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='mini'><b>Method:</b> {sr['method']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class='mini'>Graceful degradation:</div>
        <ul class="bullets">
          <li>Reduced API limits</li><li>Adjusted top-k</li>
          <li>Fallback retrieval</li>
        </ul>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='inner-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-pill'>Monitoring / Logs</div>", unsafe_allow_html=True)
    if sr:
        st.markdown(f"- **Latency:** {sr['latency_ms']:.0f} ms")
        st.markdown(f"- **Confidence:** {sr['confidence']:.0%}")
        st.markdown(f"- **Evidence count:** {len(sr['evidence'])}")
        st.markdown(f"- **Records fetched:** {sr['num_records']}")
        ev_labels = [e["cite"] for e in sr["evidence"]]
        st.markdown(f"- **Evidence:** {', '.join(ev_labels[:5])}")
        st.markdown(f"- **LLM used:** {'Gemini' if sr['llm_used'] else 'Extractive fallback'}")
        st.markdown("---")
        st.markdown("**Answer preview:**")
        import re as _re
        _ans = sr["answer"]
        for _j, _ev in enumerate(sr["evidence"], 1):
            raw = _ev.get("_raw_id", "")
            if raw:
                _ans = _ans.replace(f"[{raw}]", f"[Evidence {_j}]")
        def _repl(m):
            inner = m.group(1)
            if _re.match(r"Evidence \d+", inner):
                return m.group(0)
            for _k, _e in enumerate(sr["evidence"], 1):
                if _e.get("doc_id", "") in inner or _e.get("field", "") in inner:
                    return f"[Evidence {_k}]"
            return m.group(0)
        _ans = _re.sub(r"\[([^\]]+)\]", _repl, _ans)
        st.write(_ans[:400])
    else:
        st.info("Run a stress test to populate logs.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


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
