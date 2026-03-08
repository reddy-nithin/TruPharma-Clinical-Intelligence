# Opioid Track -- Technical Architecture

**Version:** 1.0.0 (Tier 1)
**Last Updated:** 2026-03-06

---

## 1. Overview

The Opioid Track is an isolated, self-contained add-on to the TruPharma Clinical Intelligence platform. It provides opioid-specific drug classification, NDC lookup, Morphine Milligram Equivalent (MME) conversion, and FAERS adverse-event baselines. All code lives under `opioid_track/` and does not modify any existing TruPharma files.

**Design principles:**
- Complete isolation from the parent project (if the opioid track breaks, TruPharma continues working)
- Reproducibility-first: primary data sourced from pinned, peer-reviewed GitHub repositories
- Warn-and-continue error handling (never crash)
- All data files committed to git for offline reproducibility

---

## 2. Directory Structure

```
opioid_track/
|-- __init__.py                          # Package marker
|-- config.py                            # All paths, URLs, constants, thresholds
|-- requirements.txt                     # requests>=2.28.0
|-- data/
|   |-- .gitkeep
|   |-- raw/                             # Downloaded source files (committed)
|   |   |-- ndc-opioids.csv             #   from ripl-org/historical-ndc
|   |   +-- rxcui_mme_mapping.json      #   from jbadger3/ml_4_pheno_ooe
|   |-- rxclass_opioid_enumeration.json  # Output of rxclass_opioid_fetcher
|   |-- ndc_opioid_lookup.json           # Output of ndc_opioid_classifier
|   |-- mme_reference.json               # Output of mme_mapper
|   |-- faers_opioid_queries.json        # Output of faers_opioid_filter
|   +-- opioid_registry.json             # THE canonical merged registry
|-- ingestion/
|   |-- __init__.py                      # Shared retry helper, HTTP session factory
|   |-- rxclass_opioid_fetcher.py        # Step 4: enumerate opioids via RxClass API
|   |-- ndc_opioid_classifier.py         # Step 5: NDC classification (ripl-org + OpenFDA)
|   |-- mme_mapper.py                    # Step 6: MME factors (jbadger3 + CDC)
|   +-- faers_opioid_filter.py           # Step 7: FAERS query templates + baselines
|-- core/
|   |-- __init__.py
|   |-- registry_builder.py              # Step 8: merge all ingestion outputs
|   +-- registry.py                      # Step 9: runtime API (lazy-loaded singleton)
|-- tests/
|   |-- __init__.py
|   +-- test_registry.py                 # Step 10: validation tests
+-- docs/
    |-- DEV_LOG.md                       # Running build diary
    |-- TECHNICAL.md                     # This file
    |-- TIER1_INSTRUCTIONS_REVISED.md
    |-- TIER2_INSTRUCTIONS_REVISED.md
    +-- TIER3_INSTRUCTIONS_REVISED.md
```

---

## 3. Data Flow

```
                      +---------------------+
                      | ripl-org/           |
                      | historical-ndc      |
                      | (ndc-opioids.csv)   |
                      +--------+------------+
                               |
                               v
+------------------+   +-------+-----------+   +-------------------+
| RxClass API      |   | ndc_opioid_       |   | jbadger3/         |
| (ATC, MED-RT,    |   | classifier.py     |   | ml_4_pheno_ooe    |
|  FDA EPC)        |   |                   |   | (rxcui_mme_       |
+--------+---------+   +-------+-----------+   |  mapping.json)    |
         |                     |               +--------+----------+
         v                     v                        |
+--------+---------+   +-------+-----------+            v
| rxclass_opioid_  |   | ndc_opioid_       |   +--------+----------+
| fetcher.py       |   | lookup.json       |   | mme_mapper.py     |
+--------+---------+   +-------------------+   +--------+----------+
         |                     |                        |
         v                     |                        v
+--------+---------+           |               +--------+----------+
| rxclass_opioid_  |           |               | mme_reference.    |
| enumeration.json |           |               | json              |
+--------+---------+           |               +--------+----------+
         |                     |                        |
         |    +----------------+----+                   |
         |    | OpenFDA FAERS API   |                   |
         |    +--------+------------+                   |
         |             |                                |
         |             v                                |
         |    +--------+------------+                   |
         |    | faers_opioid_       |                   |
         |    | filter.py           |                   |
         |    +--------+------------+                   |
         |             |                                |
         |             v                                |
         |    +--------+------------+                   |
         |    | faers_opioid_       |                   |
         |    | queries.json        |                   |
         |    +---------------------+                   |
         |             |                                |
         +------+------+------+-------------------------+
                |             |
                v             v
        +-------+-------------+-------+
        |    registry_builder.py      |
        |    (merge all 4 outputs)    |
        +-------------+---------------+
                      |
                      v
        +-------------+---------------+
        |    opioid_registry.json     |
        |    (THE canonical output)   |
        +-------------+---------------+
                      |
                      v
        +-------------+---------------+
        |    registry.py              |
        |    (runtime API)            |
        |                             |
        |  is_opioid(rxcui)           |
        |  is_opioid_by_ndc(ndc)      |
        |  get_opioid_profile(rxcui)  |
        |  get_mme_factor(name)       |
        |  calculate_daily_mme(...)   |
        |  list_all_opioid_rxcuis()   |
        |  get_faers_baseline()       |
        |  ...                        |
        +-----------------------------+
```

---

## 4. External Data Sources

| Source | URL | Purpose | License | Update Cadence |
|--------|-----|---------|---------|----------------|
| ripl-org/historical-ndc | `https://raw.githubusercontent.com/ripl-org/historical-ndc/master/output/ndc-opioids.csv` | Pre-classified NDC-to-opioid lookup covering 1998-2018 (195,451 entries). Published in JAMIA 2020. CSV columns: `['ndc', 'opioid', 'recovery']` with 0/1 values. | MIT | Static (archived dataset) |
| jbadger3/ml_4_pheno_ooe | `https://raw.githubusercontent.com/jbadger3/ml_4_pheno_ooe/master/supporting_files/mme_OMOP.json` | RxCUI-level MME conversion factors (12,082 mappings). File is `mme_OMOP.json` in `supporting_files/` on `master` branch. Schema: `{rxcui_string: float}`. MIT license. | MIT | Static (archived dataset) |
| NLM RxClass API | `https://rxnav.nlm.nih.gov/REST/rxclass` | Enumerates opioid drugs across ATC, MED-RT, and FDA EPC classification hierarchies. | Public domain (US Gov) | Monthly (NLM release cycle) |
| NLM RxNorm API | `https://rxnav.nlm.nih.gov/REST` | Resolves RxCUIs to ingredients, retrieves NDC lists, cross-references drug identifiers. | Public domain (US Gov) | Monthly |
| OpenFDA Drug Event API | `https://api.fda.gov/drug/event.json` | FAERS adverse event reports. Used for opioid safety baselines and query templates. | Public domain (US Gov) | Quarterly |
| OpenFDA NDC API | `https://api.fda.gov/drug/ndc.json` | Supplemental NDC classification for products not in the historical ripl-org dataset (post-2018). | Public domain (US Gov) | Ongoing |
| OpenFDA Label API | `https://api.fda.gov/drug/label.json` | SPL Set ID and UNII lookups for registry enrichment. | Public domain (US Gov) | Ongoing |

---

## 5. API Endpoints Reference

### 5.1 RxClass API (used by rxclass_opioid_fetcher.py)

**Base URL:** `https://rxnav.nlm.nih.gov/REST/rxclass`

| Endpoint | Parameters | Purpose |
|----------|------------|---------|
| `GET /classMembers.json` | `classId={atc_code}&relaSource=ATC` | Enumerate drugs in an ATC opioid class |
| `GET /classMembers.json` | `classId={concept_id}&relaSource=MEDRT&rela=has_moa` | Enumerate drugs by MED-RT mechanism of action (note: `rela` must be lowercase) |
| `GET /classMembers.json` | `classId={epc}&relaSource=FDASPL&rela=has_EPC` | Enumerate drugs by FDA Established Pharmacologic Class |

**Rate limit:** 20 requests/second (configured as `RXNAV_DELAY_SECONDS = 0.05`)

### 5.2 RxNorm API (used by multiple scripts)

**Base URL:** `https://rxnav.nlm.nih.gov/REST`

| Endpoint | Parameters | Purpose |
|----------|------------|---------|
| `GET /rxcui/{rxcui}/allrelated.json` | -- | Resolve an RxCUI to its related concepts (ingredients, brands, etc.) |
| `GET /rxcui/{rxcui}/ndcs.json` | -- | Get all NDC codes associated with an RxCUI |
| `GET /rxcui.json` | `name={name}&search=1` | Find the RxCUI for a drug name |

**Rate limit:** 20 requests/second (same NLM infrastructure)

### 5.3 OpenFDA APIs

**Base URL:** `https://api.fda.gov/drug`

| Endpoint | Parameters | Purpose |
|----------|------------|---------|
| `GET /event.json` | `search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"&count=patient.reaction.reactionmeddrapt.exact` | Top adverse reactions for opioid agonists |
| `GET /event.json` | `search=...+AND+seriousnessdeath:1&count=...` | Death-associated opioid reactions |
| `GET /event.json` | `search=...&count=patient.patientsex` | Sex distribution of opioid adverse events |
| `GET /event.json` | `search=...&count=patient.patientonsetage` | Age distribution of opioid adverse events |
| `GET /event.json` | `search=...&count=receivedate` | Yearly reporting trend |
| `GET /ndc.json` | `search=pharm_class:"opioid"&limit=100&skip={offset}` | NDC codes classified as opioid (paginated) |
| `GET /label.json` | `search=openfda.rxcui:"{rxcui}"&limit=1` | SPL Set ID and UNII for an RxCUI |

**Rate limit:** ~4 requests/second (configured as `OPENFDA_DELAY_SECONDS = 0.25`)

---

## 6. Configuration Reference (config.py)

### 6.1 Paths

| Constant | Value | Description |
|----------|-------|-------------|
| `OPIOID_DATA_DIR` | `"opioid_track/data"` | Base directory for all data files |
| `RXCLASS_OUTPUT` | `"opioid_track/data/rxclass_opioid_enumeration.json"` | Output of rxclass_opioid_fetcher |
| `NDC_LOOKUP_OUTPUT` | `"opioid_track/data/ndc_opioid_lookup.json"` | Output of ndc_opioid_classifier |
| `MME_REFERENCE_OUTPUT` | `"opioid_track/data/mme_reference.json"` | Output of mme_mapper |
| `FAERS_QUERIES_OUTPUT` | `"opioid_track/data/faers_opioid_queries.json"` | Output of faers_opioid_filter |
| `REGISTRY_OUTPUT` | `"opioid_track/data/opioid_registry.json"` | The canonical merged registry |
| `RIPL_NDC_CSV_LOCAL` | `"opioid_track/data/raw/ndc-opioids.csv"` | Cached download from ripl-org |
| `JBADGER_MME_JSON_LOCAL` | `"opioid_track/data/raw/rxcui_mme_mapping.json"` | Cached download from jbadger3 |

### 6.2 API Base URLs

| Constant | Value |
|----------|-------|
| `RXNAV_BASE` | `"https://rxnav.nlm.nih.gov/REST"` |
| `RXCLASS_BASE` | `"https://rxnav.nlm.nih.gov/REST/rxclass"` |
| `OPENFDA_BASE` | `"https://api.fda.gov/drug"` |
| `DAILYMED_BASE` | `"https://dailymed.nlm.nih.gov/dailymed/services/v2"` |

### 6.3 Rate Limiting

| Constant | Value | Effective Rate |
|----------|-------|----------------|
| `RXNAV_DELAY_SECONDS` | `0.05` | 20 req/sec max |
| `OPENFDA_DELAY_SECONDS` | `0.25` | ~4 req/sec |

### 6.4 Opioid Classification Constants

| Constant | Type | Description |
|----------|------|-------------|
| `ATC_OPIOID_CLASSES` | `dict[str, str]` | 11 ATC sub-class codes (N02A*, N07BC) mapped to human-readable descriptions. Yielded 38 RxCUIs. |
| `ATC_TO_CATEGORY` | `dict[str, str]` | ATC code to opioid category: natural/semi-synthetic, synthetic, combination, treatment/recovery |
| `MEDRT_OPIOID_CONCEPTS` | `dict[str, str]` | 3 MED-RT concept IDs: N0000191866 (mu-Receptor Agonists), N0000000154 (Antagonists), N0000175685 (Partial Agonists). Yielded 54 RxCUIs. |
| `FDA_EPC_OPIOID` | `list[str]` | 5 FDA EPC class IDs (numeric format, e.g., N0000175690). Yielded 34 RxCUIs. |
| `DEA_SCHEDULES` | `list[str]` | CII, CIII, CIV, CV |
| `MUST_INCLUDE_OPIOIDS` | `list[str]` | 14 opioid names that must appear in the final registry for validation |

### 6.5 MME Constants

| Constant | Type | Description |
|----------|------|-------------|
| `CDC_MME_FACTORS` | `dict[str, float]` | 14 named-ingredient MME factors from CDC Clinical Practice Guideline 2022. Fallback if jbadger3 download fails. |
| `METHADONE_MME_TIERS` | `list[tuple]` | 4 dose-dependent tiers for methadone conversion (dose-dependent, not a flat factor) |

### 6.6 Safety Monitoring

| Constant | Type | Description |
|----------|------|-------------|
| `OPIOID_SAFETY_TERMS` | `list[str]` | 20 MedDRA preferred terms for opioid safety signal monitoring (respiratory depression, overdose, death, withdrawal, etc.) |

---

## 7. Registry Schema (opioid_registry.json)

The canonical output file has the following top-level structure:

```json
{
  "metadata": {
    "generated_at": "ISO-8601 timestamp",
    "version": "1.0.0",
    "tier": 1,
    "total_opioid_rxcuis": "<int>",
    "total_opioid_ndcs": "<int>",
    "data_sources": {
      "ndc_classification": "ripl-org/historical-ndc + OpenFDA",
      "mme_mapping": "jbadger3/ml_4_pheno_ooe + CDC Clinical Practice Guideline 2022",
      "drug_enumeration": "NLM RxClass API (ATC, MED-RT, FDA EPC hierarchies)"
    },
    "description": "Opioid Track registry -- isolated add-on for TruPharma"
  },
  "opioid_drugs": [ "...array of opioid drug entries..." ],
  "mme_reference": { "...MME conversion data..." },
  "ndc_lookup": { "...NDC-to-opioid mapping..." },
  "faers_baseline": { "...adverse event baselines..." }
}
```

### 7.1 opioid_drugs entry

```json
{
  "rxcui": "7052",
  "drug_name": "Morphine",
  "drug_class": "Opioid Agonist",
  "schedule": "CII",
  "atc_codes": ["N02AA01"],
  "opioid_category": "natural/semi-synthetic",
  "active_ingredients": [
    { "rxcui": "7052", "name": "Morphine", "tty": "IN", "is_opioid_component": true }
  ],
  "ndc_codes": ["00069-0770-20", "..."],
  "spl_set_ids": ["abc-def-123"],
  "mme_conversion_factor": 1.0,
  "mme_source": "cdc_named",
  "pharmacologic_classes": {
    "epc": ["Opioid Agonist [EPC]"],
    "moa": ["Full Opioid Agonist"],
    "atc": ["Natural opium alkaloids"]
  }
}
```

### 7.2 mme_reference section

```json
{
  "cdc_factors": {
    "codeine": { "mme_factor": 0.15, "source": "CDC Clinical Practice Guideline 2022", "notes": "per mg oral" }
  },
  "rxcui_mme_map": {
    "2670": { "mme_factor": 1.0, "drug_name": "Morphine", "source": "jbadger3/ml_4_pheno_ooe" }
  },
  "methadone_tiers": [
    { "max_daily_dose_mg": 20, "mme_factor": 4.7 }
  ],
  "risk_thresholds": {
    "increased_risk_mme": 50,
    "high_risk_mme": 90
  }
}
```

---

## 8. Runtime API Reference (registry.py)

All functions are importable from `opioid_track.core.registry`. The registry is lazy-loaded from `opioid_registry.json` on first access.

| Function | Signature | Returns | Description |
|----------|-----------|---------|-------------|
| `is_opioid` | `(rxcui: str) -> bool` | `bool` | Check if an RxCUI is a known opioid |
| `is_opioid_by_ndc` | `(ndc: str) -> bool` | `bool` | Check if an NDC code maps to an opioid (auto-normalizes NDC format) |
| `get_opioid_profile` | `(rxcui: str) -> dict or None` | `dict` | Full profile for an opioid RxCUI, or None if not found |
| `get_mme_factor` | `(ingredient_name: str) -> float or None` | `float` | MME conversion factor for a named ingredient |
| `calculate_daily_mme` | `(ingredient_name: str, daily_dose_mg: float) -> dict` | `dict` | `{"daily_mme": float, "risk_level": str, "mme_factor_used": float}` |
| `list_all_opioid_rxcuis` | `() -> list[str]` | `list` | All known opioid RxCUIs |
| `list_all_opioid_ndcs` | `() -> list[str]` | `list` | All known opioid NDC codes |
| `get_opioids_by_category` | `(category: str) -> list[dict]` | `list` | Filter opioids by category (natural/semi-synthetic, synthetic, combination, treatment/recovery) |
| `get_opioids_by_schedule` | `(schedule: str) -> list[dict]` | `list` | Filter opioids by DEA schedule (CII, CIII, CIV, CV) |
| `get_drugs_containing_ingredient` | `(ingredient_rxcui: str) -> list[dict]` | `list` | Find all products containing a given ingredient |
| `get_faers_baseline` | `() -> dict` | `dict` | FAERS adverse event baseline snapshot |
| `registry_version` | `() -> str` | `str` | Registry version string |
| `registry_stats` | `() -> dict` | `dict` | Summary statistics (total drugs, NDCs, coverage) |
| `refresh` | `() -> None` | `None` | Clear cached data, force reload from disk |

---

## 9. Validation Thresholds

The registry builder validates the final output against these minimum thresholds:

| Metric | Minimum | Actual (Tier 1) | Status |
|--------|---------|-----------------|--------|
| Unique opioid RxCUIs | 200 | 189 | Soft miss (non-blocking; 85 drug entries with 189 unique RxCUIs across ingredients) |
| NDC codes in lookup | 2,000 | 197,043 | Pass |
| MME factors for named ingredients | 14 | 14 CDC + 12,082 RxCUI-level | Pass |
| `MUST_INCLUDE_OPIOIDS` present | 14/14 | 14/14 | Pass |
| NDC entries from ripl-org-historical | 80%+ | 99.2% (195,451 of 197,043) | Pass |
| No duplicate RxCUIs | 0 duplicates | 0 | Pass |

---

## 10. Ingestion Pipeline Execution Order

Scripts must be run sequentially from the project root:

```bash
# Step 1: Enumerate opioids from RxClass API
python -m opioid_track.ingestion.rxclass_opioid_fetcher

# Step 2: Classify NDC codes (downloads ripl-org/historical-ndc)
python -m opioid_track.ingestion.ndc_opioid_classifier

# Step 3: Build MME reference (downloads jbadger3/ml_4_pheno_ooe)
python -m opioid_track.ingestion.mme_mapper

# Step 4: Fetch FAERS baselines
python -m opioid_track.ingestion.faers_opioid_filter

# Step 5: Merge into canonical registry
python -m opioid_track.core.registry_builder

# Step 6: Run tests
pytest opioid_track/tests/
```

Steps 1-4 are independent of each other (they only write to separate output files), but are run sequentially to respect API rate limits. Step 5 depends on all four outputs existing. Step 6 depends on the registry existing.

---

## 11. Error Handling Strategy

All ingestion scripts follow the same pattern:

1. **HTTP errors:** Retry with exponential backoff (max 3 attempts). HTTP 404 responses skip retries (definitive "not found"). On final failure, log a warning and skip the item.
2. **Missing data:** Log a warning, continue with partial data. Validation at registry-build time catches gaps.
3. **Schema changes:** Runtime inspection of CSV columns and JSON keys before parsing. Adapt or log a clear error.
4. **Network unavailable:** If raw files already exist locally, use the cached version. If no cache and no network, raise a `FileNotFoundError` with manual download instructions.
5. **Rate limiting:** Respect `RXNAV_DELAY_SECONDS` and `OPENFDA_DELAY_SECONDS` between every API call.

The shared retry helper in `ingestion/__init__.py` implements exponential backoff and sets `User-Agent: "TruPharma-Opioid/1.0"` on all requests.

---

## 12. Tier 1 Implementation Statistics

Final production numbers from the completed Tier 1 build:

### Data Volume

| Dataset | Count | Size | Source |
|---------|-------|------|--------|
| Opioid drug entries | 85 | -- | RxClass API (ATC + MED-RT + FDA EPC) |
| Unique RxCUIs (across all entries) | 189 | -- | Deduplicated from 3 hierarchies |
| NDC lookup entries | 197,043 | -- | 195,451 ripl-org + 1,592 OpenFDA |
| Opioid NDCs | 4,259 | -- | Subset of NDC lookup |
| Recovery drug NDCs | 422 | -- | Subset of NDC lookup |
| RxCUI-level MME mappings | 12,082 | -- | jbadger3/ml_4_pheno_ooe |
| CDC named MME factors | 14 | -- | CDC Clinical Practice Guideline 2022 |
| FAERS query templates | 7 | -- | OpenFDA Drug Event API |
| FAERS yearly trend data points | 7,065 | -- | OpenFDA Drug Event API |
| Canonical registry file | 1 | 42.9 MB | opioid_registry.json |
| Raw cache: ndc-opioids.csv | 1 | 2.7 MB | ripl-org/historical-ndc |
| Raw cache: rxcui_mme_mapping.json | 1 | 212 KB | jbadger3/ml_4_pheno_ooe |

### RxClass Enumeration Breakdown

| Hierarchy | Classes Queried | RxCUIs Found |
|-----------|----------------|--------------|
| ATC | 11 | 38 |
| MED-RT (MOA) | 3 (mu-Receptor Agonists, Antagonists, Partial Agonists) | 54 |
| FDA EPC | 5 | 34 |
| **Total (deduplicated)** | **19** | **85 unique** |

### MME Cross-Validation

4 discrepancies found between jbadger3 RxCUI-level factors and CDC named factors:
- Tramadol, Meperidine, Fentanyl, Buprenorphine
- Resolution: CDC factors take priority as the authoritative source

### Test Coverage

| Metric | Value |
|--------|-------|
| Total tests | 21 |
| Passing | 21 |
| Failing | 0 |
| Registry API functions tested | 13 public + refresh() + normalize_ndc() |

### Known Limitations (Tier 1)

1. **RxCUI count (189) below 200 soft target:** Ingredient-level enumeration yields fewer unique RxCUIs than product-level. This is expected and non-blocking. Tier 2 will expand coverage.
2. **OpenFDA Label API 404s:** Label lookups return 404 for ingredient-level RxCUIs because SPL labels are indexed at the product level. Non-critical for Tier 1.
3. **RxNorm NDC associations:** Zero NDC results for ingredient-level RxCUIs via the RxNorm API. The ripl-org dataset provides comprehensive NDC coverage independently.
4. **ripl-org dataset static (1998-2018):** Post-2018 NDCs come from OpenFDA only (1,592 entries). Tier 2 may add additional supplemental sources.
