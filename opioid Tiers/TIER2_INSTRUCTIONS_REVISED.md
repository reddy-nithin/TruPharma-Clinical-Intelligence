# TIER 2 — External Data Ingestion + Signal Detection
# (Revised: reproducibility-first using existing GitHub repos)

## Instructions for Coding Agent

You are continuing work on the **Opioid Intelligence Track**, an isolated add-on to the TruPharma Clinical Intelligence project. Tier 1 is already complete. The opioid registry at `opioid_track/data/opioid_registry.json` exists and is loaded via `opioid_track/core/registry.py`.

**IMPORTANT:** Do not modify any existing TruPharma files outside of `opioid_track/`. Do not modify any Tier 1 files unless fixing a bug. All new code goes into `opioid_track/`.

> **Reproducibility note:** Three GitHub repositories are used in this tier instead of building equivalent logic from scratch. This significantly reduces implementation risk, covers edge cases that took those authors months to handle, and makes outputs auditable against their published methods.
>
> | Repo | Used for | Install |
> |---|---|---|
> | `marc-rauckhorst/arcos-py` | ARCOS WaPo API wrapper (Python) | `pip install arcospy` |
> | `ChapatiDB/faerslib` | PRR, ROR, MGPS signal detection algorithms | `pip install faerslib` |
> | `alipphardt/cdc-wonder-api` | CDC WONDER programmatic API client | clone + local import |

---

## Step 0: Understand What Exists

Before writing any code:

1. Read `opioid_track/README.md` and `opioid_track/config.py` to understand the Tier 1 structure.
2. Read `opioid_track/core/registry.py` — you will import from this module frequently. Understand all its functions.
3. Open `opioid_track/data/opioid_registry.json` and understand the schema.
4. Read every file in `opioid_track/ingestion/` to understand the code patterns, error handling, and logging used in Tier 1. Match those conventions exactly.
5. Read the existing TruPharma `src/` directory to understand the parent project. Do not modify it.

---

## Step 1: Extend the Directory Structure

Add these new files to the existing `opioid_track/` directory:

```
opioid_track/
├── ... (all Tier 1 files, untouched)
├── ingestion/
│   ├── ... (Tier 1 fetchers, untouched)
│   ├── cms_opioid_fetcher.py           ← NEW
│   ├── cdc_mortality_fetcher.py        ← NEW (uses alipphardt/cdc-wonder-api)
│   └── arcos_fetcher.py                ← NEW (uses arcospy / marc-rauckhorst/arcos-py)
├── core/
│   ├── ... (Tier 1 core, untouched)
│   ├── signal_detector.py              ← NEW (uses ChapatiDB/faerslib)
│   └── geographic_joiner.py            ← NEW
├── data/
│   ├── ... (Tier 1 data, untouched)
│   ├── opioid_prescribing.json         ← NEW (output)
│   ├── opioid_mortality.json           ← NEW (output)
│   ├── opioid_supply_chain.json        ← NEW (output)
│   ├── faers_signal_results.json       ← NEW (output)
│   └── opioid_geographic_profiles.json ← NEW (output)
└── tests/
    ├── ... (Tier 1 tests, untouched)
    ├── test_signal_detector.py         ← NEW
    └── test_geographic_joiner.py       ← NEW
```

---

## Step 2: Add Tier 2 Config Entries

Open `opioid_track/config.py` and **append** these entries (do not change existing entries):

```python
# === TIER 2 ADDITIONS ===

# CMS data
CMS_PRESCRIBING_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_prescribing.json"
CMS_GEO_URL = "https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-opioid-prescribing-rates/medicare-part-d-opioid-prescribing-rates-by-geography"
CMS_PROVIDER_DRUG_URL = "https://data.cms.gov/provider-summary-by-type-of-service/medicare-part-d-prescribers/medicare-part-d-prescribers-by-provider-and-drug"
MEDICAID_SDUD_BASE = "https://data.medicaid.gov/resource"

# CDC mortality data
CDC_MORTALITY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_mortality.json"
CDC_VSRR_ENDPOINT = "https://data.cdc.gov/resource/xkb8-kh2a.json"
CDC_WONDER_BASE = "https://wonder.cdc.gov"
# alipphardt/cdc-wonder-api clone path (cloned during Step 4 setup)
CDC_WONDER_API_DIR = "opioid_track/vendor/cdc-wonder-api"
VSRR_OPIOID_INDICATORS = [
    "Opioids (T40.0-T40.4,T40.6)",
    "Natural & semi-synthetic opioids (T40.2)",
    "Methadone (T40.3)",
    "Synthetic opioids, excl. methadone (T40.4)",
    "Heroin (T40.1)",
]
ICD10_OPIOID_CODES = {
    "T40.0": "Opium",
    "T40.1": "Heroin",
    "T40.2": "Natural/semi-synthetic opioids",
    "T40.3": "Methadone",
    "T40.4": "Synthetic opioids (primarily fentanyl)",
    "T40.6": "Other/unspecified narcotics",
}

# ARCOS supply chain data (uses arcospy / marc-rauckhorst/arcos-py)
ARCOS_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_supply_chain.json"
ARCOS_API_KEY = "WaPo"   # the published public key for the WaPo ARCOS API
ARCOS_RAW_CACHE_DIR = f"{OPIOID_DATA_DIR}/raw/arcos"
ARCOS_DELAY_SECONDS = 0.2

# Signal detection (uses ChapatiDB/faerslib)
SIGNAL_RESULTS_OUTPUT = f"{OPIOID_DATA_DIR}/faers_signal_results.json"
SIGNAL_CACHE_FILE = f"{OPIOID_DATA_DIR}/faers_signal_cache.json"
# faerslib supports: "prr", "ror", "mgps" (EBGM-based)
SIGNAL_METHODS = ["prr", "ror", "mgps"]
SIGNAL_CONSENSUS_THRESHOLD = 2  # minimum methods that must flag for consensus signal

# Geographic profiles
GEO_PROFILES_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_geographic_profiles.json"
CENSUS_API_BASE = "https://api.census.gov/data"
```

---

## Step 3: Build `opioid_track/ingestion/cms_opioid_fetcher.py`

This script ingests CMS Medicare Part D opioid prescribing data. *(Built directly against the CMS data API — no repo substitute needed here.)*

### What this script must do:

1. **Download the Medicare Part D Opioid Prescribing by Geography CSV.**
   - Try the CMS data API first:
     ```
     GET https://data.cms.gov/data-api/v1/dataset?keyword=opioid+prescribing+geography
     ```
   - If the dataset ID is not immediately discovered, fall back to direct CSV download from the web page URL in config.
   - If the Socrata endpoint is available (data.cms.gov uses Socrata), use:
     ```
     GET https://data.cms.gov/resource/{resource_id}.json?$limit=5000&$offset=0
     ```

2. **Parse the geographic prescribing data.** Key columns to extract:
   - `Prscrbr_Geo_Lvl` (National, State, or County)
   - `Prscrbr_Geo_Desc` (geographic name)
   - `Prscrbr_Geo_Cd` (FIPS code for states/counties)
   - `Tot_Opioid_Clms` (total opioid claims)
   - `Opioid_Prscrbng_Rate` (opioid prescribing rate per 100)
   - `Tot_Opioid_Prscrbrs` (number of opioid prescribers)
   - `Opioid_Prscrbng_Rate_1Y_Chg` (year-over-year change)
   - Year column (varies by dataset version)

3. **Download the Medicare Part D Prescribers by Provider and Drug CSV** for the most recent year only (the full dataset is very large — 1.38M+ rows).
   - After downloading, filter to only rows where `Gnrc_Name` (generic drug name) matches an opioid ingredient from the Tier 1 registry.
   - Get the ingredient list: import `opioid_track.core.registry` and call `list_all_opioid_rxcuis()` to get drug names, or build a name list from the registry JSON.
   - Use case-insensitive substring matching (e.g., "oxycodone" should match "Oxycodone HCl").

4. **Flag high prescribers:** For each state+specialty combination, compute the 99th percentile of opioid claims. Mark providers above that threshold as `is_high_prescriber: true`.

5. **Standardize FIPS codes** to 5-digit format (2-digit state + 3-digit county, zero-padded). States are 2-digit. If county FIPS includes state prefix already, keep as-is.

6. **Save output** to `config.CMS_PRESCRIBING_OUTPUT` as JSON:
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
         "opioid_drug_cost": 15000.50,
         "opioid_bene_count": 200,
         "is_high_prescriber": false,
         "top_opioid_drugs": [
           { "drug_name": "Oxycodone HCl", "claims": 200 }
         ]
       }
     ]
   }
   ```

7. **Handle large files carefully.** Use chunked CSV reading (`pandas` chunksize or `csv` module). Process in chunks and aggregate.

8. **Add a `main()` function.**

---

## Step 4: Build `opioid_track/ingestion/cdc_mortality_fetcher.py`

> **Reproducibility: uses `alipphardt/cdc-wonder-api`**
>
> CDC WONDER's web interface cannot be queried programmatically without a client that handles its specific POST-based request format. Instead of building this from scratch, use the `alipphardt/cdc-wonder-api` library which provides a Python interface for CDC WONDER's Multiple Cause of Death database. Clone it as a vendor dependency.

### Setup — clone `alipphardt/cdc-wonder-api`:

```bash
mkdir -p opioid_track/vendor
cd opioid_track/vendor
git clone https://github.com/alipphardt/cdc-wonder-api.git
```

Then in Python, add the vendor directory to the path before importing:
```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "vendor", "cdc-wonder-api"))
```

**Before building the fetcher**, read the `alipphardt/cdc-wonder-api` README and any example notebooks to understand the query builder pattern, response format, and required parameters. The library constructs POST requests to WONDER's XML-based API.

### What this script must do:

1. **Fetch CDC VSRR Provisional Drug Overdose Death Counts** from the Socrata API (this does NOT require the WONDER API and is the primary data source):
   ```
   GET https://data.cdc.gov/resource/xkb8-kh2a.json?$limit=50000&$order=year DESC,month DESC
   ```
   This returns JSON directly. No API key needed, but add an app token header if rate-limited:
   ```
   X-App-Token: (optional — register at data.cdc.gov for higher limits)
   ```

2. **Filter for opioid-related indicators** using `config.VSRR_OPIOID_INDICATORS`. The `indicator` field in the response contains strings like "Opioids (T40.0-T40.4,T40.6)". Filter rows where the `indicator` matches any of the configured values.

3. **Parse and structure the data:**
   - Extract: `state_name`, `year`, `month`, `indicator`, `data_value` (death count — may be string, convert to int), `predicted_value` (model-predicted count)
   - Some cells may be null or contain suppression notes — handle gracefully
   - Group by state and year for annual totals

4. **Build national-level annual summary** by summing across all states per year. Structure:
   ```json
   {
     "year": 2024,
     "total_overdose_deaths": 80391,
     "by_opioid_type": {
       "all_opioids": 55000,
       "natural_semisynthetic_T40.2": 12000,
       "heroin_T40.1": 5000,
       "synthetic_fentanyl_T40.4": 38000,
       "methadone_T40.3": 3000
     }
   }
   ```

5. **Build state-level annual data** with the same opioid type breakdown.

6. **Use `alipphardt/cdc-wonder-api` to supplement with county-level and demographic data from CDC WONDER MCD database.** Follow the library's documented query builder to construct a request for:
   - Deaths by county (ICD-10 multiple cause codes T40.0-T40.4, T40.6)
   - Deaths by age group (10-year bands)
   - Deaths by sex
   - Deaths by race/ethnicity

   If WONDER access returns an error or is unavailable during the run, catch the exception, log it, set `"wonder_available": false` in the output metadata, and continue. The VSRR data (step 1) is sufficient to proceed to Tier 3.

7. **Tag each year with the opioid wave:**
   - 1999–2010: "Wave 1 — Prescription opioids"
   - 2010–2013: "Wave 2 — Heroin"
   - 2013–present: "Wave 3 — Synthetic/fentanyl"

8. **Save output** to `config.CDC_MORTALITY_OUTPUT`:
   ```json
   {
     "metadata": {
       "source": "CDC VSRR + CDC WONDER (alipphardt/cdc-wonder-api)",
       "wonder_available": true,
       "generated_at": "ISO-8601",
       "latest_year": 2024,
       "notes": "VSRR data is provisional and subject to revision"
     },
     "annual_national": [ ... ],
     "by_state": [ ... ],
     "by_county": [ ... ],
     "by_demographics": [ ... ]
   }
   ```

9. **Add a `main()` function.**

---

## Step 5: Build `opioid_track/ingestion/arcos_fetcher.py`

> **Reproducibility: uses `arcospy` (marc-rauckhorst/arcos-py)**
>
> Instead of building raw HTTP calls to the WaPo ARCOS API, use `arcospy` — the official Python wrapper maintained for this exact purpose. It handles pagination, the API key, endpoint routing, and returns data as pandas DataFrames. This eliminates the need to reverse-engineer the API's endpoint structure.

### Setup:

```bash
pip install arcospy
```

If `arcospy` installation fails (e.g., outdated on PyPI), clone the source directly:
```bash
git clone https://github.com/marc-rauckhorst/arcos-py.git opioid_track/vendor/arcos-py
# then: sys.path.insert(0, "opioid_track/vendor/arcos-py")
```

**Before writing the fetcher**, read the `arcospy` documentation or the repo's README to understand the available functions and the data they return. Key functions you will use:

```python
from arcospy.arcospy import ArcosPy

arcos = ArcosPy(key="WaPo")

# State-level population and pill totals
state_df = arcos.summarized_county_annual(state="AL")

# Buyer-level (county) annual summaries per state
county_df = arcos.buyer_details(county="Mingo", state="WV")

# Pharmacy-level summaries
pharmacy_df = arcos.pharmacy_summary(state="WV")
```

Read the library source to confirm function names and signatures before using them — PyPI version and GitHub version may differ slightly.

### What this script must do:

1. **Import arcospy and initialize the client with the WaPo API key:**
   ```python
   from arcospy.arcospy import ArcosPy
   from opioid_track import config

   arcos = ArcosPy(key=config.ARCOS_API_KEY)
   ```

2. **Start with state-level summaries** (low API volume). Use arcospy to get total pills and population per state. Compute pills-per-capita.

3. **Fetch county-level annual summaries for all 50 states + DC.** Loop through all states. For each state:
   - Call the appropriate arcospy function to get county-level annual opioid distribution data
   - Rate limit at `config.ARCOS_DELAY_SECONDS` between calls

4. **Cache every raw API response** as individual JSON files in `config.ARCOS_RAW_CACHE_DIR` (e.g., `arcos_county_AL.json`). Before making an API call, check if the cached file exists — load from cache if so. This prevents re-fetching during retries.

5. **Handle API reliability issues:**
   - Implement retry with exponential backoff (3 retries, starting at 2 seconds)
   - If a state fails after all retries, log the error and continue
   - At the end, print a summary of which states succeeded and which failed

6. **Process the county-level data:**
   - Standardize FIPS codes to 5-digit format
   - Compute pills per capita using the population data returned by arcospy
   - Convert pandas DataFrames to plain Python dicts for JSON serialization

7. **Save output** to `config.ARCOS_OUTPUT`:
   ```json
   {
     "metadata": {
       "source": "DEA ARCOS via Washington Post API (arcospy / marc-rauckhorst/arcos-py)",
       "drugs_covered": ["oxycodone", "hydrocodone"],
       "years_covered": [2006, 2007, ..., 2014],
       "generated_at": "ISO-8601",
       "states_fetched": 51,
       "states_failed": 0
     },
     "by_state": [
       {
         "state": "AL",
         "total_pills": 1234567890,
         "population": 4800000,
         "pills_per_capita": 257.2,
         "by_year": [ { "year": 2006, "pills": 100000000 } ]
       }
     ],
     "by_county": [
       {
         "fips_code": "01001",
         "state": "AL",
         "county": "Autauga",
         "total_pills": 5000000,
         "pills_per_capita": 91.3,
         "by_year": [ ... ]
       }
     ]
   }
   ```

8. **Add a `main()` function.**

---

## Step 6: Build `opioid_track/core/signal_detector.py`

> **Reproducibility: uses `ChapatiDB/faerslib`**
>
> Instead of implementing PRR, ROR, IC, and EBGM from scratch (which requires careful handling of edge cases like zero cells, continuity corrections, and confidence interval methods), use `faerslib` — a Python library specifically designed for FAERS pharmacovigilance signal detection with peer-reviewed algorithm implementations. The library handles drug name standardization, 2×2 table construction from the OpenFDA API, and all four statistical methods.

### Setup:

```bash
pip install faerslib
```

**Before writing the module**, read the `ChapatiDB/faerslib` README and source code to understand:
- How to initialize the client and connect to OpenFDA
- How it constructs the 2×2 contingency table from FAERS
- How to call the signal detection methods (`prr`, `ror`, `mgps`)
- What the result objects look like
- Whether drug name standardization happens automatically or requires configuration

### What this module must do:

1. **Import and initialize faerslib:**
   ```python
   from faerslib import FAERS
   from opioid_track import config

   # faerslib connects to OpenFDA internally — read its docs for initialization
   faers = FAERS()
   ```

2. **Wrap faerslib's contingency table builder.** faerslib constructs the 2×2 table:
   ```
                     Target Reaction    Other Reactions
   Target Drug       a                  b
   Other Drugs       c                  d
   ```
   from OpenFDA FAERS. Use faerslib's built-in query functionality rather than constructing raw OpenFDA URLs manually.

3. **Cache FAERS query results** to `config.SIGNAL_CACHE_FILE`. Before making any faerslib API call for a specific drug-reaction pair, check the cache. The cache should be a JSON dict. This prevents re-querying during reruns and speeds up batch processing significantly.

4. **Implement the main detection function** wrapping faerslib's methods:
   ```python
   def detect_signals(
       drug_name: str,
       reactions: list[str] | None = None,
       methods: list[str] | None = None
   ) -> list[dict]:
   ```
   - If `reactions` is None, use `config.OPIOID_SAFETY_TERMS`
   - If `methods` is None, use `config.SIGNAL_METHODS` (["prr", "ror", "mgps"])
   - For each drug-reaction pair, call faerslib's signal detection for each requested method
   - Return a list of result dicts:
     ```json
     {
       "drug_name": "Morphine",
       "reaction": "Respiratory depression",
       "report_count": 1234,
       "prr": { "value": 3.2, "chi2": 45.6, "signal": true },
       "ror": { "value": 3.5, "ci_lower": 2.1, "ci_upper": 5.8, "signal": true },
       "mgps": { "ebgm": 2.8, "eb05": 2.1, "signal": true },
       "consensus_signal": true,
       "methods_flagging": 3,
       "source_library": "ChapatiDB/faerslib"
     }
     ```

5. **Map from RxCUI to drug name for faerslib queries.** faerslib likely takes drug names rather than RxCUIs. Use `opioid_track.core.registry.get_opioid_profile(rxcui)` to get the drug name before calling faerslib.

6. **Implement a batch runner:**
   ```python
   def run_opioid_signal_scan(top_n_drugs: int = 20) -> list[dict]:
   ```
   - Load the Tier 1 registry
   - Use `config.MUST_INCLUDE_OPIOIDS` as the base drug list, plus any additional opioids found in the registry with significant FAERS report counts
   - Run `detect_signals()` for each drug against all `config.OPIOID_SAFETY_TERMS`
   - Save full results to `config.SIGNAL_RESULTS_OUTPUT`
   - Return the results

7. **Handle edge cases:**
   - If faerslib returns a zero-count cell, use its built-in continuity correction (check the docs — faerslib may handle this automatically)
   - If a FAERS query returns 0 results, skip that drug-reaction pair and log it
   - If an API call fails, log and skip

8. **Add a `main()` function** that runs `run_opioid_signal_scan()`.

---

## Step 7: Build `opioid_track/core/geographic_joiner.py`

This module joins the CMS, CDC, and ARCOS data by county FIPS code. *(No repo needed — pure data joining logic.)*

### What this module must do:

1. **Load all three datasets:**
   - `opioid_track/data/opioid_prescribing.json` (CMS data, by_geography section)
   - `opioid_track/data/opioid_mortality.json` (CDC data, by_county or by_state section)
   - `opioid_track/data/opioid_supply_chain.json` (ARCOS data, by_county section)

2. **Build a county-level master table.** Start with the dataset that has the most counties (likely ARCOS or CMS). For each county FIPS code:
   - Left-join CMS prescribing data (matching by FIPS + year)
   - Left-join CDC mortality data (matching by FIPS + year)
   - Left-join ARCOS supply chain data (matching by FIPS + year)

3. **Fetch county population from Census Bureau** for per-capita calculations:
   ```
   GET https://api.census.gov/data/2020/acs/acs5?get=NAME,B01003_001E&for=county:*&in=state:*
   ```
   This returns county name and total population. If the Census API is unavailable, use population data already returned by arcospy (it includes state population), or leave per-capita metrics as null.

4. **Compute derived metrics** for each county that has data from at least 2 of 3 sources:
   - `pills_per_death_ratio`: ARCOS total pills ÷ CDC opioid deaths (for overlapping years)
   - `prescribing_vs_mortality`: CMS prescribing rate alongside CDC death rate (per 100K)
   - `risk_score`: simple composite = normalize each metric to 0–1 range, then average:
     - (normalized prescribing rate + normalized death rate + normalized pills per capita) / 3
   - `risk_tier`: based on risk_score — "Low" (<0.25), "Medium" (0.25–0.5), "High" (0.5–0.75), "Critical" (>0.75)

5. **Handle missing data cleanly:**
   - Not all counties will appear in all datasets (ARCOS only covers oxycodone + hydrocodone; CDC suppresses counts <10)
   - Use null for missing values — do not impute or guess
   - Only compute derived metrics when the required input data exists

6. **Save output** to `config.GEO_PROFILES_OUTPUT`:
   ```json
   {
     "metadata": {
       "generated_at": "ISO-8601",
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
         "cms_data": { "prescribing_rate": 4.2, "year": 2023 },
         "cdc_data": { "opioid_deaths": 12, "death_rate_per_100k": 21.8, "year": 2023 },
         "arcos_data": { "total_pills": 5000000, "pills_per_capita": 91.3, "year_range": "2006-2014" },
         "derived_metrics": {
           "pills_per_death_ratio": 416666.7,
           "risk_score": 0.42
         }
       }
     ]
   }
   ```

7. **Add a `main()` function.**

---

## Step 8: Build Tests

### `opioid_track/tests/test_signal_detector.py`:

1. Test that `faerslib` is importable and the FAERS client initializes without error.
2. Test that `detect_signals()` returns a list with the expected dict structure for at least one drug-reaction pair.
3. Test that `consensus_signal` and `methods_flagging` fields are present in each result.
4. Test that results for `"morphine"` + `"Respiratory depression"` return a result (even if signal is False — just test structure).
5. Test that the cache file is written after a signal scan run.
6. Test that `source_library` field is `"ChapatiDB/faerslib"` in all results.

### `opioid_track/tests/test_geographic_joiner.py`:

1. Test FIPS code normalization (3-digit → 5-digit padding).
2. Test risk score calculation with known inputs.
3. Test that missing data handling produces null, not NaN.
4. Test risk tier assignment boundaries.
5. Test that output JSON loads correctly and `metadata.data_sources_joined` includes "ARCOS via arcospy".

---

## Step 9: Run and Validate

Install all new dependencies before running:

```bash
pip install arcospy faerslib
# AND clone cdc-wonder-api vendor if needed:
git clone https://github.com/alipphardt/cdc-wonder-api.git opioid_track/vendor/cdc-wonder-api
```

Run each script in order (Tier 2 depends on Tier 1 outputs existing):

```bash
# Step 1: CMS prescribing data
python -m opioid_track.ingestion.cms_opioid_fetcher

# Step 2: CDC mortality data (uses alipphardt/cdc-wonder-api)
python -m opioid_track.ingestion.cdc_mortality_fetcher

# Step 3: ARCOS supply chain data (uses arcospy)
python -m opioid_track.ingestion.arcos_fetcher

# Step 4: Signal detection (uses ChapatiDB/faerslib)
python -m opioid_track.core.signal_detector

# Step 5: Geographic joining
python -m opioid_track.core.geographic_joiner

# Step 6: Tests
pytest opioid_track/tests/test_signal_detector.py
pytest opioid_track/tests/test_geographic_joiner.py
```

After completion, verify:
- All 5 new JSON files exist in `opioid_track/data/`
- `faers_signal_results.json` has `source_library == "ChapatiDB/faerslib"` in each result
- `opioid_supply_chain.json` metadata notes arcospy as the data source
- No existing TruPharma files were modified
- No Tier 1 files were modified (unless fixing a bug)
- The existing TruPharma app still runs correctly

---

## Final File Structure After Tier 2

```
opioid_track/
├── ... (all Tier 1 files, untouched)
├── config.py                            ← APPENDED with Tier 2 entries
├── vendor/
│   ├── cdc-wonder-api/                  ← cloned from alipphardt/cdc-wonder-api
│   └── arcos-py/                        ← cloned fallback if arcospy PyPI fails
├── ingestion/
│   ├── ... (Tier 1 fetchers)
│   ├── cms_opioid_fetcher.py            ← NEW
│   ├── cdc_mortality_fetcher.py         ← NEW (uses alipphardt/cdc-wonder-api)
│   └── arcos_fetcher.py                 ← NEW (uses arcospy)
├── core/
│   ├── ... (Tier 1 core)
│   ├── signal_detector.py               ← NEW (uses ChapatiDB/faerslib)
│   └── geographic_joiner.py             ← NEW
├── data/
│   ├── ... (Tier 1 data)
│   ├── raw/arcos/                       ← NEW (arcospy response cache)
│   ├── opioid_prescribing.json          ← NEW
│   ├── opioid_mortality.json            ← NEW
│   ├── opioid_supply_chain.json         ← NEW
│   ├── faers_signal_cache.json          ← NEW
│   └── faers_signal_results.json        ← NEW
│   └── opioid_geographic_profiles.json  ← NEW
└── tests/
    ├── ... (Tier 1 tests)
    ├── test_signal_detector.py          ← NEW
    └── test_geographic_joiner.py        ← NEW
```

---

## Splitting Work Across Multiple Agents Within This Tier

- **Agent 1:** Steps 0–2 (understand project + config), then Step 3 (CMS fetcher)
- **Agent 2:** Step 4 (CDC mortality — clone and use `alipphardt/cdc-wonder-api`) + Step 5 (ARCOS — use `arcospy`)
- **Agent 3:** Step 6 (signal detector — use `ChapatiDB/faerslib`)
- **After all three finish → one agent for:** Steps 7–9 (geographic joiner, tests, validation)
