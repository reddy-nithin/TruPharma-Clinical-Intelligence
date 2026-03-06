# TIER 3 — Deep Pharmacology, NLP, and Dashboards
# (Revised: reproducibility-first using existing GitHub repos)

## Instructions for Coding Agent

You are completing the final tier of the **Opioid Intelligence Track**, an isolated add-on to the TruPharma Clinical Intelligence project. Tiers 1 and 2 are complete. The opioid registry, external datasets (CMS, CDC, ARCOS), and signal detection results all exist in `opioid_track/data/`.

**IMPORTANT:** Do not modify any existing TruPharma files outside of `opioid_track/`. Do not modify Tier 1 or Tier 2 files unless fixing a bug. All new code goes into `opioid_track/`.

> **Reproducibility note:** Two GitHub repositories replace significant from-scratch work in this tier.
>
> | Repo | Used for | How |
> |---|---|---|
> | `CDCgov/Opioid_Involvement_NLP` | NLP extraction from DailyMed labels and FAERS narratives | Clone as vendor dependency |
> | `plotly/dash-opioid-epidemic-demo` | Dashboard scaffold: choropleth, layout, and chart patterns | Clone and adapt into Streamlit — port the chart logic |
>
> Additionally, `opioiddatalab/overdosedata` (a Streamlit + Python 3.10 overdose visualization tool using the same stack as TruPharma) should be read as a reference implementation for dashboard design patterns before building the pages.

---

## Step 0: Understand What Exists

Before writing any code:

1. Read `opioid_track/config.py` — understand all config entries from Tiers 1 and 2.
2. Read `opioid_track/core/registry.py` — you will import from this frequently.
3. Open and inspect every JSON file in `opioid_track/data/` to understand the available data:
   - `opioid_registry.json` — drug classifications (Tier 1)
   - `mme_reference.json` — dosage equivalents (Tier 1)
   - `faers_opioid_queries.json` — FAERS baseline stats (Tier 1)
   - `opioid_prescribing.json` — CMS data (Tier 2)
   - `opioid_mortality.json` — CDC data (Tier 2)
   - `opioid_supply_chain.json` — ARCOS data (Tier 2)
   - `faers_signal_results.json` — pharmacovigilance signals (Tier 2)
   - `opioid_geographic_profiles.json` — joined county data (Tier 2)
4. Read `opioid_track/core/signal_detector.py` to understand the signal detection interface.
5. Read the existing TruPharma `src/` directory to understand the parent project's RAG pipeline, agents, and Streamlit UI. Note the architecture but do not modify those files.
6. **Read the reference repos before coding:**
   - Skim `CDCgov/Opioid_Involvement_NLP` README, the main NLP script, and any example outputs to understand its annotation model and input format
   - Skim `plotly/dash-opioid-epidemic-demo` `app.py` to understand its choropleth data loading and layout patterns
   - Skim `opioiddatalab/overdosedata` to understand how a similar team structured a Streamlit opioid dashboard

---

## Step 1: Extend the Directory Structure

Add these new directories and files to `opioid_track/`:

```
opioid_track/
├── ... (all Tier 1 + Tier 2 files, untouched)
├── vendor/
│   ├── ... (Tier 2 vendor repos)
│   ├── Opioid_Involvement_NLP/          ← NEW: cloned from CDCgov
│   └── dash-opioid-epidemic-demo/       ← NEW: cloned from plotly
├── ingestion/
│   ├── ... (Tier 1 + 2 fetchers)
│   ├── pharmacology_fetcher.py          ← NEW
│   └── toxicology_fetcher.py            ← NEW
├── core/
│   ├── ... (Tier 1 + 2 core)
│   ├── nlp_miner.py                     ← NEW (adapts CDCgov/Opioid_Involvement_NLP)
│   └── knowledge_indexer.py             ← NEW
├── dashboard/
│   ├── __init__.py                      ← NEW
│   ├── opioid_app.py                    ← NEW (standalone Streamlit app)
│   ├── pages/
│   │   ├── __init__.py                  ← NEW
│   │   ├── drug_explorer.py             ← NEW
│   │   ├── landscape.py                 ← NEW
│   │   ├── geography.py                 ← NEW (adapts plotly/dash-opioid-epidemic-demo)
│   │   └── signals.py                   ← NEW
│   └── components/
│       ├── __init__.py                  ← NEW
│       └── charts.py                    ← NEW
├── agents/
│   ├── __init__.py                      ← NEW
│   └── opioid_watchdog.py               ← NEW
├── data/
│   ├── ... (Tier 1 + 2 data)
│   ├── opioid_pharmacology.json         ← NEW (output)
│   └── opioid_nlp_insights.json         ← NEW (output)
└── tests/
    ├── ... (Tier 1 + 2 tests)
    └── test_pharmacology.py             ← NEW
```

---

## Step 2: Add Tier 3 Config Entries

Open `opioid_track/config.py` and **append** these entries:

```python
# === TIER 3 ADDITIONS ===

# Pharmacology data
PHARMACOLOGY_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_pharmacology.json"
CHEMBL_DELAY_SECONDS = 0.1
CHEMBL_OPIOID_TARGETS = {
    "mu":    {"chembl_id": "CHEMBL233",     "gene": "OPRM1", "uniprot": "P35372", "gtopdb_id": 319},
    "kappa": {"chembl_id": "CHEMBL237",     "gene": "OPRK1", "uniprot": "P41145", "gtopdb_id": 320},
    "delta": {"chembl_id": "CHEMBL236",     "gene": "OPRD1", "uniprot": "P41143", "gtopdb_id": 321},
    "nop":   {"chembl_id": "CHEMBL2014868", "gene": "OPRL1", "uniprot": "P41146", "gtopdb_id": 322},
}
GTOPDB_API_BASE = "https://www.guidetopharmacology.org/services"
PUBCHEM_API_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

# Toxicology
TOXICOLOGY_SPECIES_PRIORITY = ["human", "rat", "mouse", "rabbit", "dog"]
TOXICOLOGY_ROUTE_PRIORITY = ["oral", "intravenous", "subcutaneous", "intraperitoneal", "inhalation"]

# Interspecies scaling constants (body surface area method)
KM_SCALING = {
    "mouse": 3.0,
    "rat": 6.2,
    "rabbit": 12.0,
    "dog": 20.0,
    "human": 37.0,
}

# NLP — CDCgov/Opioid_Involvement_NLP vendor path
NLP_INSIGHTS_OUTPUT = f"{OPIOID_DATA_DIR}/opioid_nlp_insights.json"
CDC_NLP_VENDOR_DIR = "opioid_track/vendor/Opioid_Involvement_NLP"
SPL_OPIOID_SECTIONS = {
    "boxed_warning":       "34066-1",
    "indications":         "34067-9",
    "dosage_admin":        "34068-7",
    "warnings_precautions":"43685-7",
    "adverse_reactions":   "34084-4",
    "drug_interactions":   "34073-7",
    "abuse_dependence":    "42227-9",
    "overdosage":          "34088-5",
    "clinical_pharmacology":"34090-1",
}

# Dashboard — reference repos
DASH_DEMO_VENDOR_DIR = "opioid_track/vendor/dash-opioid-epidemic-demo"
DASHBOARD_TITLE = "TruPharma Opioid Intelligence"
DASHBOARD_PORT = 8502  # Different port from main TruPharma app

# Knowledge chunks for RAG
KNOWLEDGE_CHUNKS_DIR = f"{OPIOID_DATA_DIR}/knowledge_chunks"
CHUNK_SIZE_TOKENS = 600
CHUNK_OVERLAP_TOKENS = 100
```

---

## Step 3: Clone the Reference Repositories

Run these commands before writing any code for this tier:

```bash
mkdir -p opioid_track/vendor

# NLP: CDCgov/Opioid_Involvement_NLP
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git \
    opioid_track/vendor/Opioid_Involvement_NLP

# Dashboard scaffold: plotly/dash-opioid-epidemic-demo
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git \
    opioid_track/vendor/dash-opioid-epidemic-demo

# Reference implementation: opioiddatalab/overdosedata (read-only, for design patterns)
git clone https://github.com/opioiddatalab/overdosedata.git \
    opioid_track/vendor/overdosedata
```

After cloning, read the key files in each repo before proceeding:
- `Opioid_Involvement_NLP/`: look for the main annotation script, any pretrained model files, and the input/output format documentation
- `dash-opioid-epidemic-demo/app.py`: understand how it loads the county choropleth data, what data format it expects, and how it builds the Plotly figure
- `overdosedata/`: find the Streamlit app entry point and read the data loading and page layout patterns

---

## Step 4: Build `opioid_track/ingestion/pharmacology_fetcher.py`

This script fetches molecular-level receptor binding data that explains WHY substances are opioids. *(Built directly against ChEMBL, GtoPdb, and PubChem APIs — no repo substitute needed.)*

### What this script must do:

1. **Install the ChEMBL Python client:**
   ```bash
   pip install chembl_webresource_client
   ```

2. **Get the list of opioid ingredients to look up.** Load the Tier 1 registry and extract all unique ingredient names and RxCUIs where `is_opioid_component` is true. This should give you 15–30 key opioid ingredients.

3. **For each opioid receptor target** (mu, kappa, delta, NOP from `config.CHEMBL_OPIOID_TARGETS`):

   a. **Query ChEMBL for bioactivity data:**
   ```python
   from chembl_webresource_client.new_client import new_client
   activity = new_client.activity

   results = activity.filter(
       target_chembl_id=target_chembl_id,
       standard_type__in=['Ki', 'IC50', 'EC50'],
       standard_units='nM',
       assay_type='B'
   ).only([
       'molecule_chembl_id', 'molecule_pref_name', 'canonical_smiles',
       'standard_type', 'standard_value', 'standard_units',
       'pchembl_value', 'assay_description'
   ])
   ```
   Rate limit at `config.CHEMBL_DELAY_SECONDS`.

   b. **Query GtoPdb for curated ligand data:**
   ```
   GET {GTOPDB_API_BASE}/targets/{gtopdb_id}/interactions
   ```
   Response is JSON with ligand-receptor interaction data including affinity values and action types (agonist/antagonist).

4. **For each opioid ingredient from the registry:**

   a. **Find its ChEMBL compound ID:**
   ```python
   molecule = new_client.molecule
   results = molecule.filter(pref_name__iexact=ingredient_name)
   ```

   b. **Get PubChem chemical properties:**
   ```
   GET {PUBCHEM_API_BASE}/compound/name/{ingredient_name}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChI,XLogP,TPSA/JSON
   ```

   c. **Collect receptor affinities** from ChEMBL data. For each receptor, find the best Ki value. Prefer values with highest `pchembl_value`.

   d. **Get mechanism of action from ChEMBL:**
   ```python
   mechanism = new_client.mechanism
   mech_data = mechanism.filter(molecule_chembl_id=chembl_id)
   ```

   e. **Determine selectivity:** Calculate ratios (Ki_mu / Ki_kappa, Ki_mu / Ki_delta) when data for multiple receptors exists.

   f. **Generate the `why_its_an_opioid` explanation string.** Template:
   ```
   "{Name} is classified as an opioid because it acts as a {action} at the mu opioid receptor (OPRM1)
   with Ki = {ki} nM{selectivity_note}. {mechanism_description}. Its primary opioid effects —
   {effects} — are mediated through {receptor} receptor activation."
   ```

   g. **Compute potency vs morphine:** morphine_ki / drug_ki at mu receptor. Morphine = 1.0 reference.

   h. **Get pharmacokinetic data** from PubChem compound pages:
   ```
   GET https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Pharmacology+and+Biochemistry
   ```

5. **Save output** to `config.PHARMACOLOGY_OUTPUT` (leave `ld50_data` and `therapeutic_index` empty — Step 5 fills those):
   ```json
   {
     "metadata": {
       "sources": ["ChEMBL", "GtoPdb", "PubChem"],
       "generated_at": "ISO-8601"
     },
     "receptor_targets": { ... },
     "ingredient_pharmacology": {
       "morphine": {
         "rxcui_ingredient": "7052",
         "pubchem_cid": "5288826",
         "chembl_id": "CHEMBL70",
         "smiles": "...",
         "molecular_weight": 285.34,
         "receptor_affinities": {
           "mu": { "ki_nM": 1.8, "action": "full agonist", "source": "GtoPdb" }
         },
         "why_its_an_opioid": "Morphine is classified as an opioid because...",
         "potency_vs_morphine": 1.0,
         "ld50_data": [],
         "therapeutic_index": null,
         "half_life_hours": 2.5,
         "onset_minutes": 15,
         "duration_hours": 4,
         "metabolism": "UGT2B7 glucuronidation",
         "active_metabolites": ["morphine-6-glucuronide", "morphine-3-glucuronide"]
       }
     }
   }
   ```

6. **Add a `main()` function.**

---

## Step 5: Build `opioid_track/ingestion/toxicology_fetcher.py`

This script adds lethality and toxicology data to the pharmacology file. *(Built directly against PubChem and TDC APIs.)*

### What this script must do:

1. **Load `config.PHARMACOLOGY_OUTPUT`** (created by Step 4). This script updates the `ld50_data` and `therapeutic_index` fields.

2. **For each ingredient, query PubChem for acute toxicity data:**
   ```
   GET https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Toxicity
   ```
   Parse the response to find LD50 values (strings like "LD50 (rat, oral) = 260 mg/kg"). Extract: species, route, LD50 value (mg/kg), and source reference.

3. **Optionally get additional LD50 data from Therapeutics Data Commons:**
   ```bash
   pip install PyTDC
   ```
   ```python
   from tdc.single_pred import Tox
   data = Tox(name='LD50_Zhu')
   df = data.get_data()
   ```
   Match by SMILES. If PyTDC installation fails, skip and proceed with PubChem data only.

4. **Compute estimated human lethal dose** using interspecies body surface area scaling:
   ```
   HED (mg/kg) = animal_LD50 (mg/kg) × (animal_Km / human_Km)
   ```
   Use `config.KM_SCALING`. Prefer rat oral data. Convert to absolute dose: `human_lethal_dose_mg = HED × 70`.

5. **Compute therapeutic index** where possible:
   ```
   TI = LD50 / ED50
   ```
   Use EC50 from ChEMBL at the mu receptor as a proxy for ED50 if available.

6. **Rank all opioid ingredients by danger** and add `danger_rank` + `danger_level` fields:
   - "Extreme": estimated lethal dose < 1 mg for 70 kg human
   - "Very High": < 10 mg
   - "High": < 100 mg
   - "Moderate": < 1000 mg
   - "Lower": ≥ 1000 mg

7. **Build the shared ingredient cross-reference.** For each ingredient, list all products in the Tier 1 registry containing it.

8. **Update and save `config.PHARMACOLOGY_OUTPUT`** with the toxicology additions.

9. **Add a `main()` function.**

---

## Step 6: Build `opioid_track/core/nlp_miner.py`

> **Reproducibility: adapts `CDCgov/Opioid_Involvement_NLP`**
>
> The CDC's `Opioid_Involvement_NLP` repository provides production-grade NLP for detecting opioid involvement in clinical text, including NegEx-based negation detection. Rather than building a custom NLP pipeline, adapt its annotator to work on DailyMed SPL label sections and FAERS narrative fields.
>
> **Read the cloned repo first.** Understand its input format (plain text strings), its output format (annotations with opioid presence flags and negation), and whether it uses spaCy, NLTK, or regex-based approaches. The adaptation below assumes a text-in / annotation-out pattern — adjust if the actual API differs.

### Setup:

```python
import sys
sys.path.insert(0, config.CDC_NLP_VENDOR_DIR)
# Then import whatever the CDC repo exposes — check its __init__.py or main module
```

### What this module must do:

1. **For each opioid in the Tier 1 registry that has an `spl_set_id`**, fetch the full SPL XML from DailyMed:
   ```
   GET https://dailymed.nlm.nih.gov/dailymed/services/v2/spls/{spl_set_id}.xml
   ```
   If no `spl_set_id`, search by drug name:
   ```
   GET https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json?drug_name={name}
   ```

2. **Parse the SPL XML** and extract each section by LOINC code (from `config.SPL_OPIOID_SECTIONS`). Use Python's `xml.etree.ElementTree`. Handle XML namespace prefixes (`urn:hl7-org:v3`). Extract the plain text content from each section's `<text>` element.

3. **Pass each extracted section's plain text through the CDC NLP annotator.** Use the `CDCgov/Opioid_Involvement_NLP` pipeline to detect:
   - Opioid term mentions and their context
   - Negated opioid mentions (e.g., "no respiratory depression" vs. "respiratory depression")
   - Safety signal terms from `config.OPIOID_SAFETY_TERMS`

   For each section, store the annotator's output alongside the raw extracted text.

4. **Run the CDC NLP annotator on FAERS narrative text** from `faers_opioid_queries.json` (the baseline snapshot's narrative fields, if available). This extends opioid detection beyond structured MedDRA codes to free-text descriptions.

5. **Extract structured data from key sections** using regex and the NLP annotations. Do not use regex alone — use the CDC annotator's output to disambiguate negated mentions:

   **From Boxed Warning (34066-1):**
   - Count of distinct warning bullets/paragraphs
   - Detect NLP-confirmed (non-negated) mentions of: "addiction", "respiratory depression", "neonatal", "benzodiazepine", "death"
   - Full text

   **From Dosage & Administration (34068-7):**
   - Starting dose (regex: `\d+\.?\d*\s*(mg|mcg|µg)`)
   - Maximum recommended daily dose
   - Max daily MME via Tier 1 MME mapper

   **From Adverse Reactions (34084-4):**
   - Frequency tables from `<table>` elements in the XML
   - Reaction name + frequency percentage pairs
   - Respiratory depression frequency

   **From Drug Interactions (34073-7):**
   - Contraindicated co-medications
   - Benzodiazepine interaction warnings
   - CYP enzyme interaction warnings (CYP3A4, CYP2D6)

   **From Abuse and Dependence (42227-9):**
   - DEA schedule
   - Abuse potential language (high/moderate/low)

   **From Overdosage (34088-5):**
   - Naloxone rescue dosing if mentioned
   - Symptoms of overdose

   **REMS check:**
   - Look for LOINC code containing "REMS" or search for "Risk Evaluation and Mitigation" in the full document text

6. **Build a comparison matrix** across all opioid labels:
   ```json
   [
     {
       "drug_name": "OxyContin",
       "rxcui": "...",
       "max_daily_dose_mg": 288,
       "max_daily_mme": 432,
       "resp_depression_in_trials": "2%",
       "boxed_warning_count": 4,
       "benzo_warning": true,
       "rems_required": true,
       "rems_type": "ETASU + Medication Guide",
       "schedule": "CII",
       "naloxone_rescue_dose": "0.4 to 2 mg IV",
       "nlp_source": "CDCgov/Opioid_Involvement_NLP"
     }
   ]
   ```

7. **Save output** to `config.NLP_INSIGHTS_OUTPUT` with `"nlp_source": "CDCgov/Opioid_Involvement_NLP"` in the metadata.

8. **Add a `main()` function.**

---

## Step 7: Build the Opioid Dashboard

> **Reproducibility: adapts `plotly/dash-opioid-epidemic-demo`**
>
> The dashboard is a **standalone Streamlit app** running independently from the main TruPharma app. Rather than building the choropleth map and chart logic from scratch, port the county-level choropleth map approach from `plotly/dash-opioid-epidemic-demo`. That repo uses Plotly's choropleth with county FIPS codes and a color metric selector — exactly what the geography page needs.
>
> The key adaptation: the original repo is Plotly Dash. You are building in Streamlit. Read `dash-opioid-epidemic-demo/app.py` and adapt the figure-building functions (which use `plotly.graph_objects` — fully compatible with Streamlit) into `opioid_track/dashboard/components/charts.py`. You are porting Plotly figure logic, not the Dash callback/layout system.
>
> Also read `opioiddatalab/overdosedata` as a reference for how a Streamlit opioid dashboard loads JSON data and structures page navigation using `st.sidebar`.

### `opioid_track/dashboard/opioid_app.py` — Main entry point:

1. Runnable via:
   ```bash
   streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
   ```

2. **Set up sidebar navigation** with 4 pages:
   - Drug Explorer
   - Opioid Landscape
   - Geographic Intelligence
   - Signal Detection

3. **Load all data once at startup** using `@st.cache_data`:
   - Registry from `opioid_track/core/registry`
   - All JSON files from `opioid_track/data/`
   - If Tier 2 data files are missing, show "Data not yet available" on those pages instead of crashing

### `opioid_track/dashboard/components/charts.py` — Ported from `plotly/dash-opioid-epidemic-demo`:

Read `dash-opioid-epidemic-demo/app.py` before writing this file. Port the following figure-building patterns:
- The county choropleth using `plotly.graph_objects.Choropleth` with FIPS-based location matching
- The color scale and hover template patterns
- The metric selector logic (switching the color metric between prescribing rate, death rate, etc.)

Implement these reusable functions (adapted from the Dash demo's figure builders):

```python
def create_choropleth(geo_data: dict, metric: str) -> plotly.Figure
    # Adapted from plotly/dash-opioid-epidemic-demo choropleth logic
    # geo_data = opioid_geographic_profiles.json counties list
    # metric = one of: "risk_score", "opioid_prescribing_rate", "death_rate_per_100k", "pills_per_capita"

def create_potency_chart(pharmacology_data: dict) -> plotly.Figure
def create_danger_scatter(pharmacology_data: dict, signal_data: list) -> plotly.Figure
def create_signal_heatmap(signal_data: list) -> plotly.Figure
def create_timeline_chart(mortality_data: dict) -> plotly.Figure
```

Each function should include a comment noting its origin (e.g., `# Choropleth logic adapted from plotly/dash-opioid-epidemic-demo`).

### `opioid_track/dashboard/pages/drug_explorer.py`:

1. **Search bar** — text input for drug name, RxCUI, or NDC. Use registry lookup functions. Show matched drug names as a selectbox.

2. **Drug Identity Card** — name, schedule, opioid category, active ingredients (opioid component highlighted).

3. **Pharmacology Panel** (from `opioid_pharmacology.json`):
   - Receptor binding affinities as a bar chart (mu, kappa, delta Ki values on log scale)
   - Potency vs morphine metric card
   - `why_its_an_opioid` explanation text
   - Metabolism pathway, half-life, active metabolites

4. **Safety Panel**:
   - MME conversion factor metric card
   - LD50 data table
   - Therapeutic index with color coding (red = narrow/dangerous, green = wide/safer)
   - Danger rank and level

5. **FAERS Signals Panel** (from `faers_signal_results.json`):
   - Top adverse reactions with signal flags
   - Color badges: red = consensus signal, yellow = partial signal, green = no signal

6. **Label Highlights Panel** (from `opioid_nlp_insights.json`):
   - Boxed warning text in a red-bordered container
   - REMS status
   - Key drug interactions
   - Max recommended dose

7. **Other Products Panel** — all products containing the same opioid ingredient with dose strengths.

### `opioid_track/dashboard/pages/landscape.py`:

1. **Classification View** — treemap or sunburst: Category → Individual drugs, sized by FAERS report count.
2. **Potency Comparison** — horizontal bar chart of ingredients ranked by mu-receptor Ki (log scale), morphine as reference line.
3. **Danger Matrix** — scatter plot: X = therapeutic index, Y = FAERS total reports, bubble size = FAERS deaths, color = opioid category.
4. **Three Waves Timeline** — line chart of overdose deaths by opioid subtype from CDC data. Annotate the three waves.
5. **Schedule Breakdown** — donut chart by DEA schedule.

### `opioid_track/dashboard/pages/geography.py` — Adapted from `plotly/dash-opioid-epidemic-demo`:

This page uses the choropleth logic ported from the Dash demo. Read `dash-opioid-epidemic-demo/app.py` before implementing.

1. **Choropleth Map** — use `create_choropleth()` from `charts.py`. The data source is `opioid_geographic_profiles.json`. Add a metric selector dropdown above the map (prescribing rate, death rate, pills per capita, risk score). The Dash demo already shows how to update the choropleth's `z` values based on a dropdown — replicate this with Streamlit's `st.selectbox` and re-render the figure.

2. **State Comparison** — horizontal bar chart comparing states on the selected metric.

3. **Year Slider** — if temporal data is available, allow scrubbing through years with `st.slider`.

4. **County Detail Panel** — selectbox to pick a state, then show county-level CMS, CDC, and ARCOS data side by side.

### `opioid_track/dashboard/pages/signals.py`:

1. **Signal Heatmap** — `create_signal_heatmap()` matrix: drugs × reactions. Color = methods flagging count (0=green, 4=red).
2. **Signal Detail** — select a drug-reaction pair; show PRR, ROR, MGPS values in a metrics row.
3. **Top Signals Table** — sortable, ranked by methods flagging count then report count.

---

## Step 8: Build `opioid_track/agents/opioid_watchdog.py`

This standalone agent module can be imported into the main TruPharma app when the team is ready to integrate, but also works independently within the opioid dashboard.

### What this module must do:

1. **Define the Opioid Watchdog agent class:**
   ```python
   class OpioidWatchdog:
       def __init__(self, registry, pharmacology_data, signal_data, nlp_insights):
           # Load all data sources

       def is_opioid_query(self, drug_name_or_rxcui: str) -> bool
       def get_full_opioid_brief(self, rxcui: str) -> dict
       def answer_why_opioid(self, drug_name: str) -> str
       def compare_danger(self, drug1: str, drug2: str) -> str
       def get_signals_summary(self, rxcui: str) -> str
       def get_label_warnings(self, rxcui: str) -> str
       def find_drugs_with_ingredient(self, ingredient: str) -> list[dict]
       def assess_dose_risk(self, drug_name: str, daily_dose_mg: float) -> dict
   ```

2. **The `get_full_opioid_brief()` method** returns a dict with: drug identity, pharmacology summary, safety summary, FAERS signals, label highlights, prescribing context, epidemic context.

3. **All text-returning methods** produce plain text strings suitable for a chat interface or LLM context window. They cite specific numbers (Ki values, LD50, FAERS counts) rather than vague answers.

4. **Handle missing data gracefully.** If pharmacology data isn't available for a drug, say so explicitly. If signal detection hasn't run for a drug, say so.

---

## Step 9: Build `opioid_track/core/knowledge_indexer.py`

This module prepares opioid data as text chunks for RAG indexing. It does NOT modify the main TruPharma RAG index — it produces standalone text files that can be added to any RAG system.

### What this module must do:

1. **Create** `config.KNOWLEDGE_CHUNKS_DIR`.

2. **Generate classification knowledge chunks** from the registry:
   - One chunk on opioid classification categories (natural, semi-synthetic, synthetic)
   - One chunk on the receptor system (mu, kappa, delta, NOP) and their roles
   - One chunk on DEA scheduling for opioids
   - One chunk listing all opioids by category with examples

3. **Generate per-ingredient pharmacology chunks** from `opioid_pharmacology.json`:
   - For each ingredient: name, receptor affinities, `why_its_an_opioid` text, potency, LD50, therapeutic index, metabolism, half-life
   - Target ~500–600 tokens per chunk

4. **Generate per-drug safety chunks** from `opioid_nlp_insights.json`:
   - For each drug: boxed warning summary, max dose, REMS status, key interactions, overdosage info

5. **Generate epidemiological context chunks** from Tier 2 data:
   - Three waves of the opioid epidemic with CDC death counts
   - Top states by prescribing rate
   - Top states by death rate
   - Demographic patterns

6. **Generate FAERS signal chunks** from signal detection results:
   - One chunk per drug summarizing its consensus safety signals

7. **Save all chunks** as individual `.txt` files in `config.KNOWLEDGE_CHUNKS_DIR/`.

8. **Save a manifest** `knowledge_chunks/manifest.json` listing all chunks with metadata:
   ```json
   [
     {
       "filename": "ingredient_morphine.txt",
       "type": "pharmacology",
       "drug_name": "morphine",
       "rxcui": "7052",
       "token_estimate": 550
     }
   ]
   ```

9. **Add a `main()` function.**

---

## Step 10: Build Tests

### `opioid_track/tests/test_pharmacology.py`:

1. Test that `opioid_pharmacology.json` exists and loads.
2. Test that morphine has mu receptor data with Ki value.
3. Test that `potency_vs_morphine` for morphine is 1.0.
4. Test that at least 10 ingredients have receptor affinity data.
5. Test that `why_its_an_opioid` is populated for at least 10 ingredients.
6. Test that LD50 data exists for at least 5 ingredients after the toxicology step.
7. Test that `opioid_nlp_insights.json` metadata contains `"nlp_source": "CDCgov/Opioid_Involvement_NLP"`.
8. Test that the vendor repos are present: `opioid_track/vendor/Opioid_Involvement_NLP/` and `opioid_track/vendor/dash-opioid-epidemic-demo/` must exist.

---

## Step 11: Update `opioid_track/README.md`

Append a Tier 3 section explaining:
- The pharmacology and toxicology data (what it contains, where it comes from)
- **The two repos adapted in this tier and how** (`CDCgov/Opioid_Involvement_NLP` for NLP, `plotly/dash-opioid-epidemic-demo` for geographic charts)
- How to clone the vendor repos (Step 3 commands)
- How to run the NLP miner
- How to launch the standalone dashboard:
  ```bash
  streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
  ```
- How the knowledge chunks can be integrated into any RAG system
- How the OpioidWatchdog agent can be imported into the main TruPharma app when ready:
  ```python
  from opioid_track.agents.opioid_watchdog import OpioidWatchdog
  ```

---

## Step 12: Run and Validate

```bash
# Step 1: Clone vendor repos (if not done in Step 3 setup)
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git opioid_track/vendor/Opioid_Involvement_NLP
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git opioid_track/vendor/dash-opioid-epidemic-demo
git clone https://github.com/opioiddatalab/overdosedata.git opioid_track/vendor/overdosedata

# Step 2: Install new dependencies
pip install chembl_webresource_client PyTDC

# Step 3: Fetch pharmacology data (ChEMBL + GtoPdb + PubChem)
python -m opioid_track.ingestion.pharmacology_fetcher

# Step 4: Fetch toxicology data
python -m opioid_track.ingestion.toxicology_fetcher

# Step 5: Run NLP label mining (uses CDCgov/Opioid_Involvement_NLP)
python -m opioid_track.core.nlp_miner

# Step 6: Generate knowledge chunks
python -m opioid_track.core.knowledge_indexer

# Step 7: Tests
pytest opioid_track/tests/test_pharmacology.py

# Step 8: Launch the dashboard (adapts plotly/dash-opioid-epidemic-demo)
streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
```

Verify:
- `opioid_pharmacology.json` has receptor data for 15+ ingredients
- `opioid_nlp_insights.json` metadata has `"nlp_source": "CDCgov/Opioid_Involvement_NLP"` and label data for 20+ opioid products
- Dashboard launches and all 4 pages render without errors
- Geography page choropleth renders county-level data (ported from `plotly/dash-opioid-epidemic-demo`)
- Knowledge chunks directory has 50+ text files
- No existing TruPharma files were modified
- No Tier 1 or Tier 2 files were modified (unless fixing bugs)
- All three vendor repos present in `opioid_track/vendor/`

---

## Final File Structure After All 3 Tiers

```
TruPharma-Clinical-Intelligence/            ← EXISTING PROJECT (completely untouched)
├── src/                                     ← NEVER MODIFIED
├── opioid_track/                            ← ENTIRE OPIOID ADD-ON (self-contained)
│   ├── __init__.py
│   ├── config.py
│   ├── README.md
│   ├── requirements.txt
│   ├── vendor/
│   │   ├── cdc-wonder-api/                  # Tier 2: alipphardt/cdc-wonder-api
│   │   ├── arcos-py/                        # Tier 2: marc-rauckhorst/arcos-py (fallback)
│   │   ├── Opioid_Involvement_NLP/          # Tier 3: CDCgov/Opioid_Involvement_NLP
│   │   ├── dash-opioid-epidemic-demo/       # Tier 3: plotly/dash-opioid-epidemic-demo
│   │   └── overdosedata/                    # Tier 3: opioiddatalab/overdosedata (reference)
│   ├── ingestion/
│   │   ├── rxclass_opioid_fetcher.py        # Tier 1
│   │   ├── ndc_opioid_classifier.py         # Tier 1 — uses ripl-org/historical-ndc
│   │   ├── mme_mapper.py                    # Tier 1 — uses jbadger3/ml_4_pheno_ooe
│   │   ├── faers_opioid_filter.py           # Tier 1
│   │   ├── cms_opioid_fetcher.py            # Tier 2
│   │   ├── cdc_mortality_fetcher.py         # Tier 2 — uses alipphardt/cdc-wonder-api
│   │   ├── arcos_fetcher.py                 # Tier 2 — uses arcospy
│   │   ├── pharmacology_fetcher.py          # Tier 3
│   │   └── toxicology_fetcher.py            # Tier 3
│   ├── core/
│   │   ├── registry_builder.py              # Tier 1
│   │   ├── registry.py                      # Tier 1
│   │   ├── signal_detector.py               # Tier 2 — uses ChapatiDB/faerslib
│   │   ├── geographic_joiner.py             # Tier 2
│   │   ├── nlp_miner.py                     # Tier 3 — uses CDCgov/Opioid_Involvement_NLP
│   │   └── knowledge_indexer.py             # Tier 3
│   ├── agents/
│   │   └── opioid_watchdog.py               # Tier 3
│   ├── dashboard/
│   │   ├── opioid_app.py                    # Tier 3 (standalone Streamlit)
│   │   ├── pages/
│   │   │   ├── drug_explorer.py
│   │   │   ├── landscape.py
│   │   │   ├── geography.py                 # adapts plotly/dash-opioid-epidemic-demo
│   │   │   └── signals.py
│   │   └── components/
│   │       └── charts.py                    # ported choropleth from dash-opioid-epidemic-demo
│   ├── data/
│   │   ├── raw/
│   │   │   ├── ndc-opioids.csv              # from ripl-org/historical-ndc
│   │   │   ├── rxcui_mme_mapping.json       # from jbadger3/ml_4_pheno_ooe
│   │   │   └── arcos/                       # arcospy response cache
│   │   ├── opioid_registry.json             # Tier 1 canonical
│   │   ├── faers_signal_results.json        # Tier 2 — via ChapatiDB/faerslib
│   │   ├── opioid_geographic_profiles.json  # Tier 2
│   │   ├── opioid_pharmacology.json         # Tier 3
│   │   ├── opioid_nlp_insights.json         # Tier 3 — via CDCgov NLP
│   │   └── knowledge_chunks/               # Tier 3
│   │       ├── manifest.json
│   │       └── *.txt
│   └── tests/
│       ├── test_registry.py                 # Tier 1
│       ├── test_signal_detector.py          # Tier 2
│       ├── test_geographic_joiner.py        # Tier 2
│       └── test_pharmacology.py             # Tier 3
└── ...
```

---

## Splitting Work Across Multiple Agents Within This Tier

- **Agent 1:** Step 3 (clone repos + read them), then Step 4 (pharmacology fetcher)
- **Agent 2:** Step 6 (NLP miner — clone and adapt `CDCgov/Opioid_Involvement_NLP`) — can run in parallel with Agent 1 since it uses Tier 1 data only
- **After Agent 1 finishes Step 4 →** Step 5 (toxicology fetcher, depends on pharmacology file)
- **Agent 3:** Step 7 (dashboard — start scaffolding while pharmacology data fetches; port `plotly/dash-opioid-epidemic-demo` choropleth into `charts.py` first)
- **After all data is ready:** Steps 8–12 (watchdog agent, knowledge indexer, tests, validation)
