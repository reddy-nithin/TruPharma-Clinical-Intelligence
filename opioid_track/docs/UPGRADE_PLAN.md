# TruPharma Opioid Track — Comprehensive Upgrade Plan

> **Primary Audience:** Investors / Demo
> **Approach:** Real trained models, high visual impact, production-ready architecture
> **Baseline:** Current app has 6 dashboard pages, FAERS pharmacovigilance (PRR/ROR/EBGM), CDC/CMS epidemiology, NLP label mining, pharmacology data, and OpioidWatchdog agent.

---

## Phase 1: Foundation & Performance (Build First)

### 1.1 Performance Caching Layer
**Why first:** The 44MB `opioid_registry.json` is loaded on every page via the singleton registry. API calls to OpenFDA, PubChem, ChemBL hit rate limits. Caching must be in place before adding more data-intensive features.

**Implementation:**
- **File:** `opioid_track/core/cache.py`
- Replace raw JSON loading with SQLite-backed cache (no external Redis dependency — keeps deployment simple)
- Cache tables: `registry_cache`, `api_response_cache`, `signal_cache`, `forecast_cache`
- TTL-based expiration: registry = 24h, API responses = 1h, signals = 6h, forecasts = 12h
- Lazy-load registry sections (drugs, NDC lookup, MME reference) independently instead of full 44MB blob
- Add `@cached` decorator for any function that hits external APIs
- **Fallback:** If SQLite cache is empty/expired, fall back to current JSON loading behavior

**Files to modify:**
- `opioid_track/core/registry.py` — swap JSON load for SQLite reads
- `opioid_track/core/signal_detector.py` — use `@cached` for OpenFDA API calls
- `opioid_track/config.py` — add cache config (TTL values, DB path)

---

### 1.2 FastAPI Layer
**Why:** Enables external integrations, makes the platform feel enterprise-grade in demos, and decouples data logic from Streamlit UI.

**Implementation:**
- **File:** `opioid_track/api/app.py` — FastAPI application
- **File:** `opioid_track/api/routes/` — route modules

**Endpoints:**
| Route | Method | Description |
|-------|--------|-------------|
| `/api/v1/drugs/{rxcui}` | GET | Full opioid profile |
| `/api/v1/drugs/search` | GET | Free-text drug search |
| `/api/v1/drugs/{rxcui}/signals` | GET | FAERS signals for drug |
| `/api/v1/drugs/{rxcui}/risk` | GET | Composite risk score |
| `/api/v1/drugs/compare` | POST | Side-by-side comparison |
| `/api/v1/mme/calculate` | POST | MME calculation |
| `/api/v1/geographic/{state}` | GET | State/county risk profiles |
| `/api/v1/geographic/forecast` | GET | Predicted overdose rates |
| `/api/v1/supply-chain/alerts` | GET | Active recalls & shortages |
| `/api/v1/watchdog/query` | POST | Natural language query |
| `/api/v1/alerts/subscribe` | POST | Subscribe to push alerts |
| `/api/v1/fhir/risk-assessment/{rxcui}` | GET | FHIR RiskAssessment resource |

**Auth:** API key-based (simple, demo-friendly). Store keys in env vars.
**Docs:** Auto-generated Swagger UI at `/docs` (FastAPI built-in — impressive in demos).

**Files to create:**
- `opioid_track/api/app.py`
- `opioid_track/api/routes/drugs.py`
- `opioid_track/api/routes/analytics.py`
- `opioid_track/api/routes/geographic.py`
- `opioid_track/api/routes/alerts.py`
- `opioid_track/api/models.py` (Pydantic response schemas)

---

## Phase 2: Predictive Intelligence (Core Differentiator)

### 2.1 Geographic Overdose Forecasting
**Data available:** 81K+ CDC mortality records (2015-2022), 3,148 county profiles with prescribing rates, death rates, pills per capita.

**Implementation:**
- **File:** `opioid_track/ml/geographic_forecaster.py`
- **Model:** Facebook Prophet (interpretable, handles trend + seasonality, produces uncertainty intervals)
  - Train per-state models on monthly mortality time-series
  - Features: prescribing rate (lagged), pills per capita, population density
  - Output: 12-month and 24-month forecasts with 80%/95% prediction intervals
- **Validation:** Walk-forward validation — train on 2015-2020, validate on 2021-2022, then retrain on full data for production forecasts
- **Spatial component:** After per-state Prophet models, apply spatial smoothing using neighboring-state averages to capture geographic spillover effects
- **Dashboard integration:** New "Predictive" sub-tab in Geographic Intelligence page
  - Forecast line chart with confidence bands (shaded area)
  - "Emerging Hotspot" map highlighting states with accelerating trends
  - Model performance metrics (MAPE, coverage of prediction intervals)

**Files to create:**
- `opioid_track/ml/geographic_forecaster.py`
- `opioid_track/ml/model_validation.py`
- `opioid_track/tests/test_forecaster.py`

**Files to modify:**
- `opioid_track/dashboard/pages/geography.py` — add forecast tab
- `opioid_track/config.py` — add ML config (forecast horizon, confidence levels)

---

### 2.2 Clinical Risk Probability Score
**Data available:** FAERS consensus signals, MME factors, therapeutic indices, LD50 estimates, potency rankings, danger classifications.

**Implementation:**
- **File:** `opioid_track/ml/risk_scorer.py`
- **Approach:** Transparent weighted composite index (not black-box) — critical for clinical/investor credibility
  - **Inputs (normalized 0-1):**
    1. FAERS consensus signal strength (number of consensus signals × average method agreement)
    2. MME conversion factor (higher = more potent = riskier)
    3. Inverse therapeutic index (lower TI = narrower safety margin)
    4. Lethal dose proximity (at standard doses, how close to estimated LD)
    5. DEA schedule severity (CII=1.0, CIII=0.7, CIV=0.4, CV=0.2)
    6. Receptor binding profile penalty (full mu-agonist > partial agonist > antagonist)
  - **Weight learning:** Use logistic regression calibrated against known high-risk vs. lower-risk opioids (fentanyl/carfentanil = high, codeine/tramadol = lower) to learn optimal weights
  - **Output:** 0-100 "Clinical Risk Index" with tier labels (Critical / High / Elevated / Moderate / Lower)
  - **Explainability panel:** Show contribution of each factor to final score (waterfall chart)

- **Dashboard integration:**
  - Risk badge on every drug in Drug Explorer
  - Sortable risk column in all drug tables
  - Risk comparison in Watchdog Danger Comparator

**Files to create:**
- `opioid_track/ml/risk_scorer.py`
- `opioid_track/tests/test_risk_scorer.py`

**Files to modify:**
- `opioid_track/dashboard/pages/drug_explorer.py` — add risk badge + waterfall chart
- `opioid_track/dashboard/pages/watchdog.py` — integrate risk score in comparator
- `opioid_track/agents/opioid_watchdog.py` — expose risk score in queries

---

### 2.3 Supply Chain Risk Dashboard (Replaces ARIMA)
**Rationale:** FDA drug recalls are sparse/irregular events unsuitable for ARIMA. A real-time monitoring dashboard is more practical and impressive.

**Implementation:**
- **File:** `opioid_track/core/supply_chain_monitor.py`
- **Data sources:**
  1. **FDA Enforcement API** (`api.fda.gov/drug/enforcement.json`) — recall alerts filtered to opioid products
  2. **FDA Drug Shortage Database** (CDER) — current shortage status for opioids
  3. **OpenFDA Drug Labels** — manufacturer count per product (supply concentration risk)
- **Computed metrics:**
  - **Supply Vulnerability Score (0-100):** Weighted composite of:
    - Number of active manufacturers (fewer = more vulnerable)
    - Recent recall history (count + severity in last 24 months)
    - Current shortage status (active shortage = high vulnerability)
    - Geographic concentration of production
  - **Recall Severity Tracking:** Class I (most serious) / II / III breakdown
  - **Shortage Timeline:** Historical shortage episodes with duration

- **Dashboard page:** New "Supply Chain" page or sub-tab in Watchdog Tools
  - Active recall alerts (filterable by severity, date, opioid)
  - Current shortage status for all tracked opioids
  - Supply vulnerability heatmap (drug × vulnerability factor)
  - Trend chart of recall frequency over time

**Files to create:**
- `opioid_track/core/supply_chain_monitor.py`
- `opioid_track/dashboard/pages/supply_chain.py`
- `opioid_track/tests/test_supply_chain.py`

**Files to modify:**
- `opioid_track/dashboard/opioid_app.py` — add Supply Chain to navigation
- `opioid_track/config.py` — add FDA enforcement API config

---

## Phase 3: Visual Upgrades (Wow-Factor)

### 3.1 DeckGL 3D Heat Globe (Geographic Intelligence)
**What:** Replace 2D Plotly choropleth with a 3D extruded column map using `pydeck`.

**Implementation:**
- **File:** `opioid_track/dashboard/components/deckgl_map.py`
- **Function:** `render_3d_geographic_map(dataframe, metric_col, lat_col, lon_col)`
- Dark map style (Carto Dark Matter — no Mapbox token needed)
- `ColumnLayer` with height proportional to selected metric (mortality rate, prescribing rate, etc.)
- Color gradient: teal (low) → amber (medium) → red (high) matching existing app palette
- Auto-rotation on load, interactive pitch/yaw controls
- Tooltip on hover showing state/county name + metric value
- Toggle between 2D (existing choropleth) and 3D (DeckGL) views

**Files to create:**
- `opioid_track/dashboard/components/deckgl_map.py`

**Files to modify:**
- `opioid_track/dashboard/pages/geography.py` — add 2D/3D toggle, integrate DeckGL component

---

### 3.2 Dynamic Knowledge Graph (Signal Detection / Drug Explorer)
**What:** Interactive force-directed network showing drug → reactions, drug → mechanisms, drug → signals relationships.

**Implementation:**
- **File:** `opioid_track/dashboard/components/network_graph.py`
- **Function:** `render_knowledge_graph(drug_name, nlp_insights, signal_data, pharmacology_data)`
- **Library:** `streamlit-agraph` (vis.js wrapper)
- **Node types (color-coded):**
  - Central: Drug (teal, large)
  - Mechanism: Receptor targets (purple)
  - Warning: FDA label warnings from NLP (amber)
  - Signal: FAERS consensus signals (red intensity = signal strength)
  - Related: Other opioids in same category (gray)
- **Edges:** Weighted by strength of association (thicker = stronger signal/higher affinity)
- **Physics:** Force-directed layout, nodes pull together on load, draggable
- **Integration points:**
  - Drug Explorer: Show knowledge graph below drug identity card
  - Signal Detection: Graph view as alternative to heatmap

**Files to create:**
- `opioid_track/dashboard/components/network_graph.py`

**Files to modify:**
- `opioid_track/dashboard/pages/drug_explorer.py` — add knowledge graph section
- `opioid_track/dashboard/pages/signals.py` — add graph view toggle

---

## Phase 4: Intelligence Features (User-Facing Value)

### 4.1 Three-Tier View System
**What:** Replace binary layman's toggle with Executive / Clinical / Research view modes.

**Implementation:**
- **File:** `opioid_track/dashboard/components/view_mode.py`
- **Sidebar control:** Radio button group at top of sidebar (above navigation)
- **Tier definitions:**

| Aspect | Executive | Clinical | Research |
|--------|-----------|----------|----------|
| Terminology | Plain English (e.g., "Safety Signal Strength" not "PRR") | Standard clinical (current) | Full technical (expose raw values) |
| Data depth | KPI cards + narrative summaries | Charts + filterable tables (current) | Raw data tables + API responses + contingency tables |
| Panels shown | Summary metrics, top-level charts, risk tiers | All current panels | All panels + method breakdowns, confidence intervals, p-values |
| Watchdog responses | Simplified explanations | Current behavior | Include citations, raw data references, methodology notes |
| Charts | Simple bar/donut charts | Current Plotly charts | Add statistical annotations, error bars, distribution plots |

- **Mechanism:** Each page checks `st.session_state.view_mode` and conditionally renders content
- **Persistence:** View mode saved in session state, persists across page navigation

**Files to create:**
- `opioid_track/dashboard/components/view_mode.py`

**Files to modify:**
- `opioid_track/dashboard/opioid_app.py` — add view mode selector to sidebar
- All 6 page files — add conditional rendering based on view mode
- `opioid_track/agents/opioid_watchdog.py` — adjust response verbosity per mode

---

### 4.2 Premium Calls to Action

#### 4.2.1 Safer Alternative Suggestions
- **File:** `opioid_track/core/alternative_finder.py`
- Given a drug + dose, find lower-risk alternatives:
  - Same therapeutic category but lower MME factor
  - Lower danger classification
  - Better therapeutic index
  - Consider non-opioid alternatives (flag for clinician review)
- Output: Ranked list with risk score comparison, MME reduction %, and switching considerations
- **Integration:** Button in Drug Explorer + Watchdog Dose Calculator

#### 4.2.2 FHIR RiskAssessment Resource Generation
- **File:** `opioid_track/core/fhir_generator.py`
- Generate valid FHIR R4 `RiskAssessment` resource containing:
  - Subject reference, encounter context
  - Risk prediction (Clinical Risk Index score + tier)
  - Basis references (FAERS signals, pharmacology data)
  - Mitigation suggestions (safer alternatives)
- Also generate `DetectedIssue` resource for safety signals
- Output as JSON (viewable + downloadable)
- **Integration:** "Generate EMR Alert" button in Drug Explorer

#### 4.2.3 PDF Risk Report Export
- **File:** `opioid_track/core/report_generator.py`
- **Library:** `reportlab` or `fpdf2`
- Generate branded PDF containing:
  - Drug profile summary
  - Risk score with factor breakdown
  - Active FAERS signals
  - Geographic context (if state selected)
  - Safer alternatives
  - Methodology notes
- TruPharma header/footer branding
- **Integration:** "Export Report" button on Drug Explorer + Watchdog pages

**Files to create:**
- `opioid_track/core/alternative_finder.py`
- `opioid_track/core/fhir_generator.py`
- `opioid_track/core/report_generator.py`
- `opioid_track/tests/test_fhir_generator.py`

**Files to modify:**
- `opioid_track/dashboard/pages/drug_explorer.py` — add CTA buttons
- `opioid_track/dashboard/pages/watchdog.py` — add CTA buttons

---

### 4.3 Real-Time Alert System
**Implementation:**
- **File:** `opioid_track/core/alert_engine.py`
- **Alert types:**
  1. **New FAERS Signal:** When a new consensus signal is detected for a tracked drug
  2. **FDA Recall:** When FDA Enforcement API returns a new recall for an opioid
  3. **Mortality Spike:** When forecast model detects actual > predicted mortality by >2σ
  4. **Drug Shortage:** When a tracked opioid enters shortage status
- **Delivery (for demo):**
  - In-app notification bell (sidebar badge with count)
  - Alert history page with timestamp, type, severity, details
  - Webhook endpoint in API (for future Slack/email integration)
- **Background check:** Periodic polling (configurable interval) via background thread or scheduled task

**Files to create:**
- `opioid_track/core/alert_engine.py`
- `opioid_track/dashboard/components/alert_bell.py`

**Files to modify:**
- `opioid_track/dashboard/opioid_app.py` — add alert bell to sidebar
- `opioid_track/api/routes/alerts.py` — webhook subscription endpoint

---

## Phase 5: Platform Overview Page (Reframed Business Pitch)

### 5.1 Platform Overview Tab
**Framing:** "Here's what this platform can do" — not "buy our product."

**Implementation:**
- **File:** `opioid_track/dashboard/pages/platform_overview.py`
- **Sections:**

1. **Platform Capabilities Grid**
   - Visual cards showing each module (Registry, Signals, Geographic, ML, NLP, API)
   - Each card shows: icon, name, data source count, key metric
   - Live numbers pulled from actual data (e.g., "85+ drugs tracked", "18 safety terms monitored", "3,148 counties profiled")

2. **Architecture Diagram**
   - Interactive visualization of the data pipeline (ingestion → processing → analytics → dashboard)
   - Clickable nodes that expand to show detail

3. **Market Context** (subtle, data-driven)
   - TAM/SAM/SOM visualization using Plotly (concentric donuts or funnel)
   - Key market stats (opioid crisis costs, pharmacovigilance market size)
   - Position as "Clinical Intelligence" not just "dashboard"

4. **Customer Personas** (who benefits)
   - Clean cards: Hospital Systems, Health Plans, PBMs, Public Health Agencies, Pharma Safety Teams
   - Each with: use case, key features used, value delivered

5. **Integration Readiness**
   - API documentation preview (link to Swagger UI)
   - FHIR compatibility badge
   - Data source logos grid

6. **Request Demo / Contact**
   - Simple form (name, org, email, use case)
   - Stores submissions locally (or sends webhook)

**Files to create:**
- `opioid_track/dashboard/pages/platform_overview.py`

**Files to modify:**
- `opioid_track/dashboard/opioid_app.py` — add "Platform Overview" to navigation

---

## Phase 6: Testing & Polish

### 6.1 Test Coverage
- Unit tests for all new modules (forecaster, risk scorer, supply chain, FHIR, alternatives)
- Integration tests for API endpoints
- Validation tests for ML models (MAPE thresholds, prediction interval coverage)
- Dashboard smoke tests (each page loads without error)

### 6.2 Dependencies
Add to `requirements.txt`:
```
# Phase 1
fastapi>=0.104.0
uvicorn>=0.24.0

# Phase 2
prophet>=1.1.5
scikit-learn>=1.3.0

# Phase 3
pydeck>=0.8.0
streamlit-agraph>=0.0.45

# Phase 4
fpdf2>=2.7.0
fhir.resources>=7.0.0

# Existing (verify versions)
streamlit
plotly
pandas
numpy
requests
```

### 6.3 Final Polish
- Consistent color palette across all new components (teal/amber/red from existing design tokens)
- Loading spinners for all API-backed components
- Error states with graceful fallbacks (if API is down, show cached data with "last updated" timestamp)
- Mobile-responsive adjustments for key pages

---

## Implementation Order (Recommended)

| Order | Component | Est. Complexity | Depends On |
|-------|-----------|----------------|------------|
| 1 | Performance Caching (1.1) | Medium | Nothing |
| 2 | Risk Scorer (2.2) | Medium | Caching |
| 3 | Geographic Forecaster (2.1) | High | Caching |
| 4 | Supply Chain Dashboard (2.3) | Medium | Caching |
| 5 | DeckGL 3D Globe (3.1) | Medium | Nothing |
| 6 | Knowledge Graph (3.2) | Medium | Nothing |
| 7 | Three-Tier View System (4.1) | High | All pages exist |
| 8 | Safer Alternatives (4.2.1) | Medium | Risk Scorer |
| 9 | FHIR Generator (4.2.2) | Medium | Risk Scorer |
| 10 | PDF Reports (4.2.3) | Low | Risk Scorer |
| 11 | FastAPI Layer (1.2) | High | All core modules |
| 12 | Alert Engine (4.3) | Medium | Supply Chain, Signals |
| 13 | Platform Overview (5.1) | Medium | All features done |
| 14 | Testing & Polish (6) | Medium | Everything |

---

## Key Design Decisions

1. **SQLite over Redis** for caching — zero infrastructure overhead, ships as single file
2. **Prophet over ARIMA/scikit-learn** for forecasting — interpretable, handles irregular data, built-in uncertainty
3. **Transparent composite score over black-box ML** for risk scoring — explainability is critical for clinical credibility
4. **Real-time supply monitoring over ARIMA recall forecasting** — sparse event data makes time-series unreliable
5. **FastAPI after core features** — build the intelligence first, then expose it via API (avoids premature abstraction)
6. **3-tier views over binary toggle** — maximizes demo versatility (switch modes live during investor pitch)
7. **Platform Overview over Business Pitch** — product-led framing builds more credibility than a sales deck embedded in a tool
