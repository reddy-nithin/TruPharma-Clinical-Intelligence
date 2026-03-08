# Opioid Track — Tier 3 Development Log

**Project:** Opioid Track Tier 3 — Deep Pharmacology, NLP, and Dashboards
**Parent Project:** TruPharma Clinical Intelligence
**Branch:** `Week-7-Opioid-track`
**Start Date:** 2026-03-06
**Tier 1 Status:** Complete (1,236 RxCUIs, 198K NDCs, 12K MME mappings)
**Tier 2 Status:** Complete (CMS, CDC, ARCOS data; 204 consensus FAERS signals; 3,148 county profiles)

---

## Tier 3 Goal

Add molecular-level pharmacology (receptor binding, toxicology), NLP-mined drug label intelligence, a standalone Streamlit dashboard, an OpioidWatchdog agent module, and RAG-ready knowledge chunks. Uses three external GitHub repositories:

| Repo | Purpose | How Used |
|---|---|---|
| `CDCgov/Opioid_Involvement_NLP` | NLP opioid mention detection + negation | Adapted NegEx rules for DailyMed SPL labels |
| `plotly/dash-opioid-epidemic-demo` | Choropleth map + chart patterns | Ported Plotly figure logic to Streamlit |
| `opioiddatalab/overdosedata` | Streamlit dashboard design reference | Read-only reference for layout patterns |

---

## Key Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Per-compound ChEMBL queries instead of bulk | Bulk receptor queries timed out (10+ min). Per-compound takes ~2 min total |
| 2 | PubChem LD50 only (no PyTDC) | PyTDC installation not attempted; PubChem PUG View provides sufficient LD50 data for 6 of 17 ingredients |
| 3 | Adapted CDC NegEx rules (not full pipeline) | CDCgov repo's NLP model targets death certificates, not SPL labels. Extracted NegEx rules and term mappings as reusable components |
| 4 | Streamlit (not Dash) for dashboard | Consistent with TruPharma's Streamlit stack. Ported Plotly figure builders from dash-opioid-epidemic-demo |
| 5 | Port 8502 for dashboard | Avoids conflict with main TruPharma app (port 8501) |
| 6 | OpioidWatchdog as standalone importable class | Can be used independently or imported into main TruPharma app when team is ready |
| 7 | Knowledge chunks as individual .txt files | Framework-agnostic; works with any RAG system (LangChain, LlamaIndex, custom) |

---

## Session 1 — Data Pipelines (2026-03-06)

### Phase 0: Environment & Config
- Appended Tier 3 config block to `config.py`: ChEMBL targets, GtoPdb/PubChem APIs, toxicology constants, NLP settings, dashboard config, knowledge chunk settings
- Cloned 3 vendor repos into `opioid_track/vendor/`
- Installed `chembl_webresource_client` and `lxml`

### Phase 1a: pharmacology_fetcher.py
- 17 opioid ingredients extracted from registry
- ChEMBL bioactivity data: Ki, IC50, EC50 at mu/kappa/delta/NOP receptors
- GtoPdb: 256 ligand-receptor interactions across 4 receptor targets
- PubChem: molecular properties, pharmacokinetics, metabolism
- 16 of 17 ingredients have receptor affinity data (meperidine excluded — indexed as "pethidine" in ChEMBL)
- `why_its_an_opioid` explanations generated for all with receptor data

### Phase 1b: toxicology_fetcher.py
- PubChem acute toxicity: 6 ingredients with LD50 data (fentanyl, morphine, methadone, tramadol, naltrexone, hydromorphone)
- 11 ingredients missing from PubChem's Toxicity heading (codeine, oxycodone, buprenorphine, etc.)
- Interspecies BSA scaling applied for human equivalent dose estimation
- Danger rankings computed: fentanyl = "High" danger
- Product cross-reference built for all 17 ingredients

---

## Session 2 — NLP + Dashboard (2026-03-06)

### Phase 2: nlp_miner.py
- Adapted CDCgov/Opioid_Involvement_NLP for DailyMed SPL XML labels
- 18 drugs mined (18/18 success), 12 with boxed warnings
- CDC NegEx negation detection on each label section (9 LOINC sections)
- Structured extraction: dosage, adverse reactions, drug interactions, abuse/dependence, overdosage, REMS
- Comparison matrix built across all 18 mined labels

### Phase 3a–3f: Dashboard
- **opioid_app.py**: Main Streamlit entry with sidebar nav, dark navy/teal theme, `@st.cache_data` loading
- **charts.py**: 8 reusable Plotly chart builders (choropleth, potency, danger scatter, signal heatmap, timeline, receptor bar, schedule donut, state choropleth)
- **drug_explorer.py**: Full drug deep-dive with search, identity card, receptor binding chart, safety profile, FAERS signals, NLP label highlights, related products
- **landscape.py**: Classification treemap, potency comparison, danger matrix with FAERS overlay, three-waves timeline, danger rankings table
- **geography.py**: State choropleth adapted from dash-opioid-epidemic-demo, state comparison bars, mortality timeline, county detail panel
- **signals.py**: Signal heatmap, individual signal detail (PRR/ROR/EBGM), top signals table, per-drug summary
- Dashboard verified: launches on port 8502, all 4 pages render

---

## Session 3 — Integration & Finalization (2026-03-07)

### Phase 4a: opioid_watchdog.py
- `OpioidWatchdog` class with 8 public methods:
  - `is_opioid_query()` — check if a drug is a known opioid
  - `get_full_opioid_brief()` — comprehensive intelligence brief (identity, pharmacology, safety, signals, label highlights)
  - `answer_why_opioid()` — explain receptor-level opioid classification
  - `compare_danger()` — compare two drugs' danger profiles with specific numbers
  - `get_signals_summary()` — FAERS pharmacovigilance signal summary
  - `get_label_warnings()` — NLP-mined label warning summary
  - `find_drugs_with_ingredient()` — find all products containing an ingredient
  - `assess_dose_risk()` — assess risk for a given daily dose (MME, lethal dose proximity, risk factors)
- `format_brief_text()` utility for plain-text output suitable for chat/LLM context
- All methods handle missing data gracefully with explicit messages

### Phase 4b: knowledge_indexer.py
- 55 knowledge chunks generated across 5 categories:
  - Classification: 4 chunks (categories, receptor system, DEA scheduling, ingredient list)
  - Pharmacology: 17 chunks (one per ingredient)
  - Safety: 18 chunks (one per NLP-mined drug label)
  - Epidemiology: 3 chunks (three waves, top prescribing states, top death rate states)
  - FAERS signals: 13 chunks (one per drug with consensus signals)
- Total estimated tokens: ~16,500
- Manifest saved to `knowledge_chunks/manifest.json`

### Phase 4c: test_pharmacology.py
- 8 test cases covering Tier 3 outputs:
  1. Pharmacology JSON loads successfully
  2. Morphine has mu receptor Ki value
  3. Morphine potency_vs_morphine = 1.0
  4. ≥10 ingredients with receptor data
  5. ≥10 ingredients with why_its_an_opioid explanation
  6. ≥5 ingredients with LD50 data
  7. NLP metadata contains CDCgov source attribution
  8. Vendor repos are present on disk
- All 8 tests pass; all 38 tests across Tiers 1–3 pass

### Phase 5a: Documentation
- DEV_LOG_TIER3.md (this file) — session-by-session development diary
- TECHNICAL_TIER3.md — comprehensive technical architecture

### Phase 5b: README.md update
- Appended Tier 3 section covering all new capabilities

### Phase 5c: Validation
- All 38 tests pass (23 Tier 1 + 7 Tier 2 + 8 Tier 3)
- Dashboard launches on port 8502 with all 4 pages rendering
- 55 knowledge chunks generated
- No existing TruPharma files modified
- No Tier 1 or Tier 2 files modified

---

## Blockers & Notes

- **PubChem LD50 gaps**: 11 of 17 ingredients have no LD50 data in PubChem's Toxicity heading. These are well-known drugs (codeine, oxycodone, buprenorphine) where PubChem simply doesn't have the section.
- **Meperidine/pethidine**: No ChEMBL bioactivity hits under "meperidine"; the compound is indexed as "pethidine" in ChEMBL.
- **ChEMBL query strategy**: Original bulk-receptor-query approach timed out. Rewrote to per-compound queries (2 min total vs 10+ min hanging).
- **CDC NLP adaptation**: The CDCgov repo targets death certificate text, not SPL labels. Extracted the NegEx rules and opioid term mappings as portable components rather than using the full pipeline.
