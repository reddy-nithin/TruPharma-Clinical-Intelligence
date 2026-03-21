# Changelog — TruPharma Clinical Intelligence

All notable UI and frontend changes made during the current session (March 21, 2026), building on top of commit `3da11e9`.

---

## Summary

Two build plans were executed against `src/frontend/pages/primary_demo.py`, plus supporting changes to the landing page, Streamlit config, and new 3D model assets:

1. **UI Updates Build Plan** — Personalized risk assessment calculator, `@st.dialog` sidebar modal, two-column adaptive detail panel with compact KG rendering
2. **Body Chart Build Plan** — Complete overhaul of the body map from a 2D image overlay to an interactive 3D `<model-viewer>` with per-gender GLB models, corrected hotspot coordinates, and semi-transparent rendering

---

## Files Changed

| File | Type | Description |
|------|------|-------------|
| `src/frontend/app.py` | Modified | Replaced auto-redirect with a styled landing page |
| `src/frontend/pages/primary_demo.py` | Modified | +348 / -174 lines across risk calc, KG panel, body map, layout |
| `src/frontend/.streamlit/config.toml` | Modified | Enabled static file serving for GLB models |
| `logs/product_metrics.csv` | Modified | New query log entry from testing |
| `src/frontend/assets/male.glb` | Added | Male 3D body model for body map |
| `src/frontend/assets/female.glb` | Added | Female 3D body model for body map |
| `src/frontend/static/male.glb` | Added | Static-served copy of male model |
| `src/frontend/static/female.glb` | Added | Static-served copy of female model |

---

## 1. Landing Page (`app.py`)

**Before:** The home page immediately called `st.switch_page("pages/primary_demo.py")`, auto-redirecting users to the Safety Chat with no landing experience.

**After:** A full landing page with:

- Centered hero section displaying the **TruPharma** brand title and subtitle ("AI-Powered Clinical Intelligence Platform")
- Theme injection via `inject_theme()`
- Four navigation buttons in a centered column, each with a descriptive caption:
  - **Safety Chat — Drug Intelligence** (primary action)
  - **Signal Heatmap — FAERS Explorer**
  - **Opioid Dashboard**
  - **Stress Test**
- Sets `st.session_state["_reset_chat"] = True` so navigating home always clears the previous chat session

---

## 2. 3D Body Chart Overhaul (`primary_demo.py`)

Replaced the 2D `humanbody.jpg` image-overlay body map with an interactive 3D visualization using Google's `<model-viewer>` web component and `.glb` mesh files.

### 2a. Per-Gender Hotspot Coordinates

Added a `_HOTSPOT_COORDS` dictionary with separate coordinate sets for male and female models (derived from trimesh bounding box analysis):

- **Male model** — Y range: -0.858 to +0.858
- **Female model** — Y range: -0.842 to +0.842
- Regions mapped: head, chest, abdomen, arms (L/R), legs (L/R), skin, systemic
- Z coordinates pushed to ~0 so hotspots render **inside** the semi-transparent body volume

### 2b. Camera & Lighting Fixes

| Attribute | Old | New |
|-----------|-----|-----|
| shadow-intensity | 0.4 | 0.3 |
| exposure | 1.1 | 0.9 |
| tone-mapping | *(unset)* | commerce |
| camera-orbit | 0deg 75deg 2.5m | 0deg 75deg 3.8m |
| min-camera-orbit | auto auto 1.2m | auto auto 2m |
| max-camera-orbit | auto auto 5m | auto auto 6m |
| field-of-view | 30deg | 28deg |
| Container height | 420px | 480px |

These changes fix body clipping, normalize brightness between male/female models, and give users a better default viewing angle.

### 2c. Semi-Transparent Rendering

A JavaScript `load` event listener traverses the Three.js scene graph exposed by `<model-viewer>` and sets all mesh materials to 55% opacity. This makes the glowing hotspot dots visible **through** the body surface rather than hidden behind it.

### 2d. Skin & Systemic Hotspot Styles

- **Skin** — dashed-border ring (transparent fill, dashed stroke in severity color)
- **Systemic** — solid dot with a white semi-transparent border (`rgba(255,255,255,0.3)`)
- Both regions are now included in the severity scaling calculation (`body_max` no longer excludes them)

### 2e. Gender Toggle & Interaction

- Male/Female toggle buttons switch both the `.glb` model source and the hotspot coordinate set
- `camera-change` listener detects user interaction and disables auto-rotate
- Reset View button restores default orbit and re-enables auto-rotate
- Rich tooltips on hover show region name, symptom count, and description

### 2f. Body Map Panel Height

Increased `components.html()` height from 530px to 600px in `_render_bodymap_panel` to accommodate the taller 3D viewer.

---

## 3. Personalized Risk Assessment Calculator (`primary_demo.py`)

### 3a. Comorbidity Weights & Scoring Engine

Added `_COMORBIDITY_WEIGHTS` dictionary and `_compute_personalized_risk()` function:

- **10 comorbidity conditions** with clinical weights (0.4–0.9): liver disease, kidney disease, heart disease, pregnancy/nursing, blood disorders, GI disorders, diabetes, hypertension, asthma, immunocompromised
- Scoring considers: severe/moderate interactions, severe/moderate reactions, age group (pediatric/adult/elderly), selected comorbidities, dosage level, treatment duration, and concurrent medication count
- Returns a tuple of `(score, factors_list, warnings_list)` with clinical justifications for each contributing factor
- Score clamped to 0.0–10.0

### 3b. Risk Gauge SVG

`_build_risk_gauge_html(score)` renders a semicircle gauge:

- 0–3.9: Green (`#059669`) — "LOW RISK"
- 4–6.9: Amber (`#d97706`) — "MODERATE"
- 7–10: Red (`#dc2626`) — "HIGH RISK"
- Animated arc via `stroke-dasharray` with CSS transition on dark background track

### 3c. Dosage Reference Bar

`_parse_reference_dose()` and `_build_dosage_bar_html()` parse ingredient strength data and render a 3-segment bar (Low / Standard / High) with the selected level highlighted in the corresponding risk color.

### 3d. Calculator UI

`_render_risk_calculator(enriched, drug_name)` renders a two-column layout:

- **Left column — Patient Context:** age group selectbox, comorbidities multiselect, dosage level + duration selectors, dosage reference bar, concurrent medications number input
- **Right column — Results:** risk gauge SVG, factor breakdown with colored contribution bars and justification text, contextual clinical warnings with amber-bordered cards
- Footer disclaimer about heuristic nature of the model

---

## 4. `@st.dialog` Risk Modal (`primary_demo.py`)

Added `_show_risk_dialog(enriched, drug_name)` decorated with `@st.dialog("Personalized Risk Assessment", width="large")`.

**Sidebar integration:**
- After the system status section, a divider and "Risk Assessment" header appear
- Scans message history in reverse for the latest assistant response with KG data
- If found: displays a button `"⚕️ Open Risk Calculator — {Drug}"` that opens the risk calculator in a centered Streamlit modal
- If not found: shows a caption "Submit a query to enable risk assessment"

This replaced the previous inline `st.expander("Interactive Calculator")` approach with a cleaner modal pattern.

---

## 5. Two-Column Adaptive Detail Panel (`primary_demo.py`)

### 5a. Layout

- **No detail open:** chat takes full width (`10 : 0.01` column ratio)
- **Detail panel open:** chat shrinks to 60%, detail panel takes 40% (`6 : 4` ratio, `gap="medium"`)

### 5b. Pill Buttons

Rebalanced the pill button columns from `[1, 1, 1, 1, 4]` to `[2, 1, 1, 1, 1, 2]` for better centering:

| Button | Panel | Disabled when |
|--------|-------|---------------|
| 📊 KG | Knowledge graph | No KG data |
| 📋 Evidence | Source evidence cards | No evidence |
| 🫁 Body Map | 3D symptom heatmap | No symptoms extracted |
| 📈 Metrics | Query performance stats | *(never)* |

### 5c. KG Panel Summary Cards

Added a row of three summary metric cards above the compact KG graph:

- **Most Common Reaction** — highest report-count adverse reaction (red text)
- **Severe Interaction** — first severe-classified interaction, or "None" in green
- **Total Relationships** — count of all ingredient + interaction + co-reported + reaction relationships

### 5d. Compact KG Mode

`_build_kg_network_html()` now accepts `compact=True`:

| Parameter | Default | Compact |
|-----------|---------|---------|
| RADIUS | 210 | 130 |
| MAX_ITEMS | 8 | 6 |
| center_font | 16 | 13 |
| net_height | 470px | 350px |

The detail panel KG uses compact mode with a 440px container; the inline chat KG uses the full-size defaults.

---

## 6. Session State & Navigation (`primary_demo.py`)

### 6a. Chat Reset on Home Navigation

When `app.py` sets `st.session_state["_reset_chat"] = True`, `primary_demo.py` clears all session state on next load:

- `messages` → `[]`
- `kg_poll_count` → `0`
- `active_detail` → `None`
- `show_risk_calc` → `False`

### 6b. New Chat / Clear Improvements

- "New Chat" button now also clears `active_detail` and `show_risk_calc` (previously only cleared messages)
- Added `show_risk_calc` to session state initialization

### 6c. Sidebar Home Button

Added a `"🏠 Home"` button at the top of the sidebar that navigates back to `app.py`.

---

## 7. Streamlit Config (`.streamlit/config.toml`)

Added `[server]` section with `enableStaticServing = true` to allow Streamlit to serve the `.glb` 3D model files from the `static/` directory at the `app/static/` URL path.

---

## 8. New Assets

| File | Size | Purpose |
|------|------|---------|
| `src/frontend/assets/male.glb` | ~12.7K lines | Male body 3D mesh for body map |
| `src/frontend/assets/female.glb` | ~24.3K lines | Female body 3D mesh for body map |
| `src/frontend/static/male.glb` | *(copy)* | Static-served copy for `<model-viewer>` |
| `src/frontend/static/female.glb` | *(copy)* | Static-served copy for `<model-viewer>` |

---

## Architecture Diagram

```
app.py (Landing Page)
  ├── pages/primary_demo.py (Safety Chat)
  │     ├── RAG query pipeline → run_rag_query()
  │     ├── Two-column layout (chat | detail panel)
  │     │     ├── KG Panel (compact vis.js + summary cards)
  │     │     ├── Evidence Panel (source cards)
  │     │     ├── Body Map Panel (3D model-viewer + hotspots)
  │     │     └── Metrics Panel (latency, confidence)
  │     ├── Risk Assessment Calculator (inline + @st.dialog)
  │     └── Sidebar (Home, New Chat, System Status, Risk button)
  ├── pages/signal_heatmap.py
  ├── pages/opioid_dashboard.py
  └── pages/stress_test.py
```
