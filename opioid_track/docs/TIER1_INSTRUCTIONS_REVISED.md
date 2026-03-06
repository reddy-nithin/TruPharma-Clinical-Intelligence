# TIER 1 — Opioid Classification Foundation
# (Revised: reproducibility-first using existing GitHub repos)

## Instructions for Coding Agent

You are adding an **Opioid Intelligence Track** as an isolated add-on to an existing project called TruPharma Clinical Intelligence. The opioid track must be completely self-contained so that if anything breaks in this track, the existing TruPharma project is untouched and continues to work.

> **Reproducibility note:** Two GitHub repositories are used as primary data sources in this tier instead of building equivalent logic from scratch. This means your outputs can always be regenerated from authoritative, versioned, peer-reviewed sources.
>
> | Repo | Used for | How |
> |---|---|---|
> | `ripl-org/historical-ndc` | Pre-classified NDC→opioid lookup (1998–2018) | Download `ndc-opioids.csv` directly from raw GitHub URL |
> | `jbadger3/ml_4_pheno_ooe` | RxCUI→MME mapping JSON | Download `rxcui_mme_mapping.json` directly from raw GitHub URL |

---

## Step 0: Understand the Existing Project

Before writing any code, read and understand the existing project:

1. Read `README.md` at the project root.
2. Read every file inside `src/ingestion/` — understand the fetcher pattern, how APIs are called, error handling, logging, and how output data is stored.
3. Read the main app entry point (likely a Streamlit app) to understand how data flows from ingestion → processing → RAG index → agents → UI.
4. Note these existing data sources already in use: OpenFDA (`/drug/label`, `/drug/event`, `/drug/ndc`), RxNorm API, NDC Directory, DailyMed. The existing pipeline uses `openfda.rxcui` as the primary cross-reference key.
5. **Do not modify any existing files.** Everything you build goes into the `opioid_track/` directory.

---

## Step 1: Create the Opioid Track Directory Structure

Create this exact directory structure at the project root:

```
opioid_track/
├── __init__.py
├── config.py
├── README.md
├── requirements.txt
├── data/
│   └── .gitkeep
├── ingestion/
│   ├── __init__.py
│   ├── rxclass_opioid_fetcher.py
│   ├── ndc_opioid_classifier.py
│   ├── mme_mapper.py
│   └── faers_opioid_filter.py
├── core/
│   ├── __init__.py
│   ├── registry_builder.py
│   └── registry.py
└── tests/
    ├── __init__.py
    └── test_registry.py
```

---

## Step 2: Create `opioid_track/config.py`

This is the central configuration for the entire opioid track. All paths, API endpoints, and constants live here.

```python
# Contents to include:

# Base paths
OPIOID_DATA_DIR = "opioid_track/data"

# Output file paths
RXCLASS_OUTPUT = f"{OPIOID_DATA_DIR}/rxclass_opioid_enumeration.json"
NDC_LOOKUP_OUTPUT = f"{OPIOID_DATA_DIR}/ndc_opioid_lookup.json"
MME_REFERENCE_OUTPUT = f"{OPIOID_DATA_DIR}/mme_reference.json"
FAERS_QUERIES_OUTPUT = f"{OPIOID_DATA_DIR}/faers_opioid_queries.json"
REGISTRY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_registry.json"

# === REPRODUCIBILITY: Raw data from pinned GitHub repos ===
# ripl-org/historical-ndc — Pre-classified NDC opioid lookup table (1998–2018)
# Published: JAMIA 2020 | License: MIT
RIPL_NDC_CSV_URL = "https://raw.githubusercontent.com/ripl-org/historical-ndc/master/ndc-opioids.csv"
RIPL_NDC_CSV_LOCAL = f"{OPIOID_DATA_DIR}/raw/ndc-opioids.csv"

# jbadger3/ml_4_pheno_ooe — RxCUI→MME mapping (peer-reviewed ML phenotyping paper)
# License: MIT
JBADGER_MME_JSON_URL = "https://raw.githubusercontent.com/jbadger3/ml_4_pheno_ooe/main/data/rxcui_mme_mapping.json"
JBADGER_MME_JSON_LOCAL = f"{OPIOID_DATA_DIR}/raw/rxcui_mme_mapping.json"

# API base URLs (all free, no auth required)
RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
RXCLASS_BASE = "https://rxnav.nlm.nih.gov/REST/rxclass"
OPENFDA_BASE = "https://api.fda.gov/drug"
DAILYMED_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

# Rate limiting
RXNAV_DELAY_SECONDS = 0.05    # 20 req/sec max
OPENFDA_DELAY_SECONDS = 0.25  # ~4 req/sec to be safe

# Opioid ATC sub-classes for categorization
ATC_OPIOID_CLASSES = {
    "N02A": "Opioids (parent class)",
    "N02AA": "Natural opium alkaloids",
    "N02AB": "Phenylpiperidine derivatives",
    "N02AC": "Diphenylpropylamine derivatives",
    "N02AD": "Benzomorphan derivatives",
    "N02AE": "Oripavine derivatives",
    "N02AF": "Morphinan derivatives",
    "N02AG": "Opioids + antispasmodics",
    "N02AJ": "Opioids + non-opioid analgesics",
    "N02AX": "Other opioids",
    "N07BC": "Drugs used in opioid dependence",
}

# ATC code to opioid category mapping
ATC_TO_CATEGORY = {
    "N02AA": "natural/semi-synthetic",
    "N02AB": "synthetic",
    "N02AC": "synthetic",
    "N02AD": "synthetic",
    "N02AE": "semi-synthetic",
    "N02AF": "semi-synthetic",
    "N02AG": "combination",
    "N02AJ": "combination",
    "N02AX": "synthetic",
    "N07BC": "treatment/recovery",
}

# MED-RT concept IDs for opioid mechanisms of action
MEDRT_OPIOID_CONCEPTS = {
    "N0000175690": "Opioid Agonist",
    "N0000175691": "Full Opioid Agonist",
    "N0000175692": "Opioid Partial Agonist",
    "N0000175688": "Opioid Antagonist",
    "N0000175693": "Opioid Agonist-Antagonist",
}

# FDA Established Pharmacologic Classes
FDA_EPC_OPIOID = [
    "Opioid Agonist [EPC]",
    "Opioid Antagonist [EPC]",
    "Opioid Partial Agonist [EPC]",
]

# DEA schedules to check
DEA_SCHEDULES = ["CII", "CIII", "CIV", "CV"]

# CDC MME conversion factors (per mg oral, unless noted)
# These are the fallback if jbadger3/ml_4_pheno_ooe JSON download fails
CDC_MME_FACTORS = {
    "codeine": 0.15,
    "tramadol": 0.2,
    "tapentadol": 0.4,
    "meperidine": 0.4,
    "morphine": 1.0,
    "oxycodone": 1.5,
    "hydrocodone": 1.0,
    "hydromorphone": 5.0,
    "oxymorphone": 3.0,
    "fentanyl": 2.4,          # transdermal mcg/hr to MME
    "buprenorphine": 12.6,
    "levorphanol": 11.0,
    "pentazocine": 0.37,
    "butorphanol": 7.0,
}

# Methadone has dose-dependent conversion
METHADONE_MME_TIERS = [
    (20, 4.7),    # ≤20 mg/day → factor 4.7
    (40, 8.0),    # 21-40 mg/day → factor 8.0
    (60, 10.0),   # 41-60 mg/day → factor 10.0
    (80, 12.0),   # 61-80 mg/day → factor 12.0
]

# Key MedDRA preferred terms for opioid safety monitoring
OPIOID_SAFETY_TERMS = [
    "Respiratory depression",
    "Respiratory failure",
    "Respiratory arrest",
    "Drug dependence",
    "Drug abuse",
    "Substance abuse",
    "Overdose",
    "Intentional overdose",
    "Accidental overdose",
    "Drug toxicity",
    "Death",
    "Completed suicide",
    "Neonatal abstinence syndrome",
    "Neonatal opioid withdrawal syndrome",
    "Withdrawal syndrome",
    "Drug withdrawal syndrome",
    "Somnolence",
    "Coma",
    "Loss of consciousness",
    "Constipation",
    "Serotonin syndrome",
]

# Minimum known opioids for validation
MUST_INCLUDE_OPIOIDS = [
    "morphine", "codeine", "oxycodone", "hydrocodone",
    "fentanyl", "methadone", "buprenorphine", "tramadol",
    "tapentadol", "meperidine", "hydromorphone", "oxymorphone",
    "naloxone", "naltrexone",
]
```

---

## Step 3: Create `opioid_track/requirements.txt`

```
requests>=2.28.0
```

No heavy dependencies for Tier 1. Just the standard library plus `requests` for API calls and downloading the raw GitHub data files. The existing TruPharma project likely already has `requests` installed.

---

## Step 4: Build `opioid_track/ingestion/rxclass_opioid_fetcher.py`

This script queries the RxClass API across multiple classification hierarchies to enumerate every opioid drug by RxCUI. *(No repo available for this step — built directly against the NLM API.)*

### What this script must do:

1. **Query RxClass API for ATC opioid classes.** For each ATC code in `config.ATC_OPIOID_CLASSES`, call:
   ```
   GET {RXCLASS_BASE}/classMembers.json?classId={atc_code}&relaSource=ATC
   ```
   Parse the response: `drugMemberGroup.drugMember[]` contains `minConcept.rxcui` and `minConcept.name`.

2. **Query RxClass API for MED-RT mechanisms.** For each concept ID in `config.MEDRT_OPIOID_CONCEPTS`, call:
   ```
   GET {RXCLASS_BASE}/classMembers.json?classId={concept_id}&relaSource=MEDRT&rela=has_MoA
   ```

3. **Query RxClass API for FDA EPC classes.** For each EPC in `config.FDA_EPC_OPIOID`, call:
   ```
   GET {RXCLASS_BASE}/classMembers.json?classId={epc}&relaSource=FDASPL&rela=has_EPC
   ```

4. **Deduplicate results by RxCUI.** The same drug will appear across multiple queries. Merge all classification metadata into a single record per RxCUI.

5. **For each unique RxCUI, resolve to active ingredients.** Call:
   ```
   GET {RXNAV_BASE}/rxcui/{rxcui}/allrelated.json
   ```
   From the response, extract entries where `tty` (term type) is `"IN"` (Ingredient) or `"MIN"` (Multiple Ingredients). These are the active ingredient RxCUIs and names.

6. **Tag each drug with its opioid category** using `config.ATC_TO_CATEGORY` based on its ATC code. If multiple ATC codes, prefer the most specific one.

7. **Implement polite rate limiting.** Sleep `config.RXNAV_DELAY_SECONDS` between every API call.

8. **Handle errors gracefully.** If an API call fails (timeout, 5xx, empty response), log a warning and continue. Do not crash the entire script for one failed call. Implement retry with exponential backoff (max 3 retries).

9. **Save output** to `config.RXCLASS_OUTPUT` as JSON with this structure:
   ```json
   [
     {
       "rxcui": "7052",
       "drug_name": "Morphine",
       "tty": "IN",
       "atc_codes": ["N02AA01"],
       "atc_descriptions": ["Natural opium alkaloids"],
       "med_rt_classes": ["Full Opioid Agonist"],
       "epc_classes": ["Opioid Agonist [EPC]"],
       "schedule": "CII",
       "opioid_category": "natural/semi-synthetic",
       "ingredients": [
         {
           "rxcui": "7052",
           "name": "Morphine",
           "tty": "IN"
         }
       ]
     }
   ]
   ```

10. **Validate output.** After saving, verify that every drug name in `config.MUST_INCLUDE_OPIOIDS` has at least one matching entry. Print a warning for any missing drugs.

11. **Add a `main()` function** that runs the full enumeration and can be called via `python -m opioid_track.ingestion.rxclass_opioid_fetcher` or imported.

---

## Step 5: Build `opioid_track/ingestion/ndc_opioid_classifier.py`

> **Reproducibility: uses `ripl-org/historical-ndc`**
>
> Instead of building a classifier from scratch, this script downloads the pre-classified `ndc-opioids.csv` file from the `ripl-org/historical-ndc` repository — a peer-reviewed dataset (JAMIA 2020) covering 1998–2018 with opioid/recovery-drug labels already applied by domain experts. This is the primary classification source. OpenFDA is used only to fill post-2018 gaps.

### What this script must do:

1. **Download `ndc-opioids.csv` from `ripl-org/historical-ndc` as the primary source.**
   ```python
   import requests, os
   from opioid_track import config

   os.makedirs(f"{config.OPIOID_DATA_DIR}/raw", exist_ok=True)

   if not os.path.exists(config.RIPL_NDC_CSV_LOCAL):
       response = requests.get(config.RIPL_NDC_CSV_URL, timeout=30)
       response.raise_for_status()
       with open(config.RIPL_NDC_CSV_LOCAL, "wb") as f:
           f.write(response.content)
       print(f"Downloaded ndc-opioids.csv from ripl-org/historical-ndc")
   else:
       print(f"Using cached ndc-opioids.csv from {config.RIPL_NDC_CSV_LOCAL}")
   ```
   If the network is unavailable and no local file exists, raise a clear `FileNotFoundError` with a message explaining where to manually download the file from.

2. **Inspect the CSV structure before parsing.** Print the first few rows and column names so the agent can see the actual schema, since column names in the repository may differ from what is expected. Then parse accordingly.

3. **Parse the CSV into a lookup dict.** The file classifies NDC codes as opioid or recovery drugs based on their active ingredients. Read all rows, keying by NDC.

4. **Implement NDC normalization** so that lookups work regardless of input format. NDC codes come in multiple formats (4-4-2, 5-3-2, 5-4-1, 5-4-2). Normalize all to 11-digit zero-padded format:
   - Split by hyphen into segments
   - Pad: first segment to 5 digits, second to 4 digits, third to 2 digits
   - Concatenate without hyphens → 11-digit string
   - Example: `0069-0770-20` → `00069077020`
   - Also store the hyphenated 5-4-2 format: `00069-0770-20`
   Apply this normalization both when loading the CSV and when performing lookups.

5. **Supplement with current OpenFDA NDC data** for products not in the historical file (post-2018 and any gaps). Query:
   ```
   GET {OPENFDA_BASE}/ndc.json?search=pharm_class:"opioid"&limit=100&skip={offset}
   ```
   Paginate through all results. For each result, extract `product_ndc`, `brand_name`, `generic_name`, `openfda.rxcui`, and `openfda.pharm_class_epc`. Classify as opioid if any EPC contains "Opioid Agonist" or "Opioid Partial Agonist"; as recovery if it contains "Opioid Antagonist".

6. **Merge historical + current data.** Deduplicate by normalized NDC. The `ripl-org` historical data takes priority over OpenFDA for overlapping NDCs (it is the more carefully reviewed source). Flag each entry with its source: `"ripl-org-historical"` or `"openfda-current"`.

7. **Save output** to `config.NDC_LOOKUP_OUTPUT` as JSON:
   ```json
   {
     "00069077020": {
       "ndc_formatted": "00069-0770-20",
       "rxcui": "261106",
       "drug_name": "Oxycodone Hydrochloride",
       "is_opioid": true,
       "is_recovery_drug": false,
       "source": "ripl-org-historical"
     }
   }
   ```

8. **Print summary stats** at the end: total NDCs classified, number opioid, number recovery, number from `ripl-org` historical vs. OpenFDA current.

9. **Add a `main()` function** that runs the full pipeline.

---

## Step 6: Build `opioid_track/ingestion/mme_mapper.py`

> **Reproducibility: uses `jbadger3/ml_4_pheno_ooe`**
>
> Instead of building an MME mapping table from scratch, this script downloads the `rxcui_mme_mapping.json` file from the `jbadger3/ml_4_pheno_ooe` repository — a peer-reviewed ML phenotyping paper with a curated RxCUI-level MME map. This is the primary RxCUI-level source. The CDC guideline factors in `config.CDC_MME_FACTORS` serve as the named-ingredient fallback and validation reference.

### What this script must do:

1. **Download `rxcui_mme_mapping.json` from `jbadger3/ml_4_pheno_ooe` as the primary RxCUI-level source.**
   ```python
   import requests, os, json
   from opioid_track import config

   os.makedirs(f"{config.OPIOID_DATA_DIR}/raw", exist_ok=True)

   if not os.path.exists(config.JBADGER_MME_JSON_LOCAL):
       response = requests.get(config.JBADGER_MME_JSON_URL, timeout=30)
       response.raise_for_status()
       with open(config.JBADGER_MME_JSON_LOCAL, "w") as f:
           json.dump(response.json(), f)
       print(f"Downloaded rxcui_mme_mapping.json from jbadger3/ml_4_pheno_ooe")
   else:
       print(f"Using cached rxcui_mme_mapping.json from {config.JBADGER_MME_JSON_LOCAL}")
   ```
   If download fails, log a warning and continue using only `config.CDC_MME_FACTORS` as the fallback.

2. **Inspect the JSON structure** after downloading. Print the first few keys and values to understand the schema. The mapping may be `{rxcui: mme_factor}` or `{rxcui: {factor: ..., drug_name: ...}}`. Adapt the rest of the script to match the actual schema.

3. **Cross-validate against `config.CDC_MME_FACTORS`.** For each named ingredient in CDC_MME_FACTORS, find its RxCUI via the RxNorm API:
   ```
   GET {RXNAV_BASE}/rxcui.json?name={ingredient_name}&search=1
   ```
   Then check whether the `jbadger3` JSON has a matching entry for that RxCUI and whether the factor is within a reasonable range (±20% of the CDC factor). Log any discrepancies. Do not overwrite — CDC guideline values always win for the named-ingredient lookup.

4. **Create the MME reference data structure:**
   ```json
   {
     "cdc_factors": {
       "codeine": { "mme_factor": 0.15, "source": "CDC Clinical Practice Guideline 2022", "notes": "per mg oral" },
       "morphine": { "mme_factor": 1.0, "source": "CDC Clinical Practice Guideline 2022", "notes": "reference standard" }
     },
     "rxcui_mme_map": {
       "2670": { "mme_factor": 1.0, "drug_name": "Morphine", "source": "jbadger3/ml_4_pheno_ooe" }
     },
     "methadone_tiers": [
       { "max_daily_dose_mg": 20, "mme_factor": 4.7 },
       { "max_daily_dose_mg": 40, "mme_factor": 8.0 },
       { "max_daily_dose_mg": 60, "mme_factor": 10.0 },
       { "max_daily_dose_mg": 80, "mme_factor": 12.0 }
     ],
     "risk_thresholds": {
       "increased_risk_mme": 50,
       "high_risk_mme": 90
     },
     "metadata": {
       "primary_rxcui_source": "jbadger3/ml_4_pheno_ooe",
       "named_ingredient_source": "CDC Clinical Practice Guideline 2022",
       "generated_at": "ISO-8601"
     }
   }
   ```

5. **Implement a `calculate_daily_mme(ingredient_name, daily_dose_mg)` function:**
   - Lookup the ingredient (case-insensitive) in `cdc_factors` first
   - If methadone, use the tiered conversion based on daily dose
   - Return: `{ "daily_mme": float, "risk_level": "normal|increased|high", "mme_factor_used": float }`

6. **Save output** to `config.MME_REFERENCE_OUTPUT`.

7. **Add a `main()` function.**

---

## Step 7: Build `opioid_track/ingestion/faers_opioid_filter.py`

This script creates pre-built FAERS query templates and fetches baseline opioid adverse event statistics. *(Built directly against the OpenFDA API — no repo substitute needed here.)*

### What this script must do:

1. **Define FAERS query templates** as a reusable dictionary. Each template is a parameterized URL pattern for the OpenFDA FAERS API:

   - `all_opioid_reactions`: Count all adverse reactions reported for opioid drugs
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"&count=patient.reaction.reactionmeddrapt.exact&limit=100
     ```
   - `opioid_by_drug`: Events for a specific opioid by RxCUI (parameterized: `{rxcui}`)
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.rxcui:"{rxcui}"&count=patient.reaction.reactionmeddrapt.exact&limit=100
     ```
   - `opioid_deaths`: Opioid-associated death reports
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"+AND+seriousnessdeath:1&count=patient.reaction.reactionmeddrapt.exact&limit=50
     ```
   - `opioid_by_sex`: Demographic breakdown by sex
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"&count=patient.patientsex
     ```
   - `opioid_by_age`: Age distribution
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"&count=patient.patientonsetage
     ```
   - `opioid_by_year`: Reporting trend over time
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"&count=receivedate
     ```
   - `specific_reaction`: Events for a specific opioid + specific reaction (parameterized: `{rxcui}`, `{reaction}`)
     ```
     {OPENFDA_BASE}/event.json?search=patient.drug.openfda.rxcui:"{rxcui}"+AND+patient.reaction.reactionmeddrapt:"{reaction}"
     ```

2. **Execute the non-parameterized queries** to build a baseline snapshot:
   - Fetch top 100 opioid adverse reactions
   - Fetch opioid death-associated reactions
   - Fetch sex distribution
   - Fetch age distribution
   - Fetch yearly reporting trends

3. **Rate limit** all API calls at `config.OPENFDA_DELAY_SECONDS`.

4. **Save output** to `config.FAERS_QUERIES_OUTPUT`:
   ```json
   {
     "query_templates": { ... },
     "baseline_snapshot": {
       "fetched_at": "ISO-8601",
       "top_reactions": [ { "term": "...", "count": 1234 } ],
       "death_reactions": [ ... ],
       "sex_distribution": [ ... ],
       "age_distribution": [ ... ],
       "yearly_trend": [ ... ]
     }
   }
   ```

5. **Add a `main()` function.**

---

## Step 8: Build `opioid_track/core/registry_builder.py`

This is the assembly step. It merges all ingestion outputs into a single canonical opioid registry.

### What this script must do:

1. **Load all four ingestion outputs:**
   - `rxclass_opioid_enumeration.json` (from Step 4)
   - `ndc_opioid_lookup.json` (from Step 5 — built on `ripl-org/historical-ndc`)
   - `mme_reference.json` (from Step 6 — built on `jbadger3/ml_4_pheno_ooe`)
   - `faers_opioid_queries.json` (from Step 7)

2. **For each opioid RxCUI from the rxclass enumeration:**

   a. Find all associated NDC codes by checking the NDC lookup for matching RxCUI. Also call:
      ```
      GET {RXNAV_BASE}/rxcui/{rxcui}/ndcs.json
      ```

   b. Retrieve the SPL Set ID from OpenFDA labels:
      ```
      GET {OPENFDA_BASE}/label.json?search=openfda.rxcui:"{rxcui}"&limit=1
      ```
      Extract `openfda.spl_set_id` and `openfda.unii` from the response.

   c. Attach the MME conversion factor. **Lookup order:** first check `mme_reference.rxcui_mme_map` using the RxCUI (from `jbadger3`); if not found, fall back to `mme_reference.cdc_factors` using the ingredient name (from CDC guideline).

   d. Build the `pharmacologic_classes` object from the rxclass data (EPC, MoA, PE, CS).

   e. For combination products (e.g., oxycodone/acetaminophen), mark which ingredient is the opioid component (`is_opioid_component: true`).

3. **Assemble the final registry** with this structure:
   ```json
   {
     "metadata": {
       "generated_at": "ISO-8601",
       "version": "1.0.0",
       "tier": 1,
       "total_opioid_rxcuis": 0,
       "total_opioid_ndcs": 0,
       "data_sources": {
         "ndc_classification": "ripl-org/historical-ndc + OpenFDA",
         "mme_mapping": "jbadger3/ml_4_pheno_ooe + CDC Clinical Practice Guideline 2022",
         "drug_enumeration": "NLM RxClass API (ATC, MED-RT, FDA EPC hierarchies)"
       },
       "description": "Opioid Track registry — isolated add-on for TruPharma"
     },
     "opioid_drugs": [ ... ],
     "mme_reference": { ... },
     "ndc_lookup": { ... },
     "faers_baseline": { ... }
   }
   ```
   Each entry in `opioid_drugs` has: `rxcui`, `drug_name`, `drug_class`, `schedule`, `atc_codes`, `opioid_category`, `active_ingredients[]`, `ndc_codes[]`, `spl_set_ids[]`, `mme_conversion_factor`, `mme_source` ("rxcui_map" or "cdc_named"), `pharmacologic_classes{}`.

4. **Validate the registry:**
   - Every entry in `config.MUST_INCLUDE_OPIOIDS` must be present
   - No duplicate RxCUIs
   - At least 200 unique opioid RxCUIs (products + ingredients)
   - At least 2,000 NDC codes in the lookup
   - MME factors present for all major ingredients (at least 14)
   - At least 80% of NDC entries sourced from `ripl-org-historical` (validates the repo download worked)
   - Print a validation summary

5. **Save** to `config.REGISTRY_OUTPUT`.

6. **Add a `main()` function.**

---

## Step 9: Build `opioid_track/core/registry.py`

This is the runtime module that loads the registry and exposes helper functions for all downstream code (Tiers 2 and 3 will import from here).

### What this module must do:

1. **Load `opioid_registry.json` once** using a singleton/module-level pattern. Lazy-load on first access.

2. **Expose these functions (all with type hints):**
   ```python
   def is_opioid(rxcui: str) -> bool
   def is_opioid_by_ndc(ndc: str) -> bool
   def get_opioid_profile(rxcui: str) -> dict | None
   def get_mme_factor(ingredient_name: str) -> float | None
   def calculate_daily_mme(ingredient_name: str, daily_dose_mg: float) -> dict
   def list_all_opioid_rxcuis() -> list[str]
   def list_all_opioid_ndcs() -> list[str]
   def get_opioids_by_category(category: str) -> list[dict]
   def get_opioids_by_schedule(schedule: str) -> list[dict]
   def get_drugs_containing_ingredient(ingredient_rxcui: str) -> list[dict]
   def get_faers_baseline() -> dict
   def registry_version() -> str
   def registry_stats() -> dict
   ```

3. **NDC normalization built in.** The `is_opioid_by_ndc()` function should normalize the input NDC before lookup, using the same normalization logic as `ndc_opioid_classifier.py`.

4. **Include a `refresh()` function** that clears the cached data and forces a reload from disk.

---

## Step 10: Build `opioid_track/tests/test_registry.py`

### What this test file must do:

1. **Test that the registry loads** without errors.
2. **Test `is_opioid()`:** morphine → True, ibuprofen → False.
3. **Test `get_opioid_profile()`:** returns a dict for morphine with expected fields.
4. **Test `get_mme_factor()`:** morphine → 1.0, codeine → 0.15.
5. **Test `calculate_daily_mme()`:** oxycodone 30mg → 45 MME (30 × 1.5), risk_level = "normal". oxycodone 60mg → 90 MME, risk_level = "high".
6. **Test `get_opioids_by_category("synthetic")`:** should include fentanyl, methadone, tramadol.
7. **Test `list_all_opioid_rxcuis()`:** returns a list with length > 200.
8. **Test NDC normalization** in `is_opioid_by_ndc()`.
9. **Test that `ripl-org/historical-ndc` data is present:** at least one NDC entry has `source == "ripl-org-historical"`.
10. **Test that `jbadger3/ml_4_pheno_ooe` data is present:** at least one RxCUI in `mme_reference.rxcui_mme_map` has `source == "jbadger3/ml_4_pheno_ooe"`.

Use `pytest` or `unittest`.

---

## Step 11: Create `opioid_track/README.md`

Write a README that explains:
- What the opioid track is (isolated add-on to TruPharma)
- **The two GitHub repos used and why** (reproducibility, peer-reviewed sources)
- How to run the ingestion pipeline (run each ingestion script, then the registry builder)
- How to use the registry module in other code
- Data sources used and their licenses (all public domain / free / MIT)
- Directory structure explanation
- How to reproduce from scratch if the raw data files are deleted (just rerun the ingestion scripts — they re-download from GitHub)

---

## Step 12: Run and Validate

1. Run each ingestion script in order:
   ```bash
   python -m opioid_track.ingestion.rxclass_opioid_fetcher
   python -m opioid_track.ingestion.ndc_opioid_classifier   # downloads ripl-org/historical-ndc
   python -m opioid_track.ingestion.mme_mapper               # downloads jbadger3/ml_4_pheno_ooe
   python -m opioid_track.ingestion.faers_opioid_filter
   ```

2. Run the registry builder:
   ```bash
   python -m opioid_track.core.registry_builder
   ```

3. Run tests:
   ```bash
   pytest opioid_track/tests/
   ```

4. Verify that **no existing TruPharma files were modified**. Run the existing TruPharma app and confirm it still works exactly as before.

5. Verify the raw cache files exist:
   ```
   opioid_track/data/raw/ndc-opioids.csv         ← from ripl-org/historical-ndc
   opioid_track/data/raw/rxcui_mme_mapping.json  ← from jbadger3/ml_4_pheno_ooe
   ```

---

## Final File Structure After Tier 1

```
TruPharma-Clinical-Intelligence/       ← EXISTING (untouched)
├── src/                                ← DO NOT MODIFY
│   ├── ingestion/                      ← DO NOT MODIFY
│   └── ...                             ← DO NOT MODIFY
├── opioid_track/                       ← ALL NEW CODE GOES HERE
│   ├── __init__.py
│   ├── config.py
│   ├── README.md
│   ├── requirements.txt
│   ├── data/
│   │   ├── raw/
│   │   │   ├── ndc-opioids.csv              ← downloaded from ripl-org/historical-ndc
│   │   │   └── rxcui_mme_mapping.json       ← downloaded from jbadger3/ml_4_pheno_ooe
│   │   ├── rxclass_opioid_enumeration.json
│   │   ├── ndc_opioid_lookup.json
│   │   ├── mme_reference.json
│   │   ├── faers_opioid_queries.json
│   │   └── opioid_registry.json             ← THE canonical output
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── rxclass_opioid_fetcher.py
│   │   ├── ndc_opioid_classifier.py         ← uses ripl-org/historical-ndc
│   │   ├── mme_mapper.py                    ← uses jbadger3/ml_4_pheno_ooe
│   │   └── faers_opioid_filter.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── registry_builder.py
│   │   └── registry.py
│   └── tests/
│       ├── __init__.py
│       └── test_registry.py
└── ...
```

---

## Splitting Work Across Multiple Agents Within This Tier

- **Agent 1:** Steps 0–3 (setup + config), then Step 4 (rxclass fetcher)
- **Agent 2:** Step 5 (NDC classifier — downloads `ripl-org/historical-ndc`) + Step 6 (MME mapper — downloads `jbadger3/ml_4_pheno_ooe`)
- **Agent 3:** Step 7 (FAERS filter)
- **After all three finish → one agent for:** Steps 8–12 (registry builder, registry module, tests, validation)
