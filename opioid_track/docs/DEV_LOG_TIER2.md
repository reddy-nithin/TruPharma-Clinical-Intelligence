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

**Date:** _(pending Session A)_
**Status:** Not started

_(Will be updated during Session A with config entries appended, any issues encountered)_

---

## Phase 2 — CMS Opioid Fetcher (Step 3)

**Date:** _(pending Session A)_
**Status:** Not started

_(Will be updated with API response details, data volumes, column schemas discovered, bugs fixed)_

---

## Phase 3 — CDC Mortality Fetcher (Step 4)

**Date:** _(pending Session B)_
**Status:** Not started

_(Will include VSRR data volume, WONDER availability, opioid wave assignments)_

---

## Phase 4 — ARCOS Supply Chain Fetcher (Step 5)

**Date:** _(pending Session B)_
**Status:** Not started

_(Will include arcospy install status, states fetched/failed, data volumes, cache sizes)_

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
