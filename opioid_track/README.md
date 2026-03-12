# TruPharma Opioid Intelligence Track 💊

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A self-contained, data-driven intelligence platform for analyzing opioid risk, pharmacology, and real-world epidemiology.**

The Opioid Track answers a deceptively simple question: **"Is this drug an opioid, and if so, how dangerous is it?"** — then backs the answer with hard data from a dozen authoritative sources, including the FDA, CDC, CMS, PubChem, and ChEMBL.

---

## 🚀 Quick Start

The entire system is reproducible from scratch and runs entirely offline after the first data ingestion run. 

### Prerequisites

```bash
cd TruPharma-Clinical-Intelligence
pip install -r opioid_track/requirements.txt
```

### 1. Clone External Dependencies
The project relies on specific open-source methodologies. Clone them into the `vendor` directory:

```bash
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git opioid_track/vendor/Opioid_Involvement_NLP
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git opioid_track/vendor/dash-opioid-epidemic-demo
git clone https://github.com/opioiddatalab/overdosedata.git opioid_track/vendor/overdosedata
```

### 2. Launch the Streamlit Dashboard
```bash
streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
```

### 3. Use the Python API (OpioidWatchdog)
```python
from opioid_track.agents.opioid_watchdog import OpioidWatchdog

watchdog = OpioidWatchdog()
watchdog.answer_why_opioid("fentanyl")
watchdog.compare_danger("fentanyl", "morphine")
```

---

## 🧠 Architecture & Methodology

Built on strict principles of **Complete Isolation** (never modifies parent projects), **Reproducibility**, and **Offline-First Data Storage**, the project is structured across four cumulative tiers of intelligence:

### Tier 1: Opioid Classification Foundation
- Builds a canonical registry of **1,236 opioid RxCUIs** and **197,043 NDC codes**.
- Maps drugs to Morphine Milligram Equivalents (MME) using peer-reviewed ML datasets.
- Establishes baseline adverse event profiles from OpenFDA.

### Tier 1.5: Product Scaling & Real-Time Sync
- Expands the registry from ingredients to product-level formulations (SCD/SBD).
- Implements real-time synchronization with the OpenFDA API for newly approved opioids.

### Tier 2: Epidemiology & Pharmacovigilance
- Ingests **CMS Medicare Part D** prescribing rates and **CMS Medicaid** supply chain data.
- Fetches **CDC Provisional Overdose Death** data (81K+ records).
- Runs on-the-fly Signal Detection math (PRR, ROR, EBGM) against FAERS, discovering **204 consensus safety signals** for opioids.
- Builds geographic profiles for 3,148 US counties.

### Tier 3: Pharmacology & NLP Label Mining
- Queries **ChEMBL**, **GtoPdb**, and **PubChem** for receptor binding affinities (Mu, Kappa, Delta) and toxicology (LD50).
- Employs **CDC NegEx NLP** algorithms to mine DailyMed Structured Product Labels for boxed warnings, overdose symptoms, and REMS requirements.
- Packages insights into **55 RAG-optimized knowledge chunks**.

---

## 📊 The Dashboard

The Streamlit interface offers five interactive workspaces:

1. **Drug Explorer**: Deep-dive into individual opioids (binding affinities, 3D molecular structures, label highlights).
2. **Opioid Landscape**: Macro-level classification, potency comparisons, and a danger matrix.
3. **Geographic Intelligence**: Interactive choropleth maps showing national risk distributions and prescribing trends.
4. **Signal Detection**: FAERS pharmacovigilance heatmaps and consensus metric tables.
5. **Watchdog Tools**: Interactive utilities like the Dose Risk Calculator and side-by-side Danger Comparator.

---

## 🔬 Testing

The system boasts a comprehensive test suite (38 total tests) to ensure data provenance and functional integrity.

```bash
pytest opioid_track/tests/ -v
```

---

## 📚 Documentation

For an exhaustive breakdown of the APIs used, specific data sources, data flow architecture, and how to re-run the entire ingestion pipeline from scratch, refer to the [Complete Technical Reference](docs/OPIOID_TRACK_COMPLETE.md).
