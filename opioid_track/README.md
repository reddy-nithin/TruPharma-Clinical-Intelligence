# Opioid Track — Tier 1: Opioid Classification Foundation

An isolated add-on to [TruPharma Clinical Intelligence](../README.md) that builds a comprehensive opioid drug registry from authoritative, peer-reviewed data sources.

## Design Principles

- **Isolation**: Completely self-contained — if anything breaks here, the parent TruPharma project is untouched
- **Reproducibility**: All data can be regenerated from scratch by re-running the ingestion scripts
- **Peer-reviewed sources**: Primary data comes from published, versioned GitHub repositories

## External Data Sources

| Source | Purpose | License |
|--------|---------|---------|
| [ripl-org/historical-ndc](https://github.com/ripl-org/historical-ndc) | Pre-classified NDC→opioid lookup (1998–2018, JAMIA 2020) | MIT |
| [jbadger3/ml_4_pheno_ooe](https://github.com/jbadger3/ml_4_pheno_ooe) | RxCUI→MME mapping (peer-reviewed ML phenotyping) | MIT |
| [NLM RxClass API](https://rxnav.nlm.nih.gov/RxClassAPIs.html) | ATC, MED-RT, FDA EPC drug classification | Public domain |
| [NLM RxNorm API](https://rxnav.nlm.nih.gov/RxNormAPIs.html) | Drug name/RxCUI resolution | Public domain |
| [OpenFDA API](https://open.fda.gov/apis/) | NDC supplement, FAERS adverse events, drug labels | Public domain |

## How to Run

### 1. Install dependencies

```bash
pip install -r opioid_track/requirements.txt
```

### 2. Run the ingestion pipeline

```bash
# Step 1: Enumerate opioid drugs from RxClass API
python3 -m opioid_track.ingestion.rxclass_opioid_fetcher

# Step 2: Classify NDC codes (downloads ripl-org/historical-ndc)
python3 -m opioid_track.ingestion.ndc_opioid_classifier

# Step 3: Build MME mapping (downloads jbadger3/ml_4_pheno_ooe)
python3 -m opioid_track.ingestion.mme_mapper

# Step 4: Fetch FAERS baseline
python3 -m opioid_track.ingestion.faers_opioid_filter
```

### 3. Build the registry

```bash
python3 -m opioid_track.core.registry_builder
```

### 4. Run tests

```bash
pytest opioid_track/tests/ -v
```

## Using the Registry API

```python
from opioid_track.core.registry import (
    is_opioid, get_opioid_profile, get_mme_factor,
    calculate_daily_mme, list_all_opioid_rxcuis,
)

# Check if a drug is an opioid
is_opioid("7052")  # True (morphine)

# Get full drug profile
profile = get_opioid_profile("7052")

# Get MME conversion factor
get_mme_factor("oxycodone")  # 1.5

# Calculate daily MME with risk level
result = calculate_daily_mme("oxycodone", 60)
# {'daily_mme': 90.0, 'risk_level': 'high', 'mme_factor_used': 1.5}

# List all opioid RxCUIs
rxcuis = list_all_opioid_rxcuis()  # ~189 RxCUIs
```

## Directory Structure

```
opioid_track/
├── __init__.py
├── config.py                  # Central configuration
├── README.md                  # This file
├── requirements.txt           # requests>=2.28.0
├── data/
│   ├── raw/                   # Downloaded source files (cached)
│   │   ├── ndc-opioids.csv           # from ripl-org/historical-ndc
│   │   └── rxcui_mme_mapping.json    # from jbadger3/ml_4_pheno_ooe
│   ├── rxclass_opioid_enumeration.json
│   ├── ndc_opioid_lookup.json
│   ├── mme_reference.json
│   ├── faers_opioid_queries.json
│   └── opioid_registry.json          # THE canonical output
├── ingestion/
│   ├── __init__.py                    # Shared retry_get utility
│   ├── rxclass_opioid_fetcher.py      # RxClass API enumeration
│   ├── ndc_opioid_classifier.py       # NDC classification
│   ├── mme_mapper.py                  # MME factor mapping
│   └── faers_opioid_filter.py         # FAERS query templates
├── core/
│   ├── __init__.py
│   ├── registry_builder.py            # Merges all outputs
│   └── registry.py                    # Runtime API
├── tests/
│   ├── __init__.py
│   └── test_registry.py
└── docs/
    ├── DEV_LOG.md                     # Development diary
    ├── TECHNICAL.md                   # Architecture documentation
    └── TIER*_INSTRUCTIONS*.md         # Original instruction files
```

## Tier 3: Deep Pharmacology, NLP, and Dashboards

Tier 3 adds molecular-level pharmacology, NLP-mined drug label intelligence, a standalone Streamlit dashboard, an OpioidWatchdog agent, and RAG-ready knowledge chunks.

### Pharmacology & Toxicology Data

- **Receptor binding affinities** (Ki, IC50, EC50) at mu, kappa, delta, and NOP opioid receptors from ChEMBL and GtoPdb
- **Toxicology**: LD50 data from PubChem with interspecies BSA scaling for estimated human lethal doses
- **Per-ingredient profiles**: potency vs morphine, therapeutic index, danger ranking, metabolism, half-life

### NLP Label Mining

Adapts [CDCgov/Opioid_Involvement_NLP](https://github.com/CDCgov/Opioid_Involvement_NLP) for DailyMed SPL label analysis:
- NegEx-based negation detection (distinguishes "respiratory depression" from "no respiratory depression")
- Structured extraction from 9 SPL sections: boxed warnings, dosage, adverse reactions, drug interactions, abuse/dependence, overdosage, REMS
- Comparison matrix across all mined labels

### Standalone Dashboard

Geographic charts adapted from [plotly/dash-opioid-epidemic-demo](https://github.com/plotly/dash-opioid-epidemic-demo).

```bash
streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
```

4 pages: Drug Explorer, Opioid Landscape, Geographic Intelligence, Signal Detection.

### OpioidWatchdog Agent

Importable into the main TruPharma app when ready:

```python
from opioid_track.agents.opioid_watchdog import OpioidWatchdog

watchdog = OpioidWatchdog()  # auto-loads all data files
watchdog.answer_why_opioid("fentanyl")
watchdog.compare_danger("fentanyl", "morphine")
watchdog.assess_dose_risk("oxycodone", 60)
```

### Knowledge Chunks for RAG

55 text chunks in `data/knowledge_chunks/` with a `manifest.json`. Framework-agnostic — works with LangChain, LlamaIndex, or any custom RAG pipeline.

### Clone Vendor Repos (Required for Tier 3)

```bash
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git opioid_track/vendor/Opioid_Involvement_NLP
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git opioid_track/vendor/dash-opioid-epidemic-demo
git clone https://github.com/opioiddatalab/overdosedata.git opioid_track/vendor/overdosedata
```

### Run Tier 3 Pipelines

```bash
# Pharmacology (ChEMBL + GtoPdb + PubChem) — ~2 min
python3 -m opioid_track.ingestion.pharmacology_fetcher

# Toxicology (PubChem LD50 + interspecies scaling)
python3 -m opioid_track.ingestion.toxicology_fetcher

# NLP label mining (DailyMed + CDC NLP)
python3 -m opioid_track.core.nlp_miner

# Knowledge chunks for RAG
python3 -m opioid_track.core.knowledge_indexer
```

### Run All Tests

```bash
pytest opioid_track/tests/ -v  # 38 tests across Tiers 1–3
```

## Reproducing from Scratch

If the `data/` directory is deleted, simply re-run the ingestion pipeline — all source data will be re-downloaded from GitHub and public APIs automatically.
