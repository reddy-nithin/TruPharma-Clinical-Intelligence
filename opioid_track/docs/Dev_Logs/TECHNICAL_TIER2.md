# Opioid Track — Technical Architecture (Tier 2)

**Version:** 2.0.0
**Last Updated:** 2026-03-06
**Prerequisite:** Tier 1 (v1.0.0) + Tier 1.5 (v1.5.0) must be complete

---

## 1. Overview

Tier 2 extends the Opioid Track with three external data ingestion pipelines (CMS prescribing, CDC mortality, CMS Medicaid Opioid Prescribing Rates), a pharmacovigilance signal detection module using faerslib, and a geographic joiner that produces county-level risk profiles. All code lives under `opioid_track/` and does not modify existing Tier 1 files.

**Design principles (carried from Tier 1):**
- Complete isolation from the parent TruPharma project
- Reproducibility-first: uses three pinned GitHub repositories for complex logic
- Warn-and-continue error handling (never crash)
- All data files committed to git for offline reproducibility

**New in Tier 2:**
- Multi-source data joining by FIPS code
- Pharmacovigilance signal detection (PRR, ROR, MGPS)
- Local FAERS SQLite database for fully offline signal queries
- Cached API responses for all external data sources

---

## 2. Directory Structure (Tier 2 Additions)

```
opioid_track/
├── ... (all Tier 1 + 1.5 files, untouched)
├── config.py                            ← APPENDED with Tier 2 entries
├── vendor/
│   ├── cdc-wonder-api/                  ← cloned from alipphardt/cdc-wonder-api
│   └── arcos-py/                        ← cloned fallback if arcospy PyPI fails
├── ingestion/
│   ├── ... (Tier 1 fetchers, untouched)
│   ├── cms_opioid_fetcher.py            ← NEW
│   ├── cdc_mortality_fetcher.py         ← NEW (uses alipphardt/cdc-wonder-api)
│   └── arcos_fetcher.py                 ← NEW (uses arcospy)
├── core/
│   ├── ... (Tier 1 core, untouched)
│   ├── signal_detector.py               ← NEW (uses ChapatiDB/faerslib)
│   └── geographic_joiner.py             ← NEW
├── data/
│   ├── ... (Tier 1 data, untouched)
│   ├── raw/arcos/                       ← NEW (arcospy response cache)
│   ├── opioid_prescribing.json          ← NEW (CMS output)
│   ├── opioid_mortality.json            ← NEW (CDC output)
│   ├── opioid_supply_chain.json         ← NEW (ARCOS output)
│   ├── faers_signal_cache.json          ← NEW (signal detection cache)
│   ├── faers_signal_results.json        ← NEW (signal detection output)
│   └── opioid_geographic_profiles.json  ← NEW (geographic joiner output)
└── tests/
    ├── ... (Tier 1 tests, untouched)
    ├── test_signal_detector.py          ← NEW (6 tests)
    └── test_geographic_joiner.py        ← NEW (5 tests)
```

---

## 3. Data Flow

```
                     +------------------+     +------------------+     +------------------+
                     |   CMS Socrata    |     |   CDC VSRR       |     | WaPo ARCOS API   |
                     |   Data API       |     |   Socrata API    |     | (via arcospy)    |
                     +--------+---------+     +--------+---------+     +--------+---------+
                              |                        |                        |
                              v                        v                        v
                     +--------+---------+     +--------+---------+     +--------+---------+
                     | cms_opioid_      |     | cdc_mortality_   |     | arcos_           |
                     | fetcher.py       |     | fetcher.py       |     | fetcher.py       |
                     +--------+---------+     +--------+---------+     +--------+---------+
                              |                        |                        |
                              v                        |                        v
                     +--------+---------+              |               +--------+---------+
                     | opioid_          |              |               | opioid_supply_   |
                     | prescribing.json |              |               | chain.json       |
                     +--------+---------+              |               +--------+---------+
                              |                        |                        |
                              |               +--------+---------+              |
                              |               | CDC WONDER API   |              |
                              |               | (alipphardt/     |              |
                              |               |  cdc-wonder-api) |              |
                              |               +--------+---------+              |
                              |                        |                        |
                              |                        v                        |
                              |               +--------+---------+              |
                              |               | opioid_          |              |
                              |               | mortality.json   |              |
                              |               +--------+---------+              |
                              |                        |                        |
                              +----------+-------------+------------+-----------+
                                         |                          |
                                         v                          |
                              +----------+-----------+              |
                              |  geographic_         |              |
                              |  joiner.py           |              |
                              |  (+ Census API)      |              |
                              +----------+-----------+              |
                                         |                          |
                                         v                          |
                              +----------+-----------+              |
                              | opioid_geographic_   |              |
                              | profiles.json        |              |
                              +----------------------+              |
                                                                    |
+------------------+                                                |
| Tier 1 Registry  |                                                |
| opioid_registry. +-----+                                         |
| json             |     |                                          |
+------------------+     |                                          |
                         v                                          |
              +----------+-----------+                              |
              | signal_detector.py   |     +--------------------+   |
              | (uses faerslib       |<----+ ChapatiDB/faerslib |   |
              |  local FAERS DB)     |     | (local faers.db)   |   |
              +----------+-----------+     +--------------------+   |
                         |                                          |
                         v                                          |
              +----------+-----------+                              |
              | faers_signal_        |                              |
              | results.json         |                              |
              +----------------------+                              |
```

---

## 4. External Data Sources (Tier 2)

| Source | URL | Purpose | License | Data Period |
|--------|-----|---------|---------|-------------|
| CMS Medicare Part D by Geography | `data.cms.gov` Socrata API | State/county opioid prescribing rates, claims, prescriber counts | Public (US Gov) | 2013–2023 (varies by release) |
| CMS Medicare Part D by Provider-Drug | `data.cms.gov` download | Provider-level opioid prescribing, high prescriber flagging | Public (US Gov) | Most recent year |
| CDC VSRR Provisional Death Counts | `data.cdc.gov/resource/xkb8-kh2a.json` | Monthly/annual overdose death counts by opioid type | Public (US Gov) | 2015–2024 (provisional) |
| CDC WONDER MCD Database | `wonder.cdc.gov` (via `alipphardt/cdc-wonder-api`) | County-level + demographic mortality data (ICD-10 T40.x) | Public (US Gov, data use agreement) | 1999–2022 |
| DEA ARCOS via WaPo API | `arcospy` Python wrapper | County-level pill distribution (oxycodone + hydrocodone) | Public (court order release) | 2006–2014 |
| ChapatiDB/faerslib | `github.com/ChapatiDB/faerslib` | PRR, ROR, MGPS signal detection algorithms + local FAERS DB | Open source | FAERS quarterly data (all years) |
| US Census Bureau ACS | `api.census.gov` | County population for per-capita calculations | Public (US Gov) | 2020 ACS 5-year estimates |

---

## 5. API Endpoints Reference (Tier 2)

### 5.1 CMS Data API (used by cms_opioid_fetcher.py)

> **Note:** CMS migrated from Socrata to their own `data-api/v1` in 2024. All legacy Socrata resource IDs return 410 Gone.

| Endpoint | Purpose |
|----------|---------|
| `GET https://data.cms.gov/data-api/v1/dataset/{uuid}/data?size=5000&offset=0` | Paginated JSON data (primary) |
| `GET https://data.cms.gov/data.json` | Dataset catalog for UUID discovery |
| `GET https://data.cms.gov/resource/{id}.json?$limit=5000&$offset=0` | Legacy Socrata (fallback, mostly 410 Gone) |

**Known UUIDs (discovered 2026-03-06):**
| Dataset | UUID |
|---------|------|
| Medicare Part D Opioid Prescribing by Geography | `94d00f36-73ce-4520-9b3f-83cd3cded25c` |
| Medicare Part D Prescribers by Provider and Drug | `9552739e-3d05-4c1b-8eff-ecabf391e2e5` |

### 5.2 CDC Socrata API (used by cdc_mortality_fetcher.py)

| Endpoint | Purpose |
|----------|---------|
| `GET https://data.cdc.gov/resource/xkb8-kh2a.json?$limit=50000&$order=year DESC,month DESC` | VSRR provisional drug overdose counts |

**Optional header**: `X-App-Token: {token}` for higher rate limits.

### 5.3 CDC WONDER API (used by cdc_mortality_fetcher.py, via vendor)

CDC WONDER uses an XML-based POST API. The `alipphardt/cdc-wonder-api` library constructs the POST body and parses responses. Requires accepting the CDC WONDER data use agreement.

### 5.4 ARCOS API (used by arcos_fetcher.py, via arcospy)

| Function | Returns |
|----------|---------|
| `ArcosPy(key="WaPo")` | Client initialization |
| `arcos.summarized_county_annual(state="XX")` | County-level annual pill summaries |
| `arcos.buyer_details(county, state)` | Buyer-level details |
| `arcos.pharmacy_summary(state)` | Pharmacy-level summaries |

**API Key**: `"WaPo"` (published public key)

### 5.5 Census Bureau API (used by geographic_joiner.py)

| Endpoint | Purpose |
|----------|---------|
| `GET https://api.census.gov/data/2020/acs/acs5?get=NAME,B01003_001E&for=county:*&in=state:*&key={key}` | County population (ACS 5-year) |

---

## 6. Configuration Reference (Tier 2 Additions to config.py)

**Status:** ✅ Appended during Session A (2026-03-06)

### 6.1 New Output Paths

| Constant | Value | Description |
|----------|-------|-------------|
| `CMS_PRESCRIBING_OUTPUT` | `opioid_track/data/opioid_prescribing.json` | CMS fetcher output |
| `CDC_MORTALITY_OUTPUT` | `opioid_track/data/opioid_mortality.json` | CDC fetcher output |
| `ARCOS_OUTPUT` | `opioid_track/data/opioid_supply_chain.json` | ARCOS fetcher output |
| `SIGNAL_RESULTS_OUTPUT` | `opioid_track/data/faers_signal_results.json` | Signal detector output |
| `SIGNAL_CACHE_FILE` | `opioid_track/data/faers_signal_cache.json` | Signal detection cache |
| `GEO_PROFILES_OUTPUT` | `opioid_track/data/opioid_geographic_profiles.json` | Geographic joiner output |

### 6.2 New API URLs

| Constant | Value |
|----------|-------|
| `CMS_GEO_URL` | `https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-opioid-prescribing-rates/medicare-part-d-opioid-prescribing-rates-by-geography` |
| `CMS_PROVIDER_DRUG_URL` | `https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug` |
| `MEDICAID_SDUD_BASE` | `https://data.medicaid.gov/resource` |
| `CDC_VSRR_ENDPOINT` | `https://data.cdc.gov/resource/xkb8-kh2a.json` |
| `CDC_WONDER_BASE` | `https://wonder.cdc.gov` |
| `CENSUS_API_BASE` | `https://api.census.gov/data` |

### 6.3 ARCOS Settings

| Constant | Value | Description |
|----------|-------|-------------|
| `ARCOS_API_KEY` | `"WaPo"` | Published public key |
| `ARCOS_RAW_CACHE_DIR` | `opioid_track/data/raw/arcos` | Per-state cached responses |
| `ARCOS_DELAY_SECONDS` | `0.2` | Rate limiting between calls |

### 6.4 Signal Detection Settings

| Constant | Value | Description |
|----------|-------|-------------|
| `SIGNAL_METHODS` | `["prr", "ror", "mgps"]` | Detection methods to run |
| `SIGNAL_CONSENSUS_THRESHOLD` | `2` | Min methods that must flag for consensus |

### 6.5 Clinical Reference

| Constant | Description |
|----------|-------------|
| `VSRR_OPIOID_INDICATORS` | 5 opioid-related VSRR indicator strings |
| `ICD10_OPIOID_CODES` | T40.0–T40.6 ICD-10 code descriptions |

### 6.6 Census API

| Constant | Value | Description |
|----------|-------|-------------|
| `CENSUS_API_KEY` | `00ea40392d...` (user-provided) | Free key for Census Bureau ACS API |

---

## 7. Output JSON Schemas

### 7.1 opioid_prescribing.json (CMS)

```json
{
  "metadata": {
    "source": "CMS Medicare Part D",
    "years_covered": [2020, 2021, 2022, 2023],
    "generated_at": "ISO-8601"
  },
  "by_geography": [
    {
      "fips_code": "01001",
      "state": "Alabama",
      "county": "Autauga County",
      "year": 2023,
      "total_opioid_claims": 12345,
      "total_opioid_prescribers": 89,
      "opioid_prescribing_rate": 4.2,
      "year_over_year_change": -0.3
    }
  ],
  "by_provider": [
    {
      "npi": "1234567890",
      "specialty": "Internal Medicine",
      "state": "AL",
      "opioid_claims": 500,
      "is_high_prescriber": false,
      "top_opioid_drugs": [{"drug_name": "Oxycodone HCl", "claims": 200}]
    }
  ]
}
```

### 7.2 opioid_mortality.json (CDC)

```json
{
  "metadata": {
    "source": "CDC VSRR + CDC WONDER (alipphardt/cdc-wonder-api)",
    "wonder_available": true,
    "latest_year": 2024,
    "notes": "VSRR data is provisional and subject to revision"
  },
  "annual_national": [
    {
      "year": 2024,
      "opioid_wave": "Wave 3 — Synthetic/fentanyl",
      "total_overdose_deaths": 80391,
      "by_opioid_type": {
        "all_opioids": 55000,
        "synthetic_fentanyl_T40.4": 38000,
        "natural_semisynthetic_T40.2": 12000,
        "heroin_T40.1": 5000,
        "methadone_T40.3": 3000
      }
    }
  ],
  "by_state": [],
  "by_county": [],
  "by_demographics": []
}
```

### 7.3 opioid_supply_chain.json (ARCOS)

```json
{
  "metadata": {
    "source": "DEA ARCOS via Washington Post API (arcospy / marc-rauckhorst/arcos-py)",
    "drugs_covered": ["oxycodone", "hydrocodone"],
    "years_covered": [2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014],
    "states_fetched": 51,
    "states_failed": 0
  },
  "by_state": [
    {
      "state": "AL",
      "total_pills": 1234567890,
      "population": 4800000,
      "pills_per_capita": 257.2,
      "by_year": [{"year": 2006, "pills": 100000000}]
    }
  ],
  "by_county": [
    {
      "fips_code": "01001",
      "state": "AL",
      "county": "Autauga",
      "total_pills": 5000000,
      "pills_per_capita": 91.3,
      "by_year": []
    }
  ]
}
```

### 7.4 faers_signal_results.json

```json
{
  "metadata": {
    "source_library": "ChapatiDB/faerslib",
    "methods_used": ["prr", "ror", "mgps"],
    "consensus_threshold": 2,
    "drugs_scanned": 14,
    "total_signals": 42
  },
  "results": [
    {
      "drug_name": "Morphine",
      "reaction": "Respiratory depression",
      "report_count": 1234,
      "prr": {"value": 3.2, "chi2": 45.6, "signal": true},
      "ror": {"value": 3.5, "ci_lower": 2.1, "ci_upper": 5.8, "signal": true},
      "mgps": {"ebgm": 2.8, "eb05": 2.1, "signal": true},
      "consensus_signal": true,
      "methods_flagging": 3,
      "source_library": "ChapatiDB/faerslib"
    }
  ]
}
```

### 7.5 opioid_geographic_profiles.json

```json
{
  "metadata": {
    "total_counties": 3142,
    "counties_with_2plus_sources": 2800,
    "data_sources_joined": ["CMS", "CDC VSRR", "ARCOS via arcospy"]
  },
  "counties": [
    {
      "fips_code": "01001",
      "state": "Alabama",
      "county": "Autauga",
      "population": 55000,
      "risk_tier": "Medium",
      "risk_score": 0.42,
      "cms_data": {"prescribing_rate": 4.2, "year": 2023},
      "cdc_data": {"opioid_deaths": 12, "death_rate_per_100k": 21.8, "year": 2023},
      "arcos_data": {"total_pills": 5000000, "pills_per_capita": 91.3, "year_range": "2006-2014"},
      "derived_metrics": {"pills_per_death_ratio": 416666.7, "risk_score": 0.42}
    }
  ]
}
```

---

## 8. Error Handling (Tier 2 Additions)

All Tier 2 scripts follow Tier 1's warn-and-continue pattern, plus:

| Scenario | Handling |
|----------|----------|
| CDC WONDER unavailable | Set `wonder_available: false`, continue with VSRR only |
| ARCOS state fetch fails | Log, skip state, continue. Report summary at end |
| faerslib DB not built | Raise clear error with setup instructions |
| Census API unavailable | Fall back to ARCOS population data, or set per-capita as null |
| CMS CSV too large for memory | Chunked reading (pandas `chunksize` or `csv` module) |
| Drug not found in faerslib | Log and skip, not an error |
| FIPS code missing/malformed | Standardize to 5-digit or skip with warning |

---

## 9. Ingestion Pipeline Execution Order (Tier 2)

```bash
# Tier 2 fetchers (run sequentially — each writes independent output files)
python -m opioid_track.ingestion.cms_opioid_fetcher       # → opioid_prescribing.json
python -m opioid_track.ingestion.cdc_mortality_fetcher     # → opioid_mortality.json
python -m opioid_track.ingestion.arcos_fetcher             # → opioid_supply_chain.json

# Signal detection (depends on Tier 1 registry, independent of Tier 2 fetchers)
python -m opioid_track.core.signal_detector                # → faers_signal_results.json

# Geographic joiner (depends on all 3 fetcher outputs)
python -m opioid_track.core.geographic_joiner              # → opioid_geographic_profiles.json

# Tests
pytest opioid_track/tests/ -v                              # 23 existing + 11 new = 34 expected
```

---

## 10. Tier 2 Implementation Statistics

_(Will be populated as each session completes)_

| Ingestion Script | Execution Time | Records Fetched | Output Size | Status |
| :--- | :--- | :--- | :--- | :--- |
| `cms_opioid_fetcher.py` | 89.9s | 200,000 Geo, 9,616 Prov | 46 MB | ✅ Complete |
| `cdc_mortality_fetcher.py` | 9.5s | 81,270 VSRR, 33,550 Opioid | ~1 MB | ✅ Complete |
| `medicaid_opioid_fetcher.py` | 111.5s | 500k claims, 2723 counties | ~6 MB | ✅ Complete |
| `signal_detector.py` | 169.8s | 265 pairs, 204 consensus | ~100 KB | ✅ Complete |
| `geographic_joiner.py`| 1.5s | 3148 county risk profiles | ~1.5 MB | ✅ Complete |
| Total new tests | 11 target | -- | pytest |

---

## 11. Known Limitations (Tier 2)

1. **ARCOS data range**: 2006–2014 only. No public API exists for newer DEA ARCOS data. This covers the Wave 1→2 transition period, which is the most important for understanding prescription opioid supply patterns.
2. **CDC VSRR is provisional**: Death counts are subject to revision. Final counts may differ by 5–10% for the most recent year.
3. **CDC WONDER data use agreement**: County-level mortality data from WONDER requires accepting CDC's data use agreement. If not accepted, the system degrades gracefully to VSRR-only data.
4. **faerslib local DB**: Requires ~2–4 GB of raw FAERS quarterly data downloads to build `faers.db`. Future migration to BigQuery is planned.
5. **CMS data lag**: Medicare Part D data is typically 1–2 years behind the current year.
6. **Census population data**: Using 2020 ACS 5-year estimates. May not reflect recent population shifts.
