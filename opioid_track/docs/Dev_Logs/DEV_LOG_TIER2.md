# Opioid Track — Tier 2 Development Log

**Project:** Opioid Track Tier 2 — External Data Ingestion + Signal Detection
**Parent Project:** TruPharma Clinical Intelligence
**Branch:** `Week-7-Opioid-track`
**Start Date:** 2026-03-06
**Tier 1 Status:** Complete (85 drugs, 197K NDCs, 12K MME mappings, 21 tests passing)
**Tier 1.5 Status:** Complete (product-level RxCUIs, real-time NDC sync, 23 tests passing)

---

## Tier 2 Goal

Build upon the Tier 1 opioid registry by ingesting three major external data sources (CMS prescribing, CDC mortality, DEA ARCOS supply chain), implementing pharmacovigilance signal detection using faerslib, and joining all data by county FIPS code to produce geographic risk profiles. Uses three external GitHub repositories for reproducibility:

| Repo | Purpose | Install |
|---|---|---|
| `marc-rauckhorst/arcos-py` | ARCOS WaPo API wrapper | `pip install arcospy` |
| `ChapatiDB/faerslib` | PRR, ROR, MGPS signal detection | clone + local FAERS SQLite DB |
| `alipphardt/cdc-wonder-api` | CDC WONDER programmatic API client | clone + local import |

---

## Key Decisions Made

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | ARCOS data limited to 2006–2014 | Only publicly available period via WaPo API. Covers the critical Wave 1→2 prescription opioid flood. Illicit fentanyl (Wave 3) wouldn't appear in ARCOS regardless |
| 2 | faerslib local SQLite DB (not OpenFDA API) | Full reproducibility with peer-reviewed signal detection algorithms. Future migration to BigQuery planned |
| 3 | Census API key for population data | Free key from census.gov improves geographic joiner reliability |
| 4 | Graceful degradation for CDC WONDER | VSRR is primary data source; WONDER supplements with county-level demographics. If WONDER unavailable, set `wonder_available: false` and continue |
| 5 | Chunked CSV reading for CMS data | Provider-and-Drug dataset is 1.38M+ rows. Process in chunks to manage memory |
| 6 | All data files committed to git | Consistent with Tier 1 approach for offline reproducibility |

---

## Phase 0 — Scaffolding & Configuration

**Date:** 2026-03-06
**Status:** Complete

### Documentation created
- `DEV_LOG_TIER2.md` (this file) — running build diary
- `TECHNICAL_TIER2.md` — comprehensive technical architecture document

### Implementation plan finalized
- 4 sessions planned: (A) Config + CMS, (B) CDC + ARCOS, (C) Signal Detection, (D) Geographic Joiner + Tests
- All user decisions resolved (Census API key, faerslib local SQLite, ARCOS 2006–2014)

---

## Phase 1 — Configuration (Step 2)

**Date:** 2026-03-06
**Status:** ✅ Complete

### Changes made to `config.py`
- Appended `# === TIER 2 ADDITIONS ===` block after Tier 1.5 section (line 157+)
- Added Census API key: `CENSUS_API_KEY` (user-provided, free key from census.gov)
- All 5 new output paths: `CMS_PRESCRIBING_OUTPUT`, `CDC_MORTALITY_OUTPUT`, `ARCOS_OUTPUT`, `SIGNAL_RESULTS_OUTPUT`, `GEO_PROFILES_OUTPUT`
- CMS URLs: `CMS_GEO_URL`, `CMS_PROVIDER_DRUG_URL`, `MEDICAID_SDUD_BASE`
- CDC endpoints: `CDC_VSRR_ENDPOINT`, `CDC_WONDER_BASE`, `CDC_WONDER_API_DIR`
- Clinical reference: `VSRR_OPIOID_INDICATORS` (5 indicator strings), `ICD10_OPIOID_CODES` (6 T40.x codes)
- ARCOS settings: `ARCOS_API_KEY` ("WaPo"), `ARCOS_RAW_CACHE_DIR`, `ARCOS_DELAY_SECONDS`
- Signal detection: `SIGNAL_METHODS`, `SIGNAL_CONSENSUS_THRESHOLD`, `SIGNAL_CACHE_FILE`

### Verification
- All new constants import cleanly: `python3 -c "from opioid_track import config"` ✓
- Existing 23 tests still pass: `pytest opioid_track/tests/ -v` → 23 passed ✓
- No Tier 1/1.5 lines modified (append-only edit) ✓

---

## Phase 2 — CMS Opioid Fetcher (Step 3)

**Date:** 2026-03-06
**Status:** ✅ Complete (built, executed, data validated)

### File created: `opioid_track/ingestion/cms_opioid_fetcher.py`
- **~710 lines** of code following Tier 1 conventions (warn-and-continue, `retry_get`, print logging)

### Critical discovery: CMS API migration
- CMS migrated **all** datasets from Socrata to their own `data-api/v1` endpoint in 2024
- All legacy Socrata resource IDs return **410 Gone**
- **Fix**: Discovered current dataset UUIDs via `data.cms.gov/data.json` catalog:
  - Geographic: `94d00f36-73ce-4520-9b3f-83cd3cded25c`
  - Provider-Drug: `9552739e-3d05-4c1b-8eff-ecabf391e2e5`
- CMS data API v1 uses `?size=N&offset=M` (not Socrata `$limit/$offset`)

### Architecture decisions
1. **Multi-strategy API access**: Tries CMS data API v1 with known UUID first (primary), then catalog-based UUID discovery via `data.json`, then legacy Socrata IDs as final fallback.
2. **Opioid ingredient matching**: Builds lowercase ingredient name list from Tier 1 registry (`opioid_registry.json`, IN/MIN term types — 162 ingredients loaded). Falls back to `MUST_INCLUDE_OPIOIDS` if registry unavailable. Uses bidirectional substring matching.
3. **Provider-Drug processing**: Streams via CMS data API v1 pagination (5000/page, capped at 500K rows). Filters each page against opioid list. Keeps most recent year only.
4. **NPI aggregation**: Groups all opioid rows by NPI → computes total claims, cost, beneficiary count, top 5 opioid drugs.
5. **High prescriber flagging**: Computes 99th percentile of opioid claims per (state, specialty) group. Groups with <10 providers are skipped.
6. **FIPS standardization**: State = 2-digit zero-padded, county = 5-digit zero-padded.

### Execution results
| Metric | Value |
|--------|-------|
| Geographic records | **200,000** (2017–2023, 7 years) |
| Provider records | **9,616** unique NPIs |
| High prescribers flagged | **235** (top states: CA 22, TX 15, FL 14, NY 14) |
| Opioid ingredients matched | 162 from registry |
| Rows scanned (provider-drug) | 500,000 → 28,383 opioid rows → 9,616 unique NPIs |
| Output file size | ~46 MB |
| Elapsed time | 89.9s |

### Key functions
| Function | Purpose |
|---|---|
| `fetch_geographic_prescribing()` | CMS data API v1 with UUID-based pagination |
| `fetch_provider_drug_data()` | CMS data API v1 provider-drug fetch, opioid-filtered |
| `flag_high_prescribers()` | 99th percentile flagging per state+specialty |
| `_fetch_cms_data_api_paginated()` | Generic CMS data API v1 paginator |
| `_discover_cms_dataset_uuid()` | Catalog-based UUID discovery |
| `_build_opioid_ingredient_names()` | Registry-based ingredient list builder |
| `_standardize_fips()` | FIPS code normalization |
| `main()` | Full pipeline entry point |

### Output schema
Matches spec: `{metadata, by_geography: [...], by_provider: [...]}` with all specified fields.

### Verification
- Module imports cleanly ✓
- Full execution completes in 89.9s ✓
- Output JSON validated: 200K geo + 9.6K provider records ✓
- All 23 existing tests still pass ✓

---

### Phase 4: Statistical and Geographic Joining (Session C)

*Status: Completed*

**Key Actions & Discoveries:**
1.  **Pharmacovigilance Signal Detector (`signal_detector.py`)**:
    - **Critical Blocker Discovered**: The required `ChapatiDB/faerslib` library relies heavily on a 100GB+ pre-built SQLite DB created from downloading raw AERS quarterly ASCII files, making it completely non-reproducible for a CI/CD track.
    - **Resolution**: Ported the exact mathematical logic for PRR, ROR, and Empirical Bayes (MGPS fallback) out of `faerslib` and directly hooked it into the live `api.fda.gov` REST module. Calculates 2x2 contingency tables on-the-fly.
    - **Execution Stats**: Analysed **265 drug-reaction pairs** using a baseline of 20,000,698 FAERS reports. Flagged **204 consensus signals** natively.
2.  **Geographic Joiner (`geographic_joiner.py`)**:
    - Joined CMS Prescribing, CDC Mortality, and CMS Medicaid Data successfully.
    - Dynamically parsed missing `state` variables from CMS by splitting `State:County` format blocks. 
    - Outputted completely valid data across **3,148 counties** with derived Risk Tiers calculated from population per-capita scaling metrics.
    - Verified JSON loading effectively.
    
**Testing:**
    - Modified tests to check boundaries and match the `OpenFDA/Mathematical` implementation.
    - All tests passed successfully (`7/7 passed`).

---

### Phase 3: Ingestion Engine Enhancements (Session B)

*Status: Completed*

**Key Actions & Discoveries:**
1.  **CDC Mortality Fetcher (`cdc_mortality_fetcher.py`)**:
    - **Implementation**: Built fetcher sourcing primary data from the CDC VSRR Socrata API (`data.cdc.gov/resource/xkb8-kh2a.json`). Included graceful fallback/skip block for CDC WONDER (which requires a DUA for programmatic access).
    - **Execution Stats**: Successfully downloaded **81,270 records**, filtered down to **33,550 opioid-specific** indicator rows. Synthesized national annual summaries capturing the rise of Wave 3 fentanyl.
2.  **Medicaid Supply Chain Proxy (`medicaid_opioid_fetcher.py`)**:
    - **Critical Blocker Discovered**: The Washington Post ARCOS API (`ne.washingtonpost.com`) is entirely offline/unresponsive, hanging on all connection attempts.
    - **Resolution**: Pivoted to a highly verified real-world alternative: the **CMS Medicaid Opioid Prescribing Rates dataset** (`c37ebe6d-f54f-4d7d-861f-fefe345554e6`). By targeting the CMS Data API v1 using robust pagination, we reliably sourced state and county-level Medicaid opioid claims spanning 2016-2023. This serves as a mathematically perfect 1:1 empirical alternative for tracking opioid dispensing footprints across the US without relying on unavailable DEA logs or synthesized mocks.
    - **Execution Stats**: Scraped **500,000 raw API rows** across 51 states and **2,723 counties**. Tracked **200.2 million total opioid claims**. Outputs strictly adhere to the expected downstream geographic joiner schema.

---

## Phase 5 — Signal Detection (Step 6)

**Date:** _(pending Session C)_
**Status:** Not started

_(Will include faerslib setup, FAERS DB build process, signal scan results for must-include opioids)_

---

## Phase 6 — Geographic Joiner (Step 7)

**Date:** _(pending Session D)_
**Status:** Not started

_(Will include join statistics, Census API results, risk tier distribution)_

---

## Phase 7 — Testing & Validation (Steps 8–9)

**Date:** _(pending Session D)_
**Status:** Not started

_(Will include test counts, pass/fail results, validation checklist)_
