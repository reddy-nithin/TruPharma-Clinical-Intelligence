# Opioid Track Upgrade — STATUS Tracker

> **Purpose:** This file is the single source of truth for upgrade progress. Every agent session MUST read this file first and update it before finishing.

## How to Use This File

### For Agents Starting a Sub-Plan:
1. Read this file FIRST before doing anything else
2. Check which sub-plan you're working on
3. Look at its status — if "IN_PROGRESS", read the "Last Checkpoint" to know where to resume
4. Update status to "IN_PROGRESS" with your start time

### For Agents Finishing Work:
1. Update the sub-tasks checklist (mark completed items with [x])
2. Set "Last Checkpoint" to describe exactly where you stopped
3. If all sub-tasks are done, set status to "COMPLETED"
4. If hitting context limits, set "Last Checkpoint" with precise resumption instructions
5. Commit this file with your changes

### For Agents Resuming After Limits:
1. Read this file
2. Find the sub-plan marked "IN_PROGRESS"
3. Read "Last Checkpoint" — it tells you EXACTLY what's done and what's next
4. Do NOT re-read files that are already confirmed working
5. Continue from the checkpoint

---

## Sub-Plan Status Table

| # | Sub-Plan | Status | Dependencies | Last Checkpoint |
|---|----------|--------|-------------|-----------------|
| 01 | Performance Caching | NOT_STARTED | None | — |
| 02 | Light/Dark Theme | NOT_STARTED | None | — |
| 03 | Risk Scorer | NOT_STARTED | 01 | — |
| 04 | Geographic Forecaster | NOT_STARTED | 01 | — |
| 05 | Supply Chain Dashboard | NOT_STARTED | 01 | — |
| 06 | DeckGL 3D Globe | NOT_STARTED | None | — |
| 07 | Knowledge Graph | NOT_STARTED | None | — |
| 08 | Three-Tier View System | NOT_STARTED | 02 | — |
| 09 | Premium CTAs | NOT_STARTED | 03 | — |
| 10 | FastAPI Layer | NOT_STARTED | 01,03,04,05 | — |
| 11 | Alert Engine | NOT_STARTED | 01,05 | — |
| 12 | Platform Overview | NOT_STARTED | All 01-11 | — |
| 13 | Testing & Polish | NOT_STARTED | All 01-12 | — |

---

## Detailed Sub-Task Tracking

### Sub-Plan 01: Performance Caching
- [ ] Created `opioid_track/core/cache.py`
- [ ] Modified `opioid_track/core/registry.py` for SQLite loading
- [ ] Modified `opioid_track/core/signal_detector.py` with @cached
- [ ] Modified `opioid_track/config.py` with cache config
- [ ] Created `opioid_track/tests/test_cache.py`
- [ ] Tests pass
- [ ] Committed with descriptive message

### Sub-Plan 02: Light/Dark Theme
- [ ] Created `opioid_track/dashboard/components/theme.py`
- [ ] Refactored `opioid_app.py` CSS to use CSS variables
- [ ] Audited/fixed `drug_explorer.py` hardcoded colors
- [ ] Audited/fixed `landscape.py` hardcoded colors
- [ ] Audited/fixed `geography.py` hardcoded colors
- [ ] Audited/fixed `demographics.py` hardcoded colors
- [ ] Audited/fixed `signals.py` hardcoded colors
- [ ] Audited/fixed `watchdog.py` hardcoded colors
- [ ] Both themes render correctly
- [ ] Committed

### Sub-Plan 03: Risk Scorer
- [ ] Created `opioid_track/ml/risk_scorer.py`
- [ ] Created `opioid_track/tests/test_risk_scorer.py`
- [ ] Modified `drug_explorer.py` with risk badge + waterfall
- [ ] Modified `watchdog.py` with risk scores
- [ ] Modified `opioid_watchdog.py` agent
- [ ] Risk ordering makes clinical sense
- [ ] Tests pass
- [ ] Committed

### Sub-Plan 04: Geographic Forecaster
- [ ] Created `opioid_track/ml/geographic_forecaster.py`
- [ ] Created `opioid_track/ml/model_validation.py`
- [ ] Created `opioid_track/tests/test_forecaster.py`
- [ ] Modified `geography.py` with Predictive tab
- [ ] Modified `config.py` with ML config
- [ ] Validation MAPE reasonable
- [ ] Tests pass
- [ ] Committed

### Sub-Plan 05: Supply Chain Dashboard
- [ ] Created `opioid_track/core/supply_chain_monitor.py`
- [ ] Created `opioid_track/dashboard/pages/supply_chain.py`
- [ ] Created `opioid_track/tests/test_supply_chain.py`
- [ ] Modified `opioid_app.py` navigation
- [ ] Modified `config.py` with FDA enforcement config
- [ ] Tests pass
- [ ] Committed

### Sub-Plan 06: DeckGL 3D Globe
- [ ] Created `opioid_track/dashboard/components/deckgl_map.py`
- [ ] Modified `geography.py` with 2D/3D toggle
- [ ] Added pydeck to requirements
- [ ] Globe renders correctly
- [ ] Committed

### Sub-Plan 07: Knowledge Graph
- [ ] Created `opioid_track/dashboard/components/network_graph.py`
- [ ] Modified `drug_explorer.py` with graph section
- [ ] Modified `signals.py` with graph toggle
- [ ] Added streamlit-agraph to requirements
- [ ] Graph renders and stabilizes
- [ ] Committed

### Sub-Plan 08: Three-Tier View System
- [ ] Created `opioid_track/dashboard/components/view_mode.py`
- [ ] Modified `opioid_app.py` with view selector
- [ ] Modified all page files with conditional rendering
- [ ] Modified `opioid_watchdog.py` verbosity
- [ ] All 3 modes work correctly
- [ ] Committed

### Sub-Plan 09: Premium CTAs
- [ ] Created `opioid_track/core/alternative_finder.py`
- [ ] Created `opioid_track/core/fhir_generator.py`
- [ ] Created `opioid_track/core/report_generator.py`
- [ ] Modified `drug_explorer.py` with CTA buttons
- [ ] Modified `watchdog.py` with CTA buttons
- [ ] Created tests for FHIR + alternatives
- [ ] FHIR validates, PDF downloads, alternatives ranked
- [ ] Committed

### Sub-Plan 10: FastAPI Layer
- [ ] Created `opioid_track/api/app.py`
- [ ] Created `opioid_track/api/models.py`
- [ ] Created `opioid_track/api/routes/drugs.py`
- [ ] Created `opioid_track/api/routes/analytics.py`
- [ ] Created `opioid_track/api/routes/geographic.py`
- [ ] Created `opioid_track/api/routes/alerts.py`
- [ ] Created `opioid_track/tests/test_api.py`
- [ ] Added fastapi/uvicorn to requirements
- [ ] Swagger UI works at /docs
- [ ] All endpoints return correct responses
- [ ] Committed

### Sub-Plan 11: Alert Engine
- [ ] Created `opioid_track/core/alert_engine.py`
- [ ] Created `opioid_track/dashboard/components/alert_bell.py`
- [ ] Modified `opioid_app.py` with alert bell
- [ ] Modified `api/routes/alerts.py` with webhook
- [ ] Alerts fire correctly
- [ ] Committed

### Sub-Plan 12: Platform Overview
- [ ] Created `opioid_track/dashboard/pages/platform_overview.py`
- [ ] Modified `opioid_app.py` navigation
- [ ] All sections render with live data
- [ ] Contact form works
- [ ] Committed

### Sub-Plan 13: Testing & Polish
- [ ] All existing tests pass
- [ ] All new tests pass
- [ ] Visual audit in light + dark mode
- [ ] All 3 view tiers work
- [ ] Loading spinners added
- [ ] Error fallbacks work
- [ ] requirements.txt updated
- [ ] Final commit
