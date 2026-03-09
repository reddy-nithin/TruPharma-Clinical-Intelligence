# Sub-Plan 13: Testing & Final Polish

## Priority: LAST (everything else must be done)
## Depends on: All Sub-Plans 01-12

---

## Goal
Comprehensive test coverage, visual consistency audit, dependency management, and final polish. Ensure the entire upgraded app works end-to-end in both themes, all view modes, with no regressions.

## Pre-Requisites
- ALL Sub-Plans 01-12 should be COMPLETED
- Read `00_STATUS.md` first — verify all previous sub-plans show COMPLETED

## Context
This sub-plan has no new features. It's purely about quality assurance.

---

## Agent Assignment

### Agent A — Run All Existing Tests + Fix Regressions

**Task:** Run the full test suite and fix any failures.

```bash
# Step 1: Run all tests
pytest opioid_track/tests/ -v --tb=short

# Step 2: If any tests fail, read the failing test and the module it tests
# Step 3: Fix the root cause (NOT the test, unless the test itself is wrong)
# Step 4: Re-run until all green
```

**Tests to verify exist and pass:**
- `test_cache.py` — caching layer
- `test_registry.py` — drug registry (pre-existing)
- `test_signal_detector.py` — FAERS signals (pre-existing)
- `test_risk_scorer.py` — clinical risk index
- `test_forecaster.py` — geographic forecasting
- `test_supply_chain.py` — supply chain monitor
- `test_premium_ctas.py` — alternatives, FHIR, PDF
- `test_api.py` — FastAPI endpoints

**Done criteria:** `pytest opioid_track/tests/ -v` — ALL GREEN.

---

### Agent B (Parallel with A) — Visual Audit

**Task:** Check every page renders correctly in both themes and all view modes.

**Checklist (manual/visual):**

**Dark Theme:**
- [ ] Drug Explorer loads, all sections render
- [ ] Opioid Landscape loads, all 5 charts render
- [ ] Geographic Intelligence loads, choropleth + 3D toggle works
- [ ] Demographics loads, all charts render
- [ ] Signal Detection loads, heatmap + graph toggle works
- [ ] Watchdog Tools loads, all 3 tabs work
- [ ] Supply Chain loads, recalls + vulnerability heatmap render
- [ ] Platform Overview loads, all 7 sections render

**Light Theme:**
- [ ] Same checklist as dark theme — toggle and verify every page
- [ ] No dark colors leaking through (text should be dark on light backgrounds)
- [ ] Charts have appropriate light backgrounds
- [ ] Borders and shadows are subtle but visible

**Executive Mode:**
- [ ] Each page shows simplified content — no technical jargon
- [ ] Tables and detail panels are hidden
- [ ] Narrative summaries appear

**Research Mode:**
- [ ] Each page shows extra detail — raw data, CIs, methodology
- [ ] No panels are missing from Clinical mode

**If issues found:** Fix them. Common issues:
- Hardcoded hex colors that weren't caught in Sub-Plan 02
- Plotly charts not using `get_plotly_theme()`
- Missing conditional rendering in view mode branches
- CSS variables not defined in light theme

**Done criteria:** All pages render correctly in all 6 combinations (2 themes × 3 view modes).

---

### Agent C (Parallel with A, B) — Dependency Management

**Task:** Ensure all dependencies are properly declared.

**Update: `requirements.txt`** (or `pyproject.toml` if that's what the project uses)

Check which dependency file exists and update it:

```bash
ls requirements*.txt pyproject.toml setup.py setup.cfg 2>/dev/null
```

**New dependencies to add (verify versions):**
```
# Performance
# (sqlite3 is stdlib — no dependency needed)

# ML / Forecasting
prophet>=1.1.5
scikit-learn>=1.3.0

# Visualization
pydeck>=0.8.0
streamlit-agraph>=0.0.45

# API
fastapi>=0.104.0
uvicorn>=0.24.0

# Document Generation
fpdf2>=2.7.0

# Existing (verify present)
streamlit>=1.28.0
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
```

**Verify installations:**
```bash
pip install -r requirements.txt
# Verify no conflicts
pip check
```

**Done criteria:** All dependencies installable without conflicts.

---

### Agent D (Sequential after A, B, C) — Loading States & Error Handling

**Task:** Add loading spinners and graceful error handling to all API-backed components.

**Pattern to apply across all pages:**

```python
# Loading spinner pattern
with st.spinner("Loading drug data..."):
    data = load_data()

# Error fallback pattern
try:
    data = fetch_from_api()
except Exception as e:
    st.warning(f"Using cached data (last updated: {cache_timestamp})")
    data = load_from_cache()

# Empty state pattern
if data is None or len(data) == 0:
    st.info("No data available. Run the ingestion pipeline to populate data.")
    return
```

**Apply to:**
- Drug Explorer: spinner when loading drug profile, signals, NLP insights
- Geographic Intelligence: spinner when loading forecasts, 3D map
- Signal Detection: spinner when running signal detection
- Supply Chain: spinner when fetching recalls from FDA API
- Watchdog: spinner when computing dose risk, comparing drugs
- Knowledge Graph: spinner when building graph
- Alert Bell: silent background check (no spinner)

**Done criteria:** No raw Python tracebacks visible to user. All slow operations show spinners. All API failures show fallback messages.

---

### Agent E (Sequential, final) — Final Commit and STATUS Update

**Task:**

1. Run final test suite:
   ```bash
   pytest opioid_track/tests/ -v
   ```

2. Update `00_STATUS.md`:
   - Mark ALL sub-plans as COMPLETED
   - Add final notes

3. Create final commit:
   ```bash
   git add opioid_track/
   git commit -m "feat(opioid): complete platform upgrade — testing, polish, and dependency management"
   ```

4. Verify app starts:
   ```bash
   streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
   ```

5. Verify API starts:
   ```bash
   uvicorn opioid_track.api.app:app --port 8000
   ```

**Done criteria:** All tests pass. App and API both start without errors. STATUS.md shows all COMPLETED.

---

## Execution Order
1. **Agent A** (tests) + **Agent B** (visual audit) + **Agent C** (dependencies) — all in parallel
2. **Agent D** (loading states) — after A/B/C
3. **Agent E** (final commit) — last

## Checkpoint Protocol
- This is the final sub-plan — no further checkpoints needed
- If issues are found, create specific fix tasks and track them in STATUS.md

## Summary Verification Checklist
```
[ ] All pytest tests pass
[ ] App loads in dark mode — all pages work
[ ] App loads in light mode — all pages work
[ ] Executive view mode — simplified on all pages
[ ] Research view mode — extra detail on all pages
[ ] 3D globe renders with correct data
[ ] Knowledge graph renders and stabilizes
[ ] Risk badges show on Drug Explorer
[ ] Forecast chart shows in Geography
[ ] Supply Chain page shows recalls
[ ] Alert bell shows in sidebar
[ ] Platform Overview shows live metrics
[ ] PDF report downloads correctly
[ ] FHIR JSON validates
[ ] API Swagger UI accessible at /docs
[ ] All CTAs work (alternatives, FHIR, PDF)
[ ] No hardcoded dark colors in light mode
[ ] All dependencies install cleanly
[ ] No Python tracebacks visible to user
```
