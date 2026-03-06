# Tier 3 — Deep Pharmacology, NLP, and Dashboards
## Full Implementation Plan

**Source:** Created from TIER3_INSTRUCTIONS_REVISED.md + planning session  
**Last Updated:** 2026-03-06  
**Reference:** opioid_track/docs/TIER3_INSTRUCTIONS_REVISED.md (original instructions)

---

## Current State (Pre-Tier 3)

Tiers 1, 1.5, and 2 are **complete**:
- 1,236 opioid RxCUIs, 198K NDC entries, 9.2K opioid NDCs
- CMS prescribing data (200K geo records), CDC mortality (81K VSRR records), Medicaid supply proxy
- FAERS signal detection (204 consensus signals across 14 drugs, 21 safety terms)
- 3,148 county-level geographic profiles with risk tiers
- 23 passing tests across test_registry.py, test_signal_detector.py, test_geographic_joiner.py

**Environment:** Python 3.11.5. Key packages: streamlit 1.54.0, plotly 6.5.2, pandas 2.2.3, numpy 2.2.5.  
**Missing:** chembl_webresource_client, PyTDC, lxml.

**APIs:** All Tier 3 APIs are public (ChEMBL, PubChem, GtoPdb, DailyMed). No keys required.

---

## Session Boundaries (Chunked Strategy)

| Session | Phases | When to Start New Chat |
|---------|--------|-------------------------|
| **Session 1** | Phase 0 + Phase 1 | After pharmacology_fetcher and toxicology_fetcher complete |
| **Session 2** | Phase 2 + Phase 3 | After nlp_miner and full dashboard (all 4 pages) complete |
| **Session 3** | Phase 4 + Phase 5 | After watchdog, indexer, tests, docs, validation |

**Handoff prompt for new chat:**  
"Continue the Tier 3 Opioid Intelligence build. Read opioid_track/TIER3_BUILD_TRACKER.md for current status and pick up from the next step."

---

## Phase 0: Environment and Setup (Steps 2-3)

### 0a. Virtual Environment
```bash
cd /path/to/TruPharma-Clinical-Intelligence/TruPharma-Clinical-Intelligence
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r opioid_track/requirements.txt
```

### 0b. Install New Dependencies
Add to opioid_track/requirements.txt:
```
requests>=2.28.0
chembl_webresource_client>=0.10.8
lxml>=4.9.0
plotly>=5.18.0
streamlit>=1.30.0
```
Optional: PyTDC (skip on failure)

### 0c. Clone Vendor Repos (Step 3)
```bash
mkdir -p opioid_track/vendor
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git opioid_track/vendor/Opioid_Involvement_NLP
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git opioid_track/vendor/dash-opioid-epidemic-demo
git clone https://github.com/opioiddatalab/overdosedata.git opioid_track/vendor/overdosedata
```

### 0d. Update Config (Step 2)
Append Tier 3 config entries to opioid_track/config.py (see TIER3_INSTRUCTIONS_REVISED.md Step 2 for full block).

### 0e. Read Vendor Repos
Before coding, read key files from each cloned repo to understand their APIs.

---

## Phase 1: Data Pipelines (Steps 4-5) — Workstream A

### 1a. opioid_track/ingestion/pharmacology_fetcher.py (Step 4)
- ChEMBL: bioactivity (Ki, IC50, EC50) for mu/kappa/delta/NOP
- GtoPdb: ligand-receptor interactions
- PubChem: chemical properties, pharmacokinetics
- Output: opioid_track/data/opioid_pharmacology.json

### 1b. opioid_track/ingestion/toxicology_fetcher.py (Step 5)
- PubChem acute toxicity (LD50)
- Optional PyTDC
- Interspecies scaling, therapeutic index, danger ranking
- Updates opioid_pharmacology.json

---

## Phase 2: NLP Mining (Step 6) — Workstream B

### opioid_track/core/nlp_miner.py
- Adapt CDCgov/Opioid_Involvement_NLP for DailyMed SPL labels
- Parse SPL XML by LOINC, run CDC NLP annotator
- Output: opioid_track/data/opioid_nlp_insights.json

---

## Phase 3: Dashboard (Step 7) — Workstream C

### Files to Create
- opioid_track/dashboard/opioid_app.py — main entry, sidebar nav, dark theme
- opioid_track/dashboard/components/charts.py — choropleth, potency, danger scatter, signal heatmap, timeline
- opioid_track/dashboard/pages/drug_explorer.py — search, identity card, receptor chart, safety, FAERS, NLP insights
- opioid_track/dashboard/pages/landscape.py — treemap, potency bar, danger matrix, three waves, schedule donut
- opioid_track/dashboard/pages/geography.py — choropleth with metric selector, state comparison, county detail
- opioid_track/dashboard/pages/signals.py — heatmap, signal detail, top signals table

### Design
- Dark navy base, teal/cyan accents, red/amber for danger
- Brain receptor SVG on Drug Explorer (nice-to-have)
- Highly interactive: expandable panels, cross-referencing

---

## Phase 4: Integration (Steps 8-10)

### 4a. opioid_track/agents/opioid_watchdog.py (Step 8)
OpioidWatchdog class with: is_opioid_query, get_full_opioid_brief, answer_why_opioid, compare_danger, get_signals_summary, get_label_warnings, find_drugs_with_ingredient, assess_dose_risk.

### 4b. opioid_track/core/knowledge_indexer.py (Step 9)
Generate 50+ RAG-ready text chunks + manifest.json.

### 4c. opioid_track/tests/test_pharmacology.py (Step 10)
8 test cases covering Tier 3 outputs.

---

## Phase 5: Documentation and Finalization (Steps 11-12)

### 5a. DEV_LOG_TIER3.md and TECHNICAL_TIER3.md
### 5b. Update README.md with Tier 3 section
### 5c. Full validation, single git commit

---

## Risk Mitigation

- ChEMBL rate limits: 0.1s delay; back off if hit
- CDCgov NLP repo: read first, adapt to actual API
- PyTDC: skip on failure, use PubChem only
- DailyMed XML: try/except per drug
- Blockers: inform user, tackle together
