# Opioid Track — Technical Architecture (Tier 3)

**Version:** 3.0.0
**Last Updated:** 2026-03-07
**Prerequisite:** Tier 1 (v1.0.0) + Tier 1.5 (v1.5.0) + Tier 2 (v2.0.0) must be complete

---

## 1. Overview

Tier 3 adds molecular-level pharmacology intelligence, NLP-mined drug label analysis, a standalone Streamlit dashboard, an OpioidWatchdog agent, and RAG-ready knowledge chunks. All code lives under `opioid_track/` and does not modify existing files.

**Design principles (carried from Tiers 1–2):**
- Complete isolation from the parent TruPharma project
- Reproducibility-first: uses three pinned GitHub repositories
- Warn-and-continue error handling (never crash)
- All data files committed to git for offline reproducibility

**New in Tier 3:**
- Receptor-level pharmacology via ChEMBL, GtoPdb, PubChem
- Toxicology with interspecies LD50 scaling
- NLP label mining with CDC NegEx negation detection
- 4-page Streamlit dashboard (Drug Explorer, Landscape, Geography, Signals)
- OpioidWatchdog agent class for structured intelligence queries
- 55 RAG-ready knowledge text chunks

---

## 2. Directory Structure (Tier 3 Additions)

```
opioid_track/
├── ... (all Tier 1 + 1.5 + 2 files, untouched)
├── config.py                              ← APPENDED with Tier 3 entries
├── vendor/
│   ├── ... (Tier 2 vendor repos)
│   ├── Opioid_Involvement_NLP/            ← cloned from CDCgov
│   ├── dash-opioid-epidemic-demo/         ← cloned from plotly
│   └── overdosedata/                      ← cloned from opioiddatalab
├── ingestion/
│   ├── ... (Tier 1 + 2 fetchers, untouched)
│   ├── pharmacology_fetcher.py            ← NEW
│   └── toxicology_fetcher.py              ← NEW
├── core/
│   ├── ... (Tier 1 + 2 core, untouched)
│   ├── nlp_miner.py                       ← NEW (adapts CDCgov/Opioid_Involvement_NLP)
│   └── knowledge_indexer.py               ← NEW
├── agents/
│   └── opioid_watchdog.py                 ← NEW
├── dashboard/
│   ├── opioid_app.py                      ← NEW (standalone Streamlit app)
│   ├── components/charts.py               ← NEW (ported from dash-opioid-epidemic-demo)
│   └── pages/
│       ├── drug_explorer.py               ← NEW
│       ├── landscape.py                   ← NEW
│       ├── geography.py                   ← NEW (adapts dash-opioid-epidemic-demo)
│       └── signals.py                     ← NEW
├── data/
│   ├── ... (Tier 1 + 2 data, untouched)
│   ├── opioid_pharmacology.json           ← NEW (pharmacology + toxicology output)
│   ├── opioid_nlp_insights.json           ← NEW (NLP label mining output)
│   └── knowledge_chunks/                  ← NEW
│       ├── manifest.json
│       └── *.txt (55 chunks)
└── tests/
    ├── ... (Tier 1 + 2 tests, untouched)
    └── test_pharmacology.py               ← NEW (8 tests)
```

---

## 3. External Repositories

### 3.1 CDCgov/Opioid_Involvement_NLP

**Purpose:** NLP detection of opioid involvement in clinical text.
**How adapted:** The full CDC pipeline targets death certificate text. We extracted:
- NegEx negation rules from `negex_triggers.txt`
- Opioid term mappings from the classification files
- The negation detection algorithm (NegEx-based)

These components are applied to DailyMed SPL label text sections parsed by LOINC code. The NegEx engine disambiguates affirmed vs. negated mentions (e.g., "no respiratory depression" vs. "respiratory depression may occur").

### 3.2 plotly/dash-opioid-epidemic-demo

**Purpose:** County-level opioid choropleth map and chart design patterns.
**How adapted:** Ported the Plotly figure-building logic from the Dash `app.py` into Streamlit-compatible functions in `charts.py`. The county FIPS-based choropleth, color scale patterns, and hover templates are adapted from this repo. Only the Plotly `graph_objects` calls were kept; the Dash callback/layout system was replaced with Streamlit widgets.

### 3.3 opioiddatalab/overdosedata

**Purpose:** Reference implementation for Streamlit opioid dashboard patterns.
**How used:** Read-only. Studied its data loading, sidebar navigation, and page structure patterns to inform the dashboard design. No code was directly ported.

---

## 4. Data Pipeline Architecture

### 4.1 Pharmacology Fetcher (`ingestion/pharmacology_fetcher.py`)

**Input:** Opioid ingredients from Tier 1 registry (17 ingredients)
**APIs:** ChEMBL (bioactivity + mechanisms), GtoPdb (curated interactions), PubChem (properties + pharmacokinetics)
**Output:** `opioid_pharmacology.json`

Data flow:
1. Extract unique opioid ingredients from registry where `is_opioid_component=true`
2. For each ingredient:
   - Find ChEMBL compound ID by name lookup
   - Fetch bioactivity data (Ki, IC50, EC50) at mu/kappa/delta/NOP targets
   - Fetch GtoPdb curated ligand-receptor interactions
   - Fetch PubChem chemical properties and pharmacokinetics
   - Resolve best receptor affinity values across sources
   - Generate `why_its_an_opioid` explanation
   - Compute potency relative to morphine (morphine Ki / drug Ki at mu)

**Rate limiting:** 0.1s delay between ChEMBL requests; 0.5s for PubChem/GtoPdb.

### 4.2 Toxicology Fetcher (`ingestion/toxicology_fetcher.py`)

**Input:** `opioid_pharmacology.json` from Step 4
**APIs:** PubChem PUG View (Toxicity heading)
**Output:** Updates `opioid_pharmacology.json` in-place

Data flow:
1. For each ingredient with a PubChem CID, fetch acute toxicity data
2. Parse LD50 values from PubChem's text-based toxicity entries
3. Apply interspecies BSA scaling: `HED = animal_LD50 × (animal_Km / human_Km)`
4. Compute therapeutic index: `TI = LD50 / ED50` (using mu EC50 as ED50 proxy)
5. Classify danger level by estimated human lethal dose thresholds
6. Build ingredient→product cross-reference from registry

### 4.3 NLP Miner (`core/nlp_miner.py`)

**Input:** Tier 1 registry (drugs with SPL set IDs), DailyMed SPL XML, CDCgov NegEx rules
**Output:** `opioid_nlp_insights.json`

Data flow:
1. For each opioid drug in registry, fetch SPL XML from DailyMed
2. Parse XML by LOINC section codes (9 sections: boxed warning through clinical pharmacology)
3. Run CDC NegEx-based annotation on each section's text
4. Extract structured data:
   - Boxed warning: paragraph count, key warnings, full text
   - Dosage: starting dose, max daily dose, dose values found
   - Adverse reactions: respiratory depression flag, safety terms
   - Drug interactions: benzodiazepine warning, CYP enzyme interactions
   - Abuse/dependence: DEA schedule, abuse potential
   - Overdosage: symptoms, naloxone rescue dose
   - REMS: required flag, type
5. Build comparison matrix across all mined labels

---

## 5. Dashboard Architecture

### 5.1 Main Entry (`dashboard/opioid_app.py`)

- Standalone Streamlit app on port 8502
- Dark navy theme with teal/cyan accents, red/amber for danger
- `@st.cache_data` for all JSON loading
- Sidebar navigation: Drug Explorer, Opioid Landscape, Geographic Intelligence, Signal Detection
- Graceful handling of missing data files

### 5.2 Chart Components (`dashboard/components/charts.py`)

8 reusable Plotly figure builders:
1. `create_choropleth()` — county/state choropleth (adapted from dash-opioid-epidemic-demo)
2. `create_potency_chart()` — horizontal bar chart of ingredients by mu Ki
3. `create_danger_scatter()` — scatter: potency vs FAERS reports, sized by danger
4. `create_signal_heatmap()` — drugs × reactions matrix with methods-flagging color
5. `create_timeline_chart()` — CDC mortality timeline with three-waves annotations
6. `create_receptor_bar()` — receptor binding bar chart for single ingredient
7. `create_schedule_donut()` — DEA schedule distribution
8. `create_state_choropleth()` — state-level metric choropleth

### 5.3 Pages

| Page | Key Visualizations |
|------|--------------------|
| Drug Explorer | Search, identity card, receptor binding chart, safety profile, FAERS signals, NLP label highlights, related products |
| Opioid Landscape | Classification treemap, potency comparison, danger matrix, three-waves timeline, schedule donut |
| Geographic Intelligence | State choropleth with metric selector, state comparison bars, mortality timeline, county detail |
| Signal Detection | Signal heatmap, signal detail (PRR/ROR/EBGM metrics), top signals table |

---

## 6. OpioidWatchdog Agent

**Module:** `agents/opioid_watchdog.py`
**Class:** `OpioidWatchdog`

Designed for import into the main TruPharma app or standalone use:

```python
from opioid_track.agents.opioid_watchdog import OpioidWatchdog
watchdog = OpioidWatchdog()  # auto-loads all data files
```

### Public Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `is_opioid_query(name_or_rxcui)` | `bool` | Check if a drug is a known opioid |
| `get_full_opioid_brief(rxcui)` | `dict` | Comprehensive brief: identity, pharmacology, safety, signals, label highlights, prescribing context |
| `answer_why_opioid(drug_name)` | `str` | Receptor-level explanation of opioid classification |
| `compare_danger(drug1, drug2)` | `str` | Side-by-side danger comparison with specific numbers |
| `get_signals_summary(rxcui)` | `str` | FAERS pharmacovigilance signal summary |
| `get_label_warnings(rxcui)` | `str` | NLP-mined label warning summary |
| `find_drugs_with_ingredient(ingredient)` | `list[dict]` | All products containing an ingredient |
| `assess_dose_risk(drug_name, daily_dose_mg)` | `dict` | MME assessment, lethal dose proximity, risk factors, recommendation |
| `format_brief_text(rxcui)` | `str` | Plain-text brief for chat/LLM context |

All text-returning methods cite specific numbers (Ki values, LD50, FAERS counts). Missing data is reported explicitly rather than silently omitted.

---

## 7. Knowledge Indexer

**Module:** `core/knowledge_indexer.py`
**Output:** `data/knowledge_chunks/` (55 `.txt` files + `manifest.json`)

### Chunk Categories

| Category | Count | Content |
|----------|-------|---------|
| Classification | 4 | Categories, receptor system, DEA scheduling, full ingredient list |
| Pharmacology | 17 | One per ingredient: receptor affinities, potency, LD50, metabolism |
| Safety | 18 | One per NLP-mined drug: boxed warnings, REMS, interactions, overdosage |
| Epidemiology | 3 | Three waves timeline, top prescribing states, top death-rate states |
| FAERS Signals | 13 | One per drug with consensus signals: reaction list, PRR/ROR/EBGM |

**Token budget:** ~500–600 tokens per pharmacology/safety chunk; ~16,500 total.

**Manifest format:**
```json
{
  "generated_at": "ISO-8601",
  "total_chunks": 55,
  "chunks": [
    {
      "filename": "ingredient_morphine.txt",
      "type": "pharmacology",
      "drug_name": "morphine",
      "rxcui": "7052",
      "token_estimate": 550
    }
  ]
}
```

---

## 8. Test Coverage

### Tier 3 Tests (`tests/test_pharmacology.py`)

| # | Test | Validates |
|---|------|-----------|
| 1 | `test_pharmacology_loads` | opioid_pharmacology.json exists and parses |
| 2 | `test_morphine_mu_receptor` | Morphine has mu receptor Ki value |
| 3 | `test_morphine_potency_baseline` | Morphine potency = 1.0 (reference) |
| 4 | `test_receptor_data_coverage` | ≥10 ingredients with receptor data |
| 5 | `test_why_opioid_populated` | ≥10 ingredients with explanation text |
| 6 | `test_ld50_coverage` | ≥5 ingredients with LD50 data |
| 7 | `test_nlp_source_attribution` | NLP metadata has CDCgov attribution |
| 8 | `test_vendor_repos_present` | Both vendor repos exist on disk |

**Full test suite:** 38 tests (23 Tier 1 + 7 Tier 2 + 8 Tier 3) — all passing.

---

## 9. Data Schema Summary

### opioid_pharmacology.json

```
metadata: { sources, generated_at, total_ingredients, ingredients_with_receptor_data }
receptor_targets: { mu/kappa/delta/nop: { chembl_id, gene, uniprot, gtopdb_interactions } }
ingredient_pharmacology: {
  "<name>": {
    rxcui_ingredient, pubchem_cid, chembl_id, smiles,
    molecular_formula, molecular_weight, xlogp,
    receptor_affinities: { mu/kappa/delta: { ki_nM, source } },
    mu_ec50_nM, mechanisms_of_action,
    why_its_an_opioid, potency_vs_morphine,
    ld50_data: [{ species, route, ld50_mg_kg, raw_text, source }],
    therapeutic_index, estimated_human_lethal_dose_mg,
    danger_level, danger_rank,
    half_life_hours, onset_minutes, duration_hours,
    metabolism, active_metabolites,
    products_containing: [{ rxcui, drug_name, schedule, tty }]
  }
}
```

### opioid_nlp_insights.json

```
metadata: { nlp_source: "CDCgov/Opioid_Involvement_NLP", total_drugs_processed }
drug_label_insights: [{
  drug_name, rxcui, spl_set_id, opioid_ingredients, opioid_category, schedule,
  sections_parsed, section_annotations: { <section>: { opioid_mentions, negated_mentions, safety_flags } },
  boxed_warning: { present, paragraph_count, key_warnings, full_text },
  dosage: { starting_dose, max_daily_dose_mg, doses_found },
  adverse_reactions: { resp_depression_mentioned, reaction_frequencies, safety_terms_detected },
  drug_interactions: { benzo_warning, cyp_interactions, contraindicated_classes },
  abuse_dependence: { schedule, abuse_potential },
  overdosage: { naloxone_rescue_dose, symptoms },
  rems: { rems_required, rems_type }
}]
comparison_matrix: [{ drug_name, rxcui, max_daily_dose_mg, resp_depression_in_label, ... }]
```

---

## 10. Configuration Entries (Tier 3)

All appended to `opioid_track/config.py` under `# === TIER 3 ADDITIONS ===`:

| Config Key | Value | Purpose |
|------------|-------|---------|
| `PHARMACOLOGY_OUTPUT` | `data/opioid_pharmacology.json` | Combined pharmacology + toxicology output |
| `CHEMBL_DELAY_SECONDS` | 0.1 | Rate limit for ChEMBL API |
| `CHEMBL_OPIOID_TARGETS` | mu/kappa/delta/NOP | Receptor target ChEMBL/GtoPdb IDs |
| `GTOPDB_API_BASE` | `guidetopharmacology.org` | GtoPdb REST API |
| `PUBCHEM_API_BASE` | `pubchem.ncbi.nlm.nih.gov` | PubChem PUG REST |
| `KM_SCALING` | mouse=3.0 ... human=37.0 | Interspecies BSA scaling constants |
| `NLP_INSIGHTS_OUTPUT` | `data/opioid_nlp_insights.json` | NLP mining output |
| `CDC_NLP_VENDOR_DIR` | `vendor/Opioid_Involvement_NLP` | CDC NLP vendor repo path |
| `SPL_OPIOID_SECTIONS` | 9 LOINC codes | SPL sections to parse |
| `DASHBOARD_PORT` | 8502 | Standalone dashboard port |
| `KNOWLEDGE_CHUNKS_DIR` | `data/knowledge_chunks` | RAG chunk output directory |
| `CHUNK_SIZE_TOKENS` | 600 | Target chunk size |
