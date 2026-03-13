# TruPharma Competition UI Overhaul — Plan & Tracker

**Date:** 2026-03-13
**Competition:** 2026-03-14 (startup pitch, 5-min video demo)
**Branch:** `integration/vertex-pinecone-merge`
**Goal:** Merge body heatmap + risk calculator from `main` branch, add welcome state, polish UI for competition.

---

## Progress Tracker

| Step | Description | Status | Priority |
|------|------------|--------|----------|
| 1 | Welcome State (branded hero + example query cards) | NOT STARTED | HIGHEST |
| 2 | Port Body Heatmap (dark-theme adapted) | NOT STARTED | HIGH |
| 3 | Port Risk Calculator (dark-theme adapted) | NOT STARTED | HIGH |
| 4 | Visual Polish (animations, input glow, debug removal) | NOT STARTED | MEDIUM |
| 5 | Landing Page Auto-Redirect | NOT STARTED | LOW |
| 6 | Sidebar Cleanup | NOT STARTED | LOW |

**Update status to `DONE` after completing each step.**

---

## Architecture Decision

**Chat-first, features-inline.** The chat page (`primary_demo.py`) is the entire app. Body heatmap and risk calculator appear as expandable sections within each chat response (same pattern as the existing KG visualization). The landing page (`app.py`) auto-redirects to the chat.

---

## Step 1: Welcome State for Empty Chat

**File to modify:** `src/frontend/pages/primary_demo.py`

When `st.session_state.messages` is empty, render a branded welcome in the main chat area (between the disclaimer banner at line ~872 and the conversation history loop at line ~875):

```python
if not st.session_state.messages:
    _render_welcome_state()
```

### What `_render_welcome_state()` should render:

1. **Hero block** (centered):
   - Title: "TruPharma" (in teal `#3df5c8`) + "Safety Intelligence" (in `#e8f0f8`)
   - Subtitle: "AI-powered drug safety analysis backed by FDA labels, FAERS surveillance, and real-time knowledge graphs"

2. **Trust indicators** (4 metric cards in a row using `st.columns(4)`):
   - "150K+" / "Drug Labels"
   - "4.2M+" / "FAERS Reports"
   - "Real-time" / "Knowledge Graph"
   - "Gemini 2.5" / "Flash AI"

3. **Example query cards** (2×3 grid using `st.columns(3)` × 2 rows):
   Each card is a styled `st.button()` that sets `st.session_state["_pending_example"]`:
   - 🔬 "Drug interactions for ibuprofen" — "Check known interactions and severity"
   - 💊 "Aspirin with warfarin safety" — "Evaluate co-administration risks"
   - ⚠️ "Metformin safety warnings" — "Review FDA boxed warnings and precautions"
   - 📋 "Side effects of omeprazole" — "Browse adverse reactions from FAERS"
   - ⚖️ "Ibuprofen vs naproxen comparison" — "Compare adverse reaction profiles"
   - 🔗 "Prednisone co-reported drugs" — "Explore FAERS co-occurrence data"

4. **Prompt hint**: "Ask any drug safety question below ↓" (centered, muted text)

### CSS to add (in the chat-specific CSS block starting at line 42):

```css
/* ── Welcome state ── */
.welcome-hero { text-align: center; padding: 2rem 0 1rem; }
.welcome-title {
    font-family: var(--font-header);
    font-size: 2.8rem; font-weight: 800;
    color: var(--text-primary); line-height: 1.2;
    margin-bottom: 0.5rem;
}
.welcome-title span { color: var(--teal-bright); }
.welcome-subtitle {
    font-family: var(--font-body);
    font-size: 1.05rem; color: var(--text-secondary);
    max-width: 600px; margin: 0 auto 1.5rem;
    line-height: 1.5;
}
.trust-card {
    background: var(--bg-surface);
    border: 1px solid var(--border-default);
    border-radius: var(--radius-md);
    padding: 0.8rem; text-align: center;
    box-shadow: var(--shadow-card);
}
.trust-card .value {
    font-family: var(--font-data);
    font-size: 1.4rem; font-weight: 800;
    color: var(--teal-bright);
}
.trust-card .label {
    font-size: 0.72rem; color: var(--text-secondary);
    text-transform: uppercase; letter-spacing: 0.06em;
}
.example-card-grid { margin: 1.5rem 0; }
```

Style the example card buttons using Streamlit's `st.button` with `use_container_width=True`, and add CSS to make them look like cards with hover effects.

---

## Step 2: Port Body Heatmap

**File to modify:** `src/frontend/pages/primary_demo.py`
**Source:** `git show main:src/frontend/pages/primary_demo.py` (lines ~1400-1744)

### What to cherry-pick:

1. **Constants** — `_REGION_KEYWORDS` dict and `_SYMPTOM_REGION_MAP` dict (built from keywords)
2. **`map_symptoms_to_regions(symptoms)`** — maps symptom strings to body regions, returns counts
3. **`_build_body_heatmap_html(region_counts, symptoms)`** — returns HTML with SVG body overlay
4. **`_extract_symptoms_from_result(r)`** — extracts symptom names from `r["kg_reactions"]`

### Dark-theme adaptations for `_build_body_heatmap_html()`:

| Element | Main branch (light) | Integration (dark) |
|---------|---------------------|-------------------|
| `font-family` in CSS | `"Times New Roman",serif` | `"Quicksand",sans-serif` |
| `.bm-title` color | `#374151` | `#e8f0f8` |
| `.bm-sub` color | `#9ca3af` | `#7a9bbf` |
| `.how-to` color | `#9ca3af` | `#3d5a74` |
| `.legend` color | `#6b7280` | `#7a9bbf` |
| `#zoom-inner` background | `#fff` | `#111e2e` |
| `#zoom-inner` box-shadow | `rgba(0,0,0,0.45)` | `rgba(0,0,0,0.6)` |
| `.zoom-x` color | `#6b7280` | `#7a9bbf` |
| `.zoom-x:hover` color | `#1f2937` | `#e8f0f8` |
| `.zoom-x` background | `rgba(0,0,0,0.08)` | `rgba(255,255,255,0.08)` |
| `.zoom-x:hover` bg | `rgba(0,0,0,0.16)` | `rgba(255,255,255,0.16)` |
| `.zoom-hint` background | `rgba(255,255,255,0.85)` | `rgba(17,30,46,0.9)` |
| `.zoom-hint` color | `#6b7280` | `#7a9bbf` |

### Integration point in `render_message_details()`:

Add after the KG expander block (after line ~827, before the Metrics expander):

```python
# Body Map expander
symptoms = _extract_symptoms_from_result(result)
if symptoms:
    region_counts = map_symptoms_to_regions(symptoms)
    if sum(v for k, v in region_counts.items() if k != "unknown") > 0:
        with st.expander("Adverse-Event Body Map", expanded=False):
            html = _build_body_heatmap_html(region_counts, symptoms)
            components.html(html, height=530, scrolling=False)
            sys_count = region_counts.get("systemic", 0)
            if sys_count:
                st.caption(f"Systemic (whole-body): {sys_count} symptom(s)")
```

**Required asset:** `src/frontend/assets/images/humanbody.jpg` — already exists on both branches.

---

## Step 3: Port Risk Calculator

**File to modify:** `src/frontend/pages/primary_demo.py`
**Source:** `git show main:src/frontend/pages/primary_demo.py` (lines ~720-1050)

### What to cherry-pick:

1. **`_COMORBIDITY_WEIGHTS`** — dict mapping conditions to risk weights
2. **`_compute_personalized_risk(age_group, comorbidities, dosage, duration, concurrent_meds, reactions, interactions)`** — returns `(score, factors, warnings)`
3. **`_build_risk_gauge_html(score)`** — SVG semicircle gauge
4. **`_parse_reference_dose(ingredients)`** — extracts dose from ingredient strength
5. **`_build_dosage_bar_html(dose_val, dose_unit, ingredient, selected_level)`** — dose range bar
6. **`_render_risk_calculator(enriched, drug_name)`** — main render function with Streamlit widgets

### Dark-theme adaptations:

| Element | Main branch (light) | Integration (dark) |
|---------|---------------------|-------------------|
| Gauge track stroke | `#e5e7eb` | `#1a2f45` |
| Gauge font | `Times New Roman,serif` | `Quicksand,sans-serif` |
| Gauge label color | `#6b7280` | `#7a9bbf` |
| Card border | `#ede9fe` | `#2a5278` |
| Card title color | `#7c3aed` | `#7c3aed` (keep) |
| Factor label color | `#374151` | `#e8f0f8` |
| Factor bar track bg | `#f3f4f6` | `#1a2f45` |
| Justification text | `#9ca3af` | `#5a8aaa` |
| Warning div bg | `#fefce8` | `rgba(245,158,11,0.08)` |
| Warning div border | `#d97706` | `#d97706` (keep) |
| Dosage bar segment bgs | `#d1fae5` / `#fef3c7` / `#fee2e2` | `rgba(5,150,105,0.12)` / `rgba(217,119,6,0.12)` / `rgba(220,38,38,0.12)` |
| Dosage bar text | `#374151` | `#e8f0f8` |
| Dosage bar ref text | `#6b7280` | `#7a9bbf` |
| `.card` wrapper | `style='border:2px solid #ede9fe;'` | Remove — use existing dark `.card` class or `style='border:2px solid #2a5278;'` |

### Integration point in `render_message_details()`:

Add after body map expander:

```python
# Risk Calculator expander
if result.get("kg_available") and enriched and (enriched["interactions"] or enriched["reactions"]):
    with st.expander("Personalized Risk Assessment", expanded=False):
        drug_name = result.get("drug_name") or "Drug"
        _render_risk_calculator(enriched, drug_name)
```

**IMPORTANT:** Refactor `render_message_details()` to compute `enriched` once at the top of the KG section and reuse for body map + risk calculator. Currently `enriched` is computed inside the KG expander `with` block. Move it outside:

```python
# Compute enriched KG data ONCE (reused by KG viz, body map, risk calc)
enriched = None
if result.get("kg_available"):
    raw_ix = result.get("kg_interactions", [])
    raw_co = result.get("kg_co_reported", [])
    raw_rx = result.get("kg_reactions", [])
    raw_ing = result.get("kg_ingredients", [])
    if raw_ix or raw_co or raw_rx or raw_ing:
        enriched = _enrich_kg_data(raw_ing, raw_ix, raw_co, raw_rx)
```

---

## Step 4: Visual Polish

**File to modify:** `src/frontend/pages/primary_demo.py`

### 4a. Chat message entrance animation
Add to CSS block:
```css
[data-testid="stChatMessage"] {
    animation: msg-appear 0.3s ease both;
}
@keyframes msg-appear {
    from { opacity: 0; transform: translateY(12px); }
    to   { opacity: 1; transform: translateY(0); }
}
```

### 4b. Enhanced chat input styling
Add to CSS block:
```css
[data-testid="stChatInput"] textarea {
    border: 1px solid var(--teal-dim) !important;
    background: var(--bg-surface) !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--teal-bright) !important;
    box-shadow: 0 0 0 2px rgba(61,245,200,0.1) !important;
}
```

### 4c. Remove debug section
Delete lines 290-317 (the `#region agent log f1239c` block with Debug Info expander).

### 4d. Enhanced spinner text
Change line 906 from:
```python
with st.spinner("Searching FDA labels and knowledge graph..."):
```
to:
```python
with st.spinner("Analyzing drug safety data across FDA labels, FAERS reports, and knowledge graph..."):
```

---

## Step 5: Landing Page Auto-Redirect

**File to modify:** `src/frontend/app.py`

Replace the entire landing page content (after `st.set_page_config()`) with:
```python
st.switch_page("pages/primary_demo.py")
```

Keep `st.set_page_config()` as the first Streamlit call.

---

## Step 6: Sidebar Cleanup

**File to modify:** `src/frontend/pages/primary_demo.py`

1. **Remove** the "Return to Home" button (lines 198-202) — no longer needed
2. **Remove** the Debug Info expander (lines 290-317) — done in Step 4c
3. **Remove** the session timestamp at bottom (lines 320-326) — unnecessary for competition
4. **Keep**: Brand block, New Chat/Clear, Example Queries, Advanced Settings, System Status

---

## Key Context for Any Agent

### Current Branch State
- `integration/vertex-pinecone-merge` — has Vertex AI, Pinecone, Gemini, Neo4j, chat UI working
- `main` — has body heatmap, risk calculator, but light theme and no chat UI
- Both deployed on Streamlit Community Cloud

### Design System
- Dark theme with teal accents (`#3df5c8` primary, navy backgrounds)
- Font: Quicksand (Google Fonts)
- CSS variables defined in `src/frontend/theme.py` — use these, don't hardcode colors
- Key tokens: `--bg-void: #060d14`, `--bg-base: #0b1622`, `--bg-surface: #111e2e`, `--teal-bright: #3df5c8`

### Integration Branch File Structure
```
src/frontend/
├── app.py                    # Landing page (will become redirect)
├── theme.py                  # Shared CSS design system
├── assets/images/humanbody.jpg
└── pages/
    ├── primary_demo.py       # Main chat page (929 lines) — PRIMARY EDIT TARGET
    ├── signal_heatmap.py     # Placeholder
    ├── opioid_dashboard.py   # Opioid intelligence
    └── stress_test.py        # Edge-case testing
```

### Backend (no changes needed)
- RAG engine: `src/rag/engine.py` — `run_rag_query()` returns dict with `answer`, `evidence`, `kg_*`, `latency_ms`, etc.
- KG data in results: `kg_available`, `kg_interactions`, `kg_co_reported`, `kg_reactions`, `kg_ingredients`, `kg_identity`
- Embeddings: Vertex AI `text-embedding-004` (768-dim)
- LLM: Gemini 2.5 Flash (Vertex AI preferred, direct API fallback)
- Vector store: Pinecone (FAISS fallback)

### Demo Flow (5 min video)
1. App opens → welcome state with branded hero + example cards
2. Click example → response with citations → expand KG graph → click nodes
3. Expand Body Map → anatomical heatmap with severity colors
4. Expand Risk Assessment → set Elderly/Liver disease/High dose → gauge goes red
5. Follow-up question → show conversational context
6. Flash system status → mention architecture → close with vision

---

## Verification Command
```bash
cd /Users/nithinreddy/TruPharma-Clinical-Intelligence && python3 -m streamlit run src/frontend/app.py --server.port 8501
```
