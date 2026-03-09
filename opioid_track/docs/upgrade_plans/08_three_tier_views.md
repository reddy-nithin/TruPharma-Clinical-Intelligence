# Sub-Plan 08: Three-Tier View System

## Priority: After Sub-Plans 01-07 (needs all pages to exist)
## Depends on: Sub-Plan 02 (theme system for session state patterns)

---

## Goal
Replace the binary "Layman's View" toggle from POTENTIAL_UPGRADES.md with a 3-tier system: Executive (high-level KPIs), Clinical (current behavior), Research (raw data + statistics). Each page adapts its content depth based on the active mode. This is critical for demo versatility — switch modes live during investor pitches.

## Pre-Requisites
- Sub-Plan 02 (Theme) should be COMPLETED (establishes session state patterns)
- All page files should exist (including new Supply Chain page from Sub-Plan 05)
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/dashboard/opioid_app.py` — sidebar structure
2. `opioid_track/dashboard/components/theme.py` — session state pattern to follow
3. All page files in `opioid_track/dashboard/pages/` — understand what each page shows
4. `opioid_track/agents/opioid_watchdog.py` — agent responses to adjust by mode

---

## View Mode Specification

| Aspect | Executive | Clinical | Research |
|--------|-----------|----------|----------|
| **Terminology** | Plain English: "Safety Signal Strength" not "PRR", "Risk Score" not "EBGM" | Standard clinical vocabulary (current) | Full technical: show method names, formulas |
| **Data depth** | KPI cards + 1-2 summary charts per section + narrative text | All current panels + charts + tables | All panels + raw contingency tables + CIs + p-values |
| **Drug Explorer** | Drug name, risk score badge, top 3 warnings, "Is it safe?" summary | Current full view | Add: raw API responses, RxCUI lookup chain, FAERS counts |
| **Landscape** | 2 charts max (treemap + danger matrix), narrative | All 5 current charts | Add: data sources, observation counts, last-updated timestamps |
| **Geography** | Choropleth + top 5 states narrative | Current full view | Add: raw county data download, methodology notes |
| **Demographics** | Headline stat + 1 chart per section | Current full view | Add: source citations, confidence intervals, rate calculations |
| **Signals** | "X drugs have safety alerts" + top signals list | Current heatmap + detail | Add: contingency tables, χ² values, CI bounds, raw FAERS counts |
| **Watchdog** | Simplified: "Is this dose dangerous? Yes/No + why" | Current full tools | Add: show calculations, formulas, data sources for each output |
| **Supply Chain** | "X recalls active, Y drugs at risk" | Current dashboard | Add: raw FDA API responses, historical recall JSON |
| **Watchdog Agent** | Short, non-technical answers (~2-3 sentences) | Current behavior | Detailed with citations, raw data references, methodology |

---

## Agent Assignment

### Agent A (Worktree: `view-modes`) — Create View Mode Module

**Create file: `opioid_track/dashboard/components/view_mode.py`**

```python
"""
Three-tier view system: Executive / Clinical / Research.
Controls content depth across all dashboard pages.
"""
import streamlit as st
from typing import Literal

ViewMode = Literal["executive", "clinical", "research"]

VIEW_LABELS = {
    "executive": "Executive",
    "clinical": "Clinical",
    "research": "Research",
}

VIEW_DESCRIPTIONS = {
    "executive": "High-level KPIs and plain-English summaries",
    "clinical": "Standard clinical intelligence view",
    "research": "Full technical detail with raw data",
}

# Terminology mappings: technical term → executive-friendly term
TERM_MAPPINGS = {
    "PRR": "Signal Strength (Proportional)",
    "ROR": "Signal Strength (Odds-Based)",
    "EBGM": "Bayesian Signal Score",
    "EB05": "Bayesian Lower Bound",
    "MME": "Morphine Equivalent Dose",
    "RxCUI": "Drug Code",
    "NDC": "Product Code",
    "FAERS": "FDA Safety Reports",
    "LD50": "Estimated Lethal Dose",
    "therapeutic_index": "Safety Margin",
    "potency_vs_morphine": "Relative Strength",
    "consensus_signal": "Confirmed Safety Alert",
    "contingency_table": "Report Comparison Table",
    "chi_squared": "Statistical Significance",
    "confidence_interval": "Uncertainty Range",
    "disproportionality": "Unusual Reporting Pattern",
    "pharmacovigilance": "Drug Safety Monitoring",
}


def render_view_selector() -> None:
    """
    Render view mode selector in the sidebar.
    Call at the top of sidebar, after theme toggle (if present), before navigation.

    Uses st.sidebar.radio with horizontal layout.
    Stores selection in st.session_state.view_mode.
    """
    current = st.session_state.get("view_mode", "clinical")
    mode = st.sidebar.radio(
        "View Mode",
        options=list(VIEW_LABELS.keys()),
        format_func=lambda x: VIEW_LABELS[x],
        index=list(VIEW_LABELS.keys()).index(current),
        horizontal=True,
        help="Executive: simplified KPIs | Clinical: standard view | Research: full technical detail",
    )
    st.session_state.view_mode = mode


def get_view_mode() -> ViewMode:
    """Returns current view mode."""
    return st.session_state.get("view_mode", "clinical")


def is_executive() -> bool:
    return get_view_mode() == "executive"


def is_clinical() -> bool:
    return get_view_mode() == "clinical"


def is_research() -> bool:
    return get_view_mode() == "research"


def translate_term(technical_term: str) -> str:
    """
    In executive mode, translate technical terms to plain English.
    In clinical/research mode, return as-is.
    """
    if is_executive():
        return TERM_MAPPINGS.get(technical_term, technical_term)
    return technical_term


def show_if_clinical_or_above(content_func):
    """Only render content in Clinical or Research mode."""
    if not is_executive():
        content_func()


def show_if_research(content_func):
    """Only render content in Research mode."""
    if is_research():
        content_func()


def executive_summary(text: str) -> None:
    """
    Show a narrative summary block only in Executive mode.
    Styled with a subtle background and larger text.
    """
    if is_executive():
        st.markdown(f"""
        <div style="background: var(--accent-teal-bg); border-left: 3px solid var(--accent-teal);
                     padding: 16px; border-radius: 4px; margin: 12px 0;">
            <p style="font-size: 1.1em; line-height: 1.6; margin: 0;">{text}</p>
        </div>
        """, unsafe_allow_html=True)
```

**Done criteria:** Module imports. `get_view_mode()` returns correct mode. `translate_term()` works in executive mode.

---

### Agent B (Sequential, largest task) — Modify All Page Files

**This is the most time-consuming agent. Work page by page.**

**For EACH page file, follow this pattern:**

```python
# At the top of the page function:
from opioid_track.dashboard.components.view_mode import (
    get_view_mode, is_executive, is_clinical, is_research,
    translate_term, show_if_clinical_or_above, show_if_research,
    executive_summary,
)

# Example pattern for a section:
def render_signals_page():
    mode = get_view_mode()

    # Executive mode: simplified summary
    if is_executive():
        executive_summary(
            f"Our system detected <b>{total_signals}</b> confirmed safety alerts "
            f"across <b>{drugs_scanned}</b> opioid drugs. "
            f"<b>{critical_count}</b> require immediate attention."
        )
        # Show only top signals table, no heatmap
        render_top_signals_table(signals[:10])
        return  # Exit early — don't show the rest

    # Clinical mode: current behavior (no changes needed)
    render_summary_metrics()
    render_heatmap()
    render_signal_detail()

    # Research mode: add extra detail
    if is_research():
        st.markdown("### Raw Signal Data")
        render_contingency_tables()
        render_raw_faers_counts()
        render_method_parameters()
```

**Page-by-page changes:**

**1. `drug_explorer.py`**
- Executive: Drug name card (simplified), risk badge, top 3 warnings as bullet points, "Bottom line: [safe/risky/dangerous]" narrative
- Clinical: Current full view
- Research: Add raw RxCUI data, API response viewer, pharmacology JSON

**2. `landscape.py`**
- Executive: Only treemap + danger matrix. Narrative: "There are X opioids tracked. Y are classified as extreme danger."
- Clinical: All 5 charts
- Research: Add data source notes, observation counts per chart

**3. `geography.py`**
- Executive: Choropleth + "Top 5 most affected states: ..." narrative
- Clinical: Full view with bar chart, county table
- Research: Add downloadable county CSV, methodology notes, data freshness info

**4. `demographics.py`**
- Executive: Headline: "Adults 25-44 are most affected. Men are X times more likely." + 1 chart
- Clinical: Full age/sex/race breakdowns
- Research: Add confidence intervals, rate calculations, CDC source links

**5. `signals.py`**
- Executive: "X confirmed safety alerts found" + top 10 signals list
- Clinical: Heatmap + detail view
- Research: Add 2×2 contingency tables, χ² values, CI bounds, raw FAERS counts per cell

**6. `watchdog.py`**
- Executive: Simplified dose calculator ("Is this dose dangerous? Yes/No"), simplified comparator
- Clinical: Current full tools
- Research: Show MME calculation steps, LD50 source data, formula breakdowns

**7. `supply_chain.py`** (if exists from Sub-Plan 05)
- Executive: "X active recalls. Y drugs at risk." + top recalls list
- Clinical: Full dashboard
- Research: Raw FDA API responses, recall JSON viewer

**Modify: `opioid_track/dashboard/opioid_app.py`**
1. Import `render_view_selector` from view_mode module
2. In sidebar section, add `render_view_selector()` call (after theme toggle, before navigation)

**Done criteria:** Toggle between modes on every page — content depth changes appropriately. Executive hides technical detail. Research shows extra data.

---

### Agent C (Sequential after B) — Modify Watchdog Agent

**Modify: `opioid_track/agents/opioid_watchdog.py`**

1. Import `get_view_mode` from view_mode module
2. In `query_intelligence_brief()` and other response methods:
   - **Executive mode:** Shorter responses (2-3 sentences), no jargon, no citations
   - **Clinical mode:** Current behavior
   - **Research mode:** Longer responses with citations, methodology notes, raw data references

```python
def _format_response(self, detailed_response: str, executive_summary: str) -> str:
    mode = get_view_mode()
    if mode == "executive":
        return executive_summary
    elif mode == "research":
        return detailed_response + "\n\n**Sources & Methodology:**\n..."
    return detailed_response  # clinical mode
```

**Done criteria:** Watchdog responses adapt to view mode.

---

## Execution Order
1. **Agent A** creates view_mode.py (worktree)
2. **Agent B** modifies all page files (sequential — this is the bulk of the work)
3. **Agent C** modifies watchdog agent (sequential after B)
4. Visual verification: toggle through all 3 modes on every page
5. Commit: `git commit -m "feat(opioid): add 3-tier view system (Executive/Clinical/Research)"`

## Checkpoint Protocol
**This is the largest sub-plan. Expect multiple agent sessions.**
- **Mid-Agent B, page 1-2 done:** "Checkpoint: drug_explorer and landscape adapted. Next: geography.py"
- **Mid-Agent B, page 3-4 done:** "Checkpoint: geography and demographics adapted. Next: signals.py"
- **Mid-Agent B, page 5-7 done:** "Checkpoint: signals, watchdog, and supply_chain adapted. Next: Agent C"

## Final Verification
```bash
# Toggle to Executive mode → every page shows simplified content
# Toggle to Clinical mode → every page shows current (default) content
# Toggle to Research mode → every page shows extra technical detail
# Watchdog Intelligence Brief adapts response length/detail
```
Update `00_STATUS.md` to "COMPLETED".
