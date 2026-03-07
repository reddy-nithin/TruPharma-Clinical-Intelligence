# TruPharma Opioid Intelligence Track — Complete Technical Reference

**Version:** 3.0.0 | **Last Updated:** 2026-03-07  
**Project:** Self-contained add-on to TruPharma Clinical Intelligence  
**Test Suite:** 38 tests, all passing

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [Design Principles](#2-design-principles)
3. [Architecture Overview](#3-architecture-overview)
4. [Tier 1 — Opioid Classification Foundation](#4-tier-1--opioid-classification-foundation)
5. [Tier 1.5 — Product Scaling and Real-Time Sync](#5-tier-15--product-scaling-and-real-time-sync)
6. [Tier 2 — External Data and Signal Detection](#6-tier-2--external-data-and-signal-detection)
7. [Tier 3 — Pharmacology, NLP, and Dashboard](#7-tier-3--pharmacology-nlp-and-dashboard)
8. [The Dashboard](#8-the-dashboard)
9. [The OpioidWatchdog Agent](#9-the-opioidwatchdog-agent)
10. [Knowledge Chunks for RAG](#10-knowledge-chunks-for-rag)
11. [All External Data Sources](#11-all-external-data-sources)
12. [Full Directory Structure](#12-full-directory-structure)
13. [How to Run Everything](#13-how-to-run-everything)
14. [Testing and Validation](#14-testing-and-validation)
15. [Known Limitations and Blockers Resolved](#15-known-limitations-and-blockers-resolved)

---

## 1. What This Project Does

The Opioid Track answers a deceptively simple question: **"Is this drug an opioid, and if so, how dangerous is it?"** — then backs the answer with hard data from a dozen authoritative sources.

It is an isolated, self-contained intelligence platform built in four tiers:

| Tier | What It Adds | Key Output |
|------|-------------|------------|
| **Tier 1** | Drug classification registry — which drugs are opioids, what's in them, how to convert their doses to a standard unit | `opioid_registry.json` (1,236 RxCUIs, 198K NDCs, 12K MME mappings) |
| **Tier 1.5** | Product-level scaling and real-time NDC sync for drugs approved after 2018 | Updated registry with SCD/SBD RxCUIs |
| **Tier 2** | Prescribing data (CMS), mortality data (CDC), supply chain data (Medicaid), and pharmacovigilance signal detection (FAERS) | 200K geographic records, 33.5K mortality records, 204 consensus safety signals, 3,148 county risk profiles |
| **Tier 3** | Receptor-level pharmacology, NLP-mined drug label intelligence, interactive dashboard, AI agent, and RAG-ready knowledge chunks | Pharmacology for 17 ingredients, NLP analysis of 18 drug labels, 5-page Streamlit dashboard, OpioidWatchdog agent, 55 knowledge chunks |

The entire system is reproducible from scratch. Delete the `data/` folder and re-run the ingestion scripts — everything regenerates automatically from public APIs and GitHub repositories.

---

## 2. Design Principles

These four principles were established in Tier 1 and carried through every subsequent tier:

**Complete Isolation.** The Opioid Track lives entirely inside `opioid_track/`. It never modifies any file in the parent TruPharma `src/` directory. If the Opioid Track breaks, the parent project is untouched.

**Reproducibility First.** Rather than building complex logic from scratch, the project pins to specific GitHub repositories with published, peer-reviewed methodologies. Eight external repos provide the heavy lifting — from NDC classification tables (JAMIA 2020) to NLP negation detection (CDC) to signal detection algorithms (EBGM/PRR/ROR).

**Warn and Continue.** No single API failure should crash the pipeline. If PubChem doesn't have LD50 data for codeine, the system logs it and moves on. Partial data is always better than no data.

**All Data Committed to Git.** Every JSON output is committed to the repository. This means the project works fully offline after the first run — no API calls needed to use the registry, launch the dashboard, or run the agent.

---

## 3. Architecture Overview

The system flows through three layers: **Ingestion** (fetch and normalize data from external sources), **Core** (process, join, and analyze the data), and **Presentation** (dashboard, agent, and knowledge chunks for RAG).

```
EXTERNAL SOURCES                    INGESTION LAYER                  CORE LAYER                     PRESENTATION
─────────────────                   ───────────────                  ──────────                     ────────────

NLM RxClass API ──────┐
NLM RxNorm API ───────┤
ripl-org/historical-ndc─┤── Tier 1 ──→ opioid_registry.json ────────────────→ registry.py (API) ───→ All downstream
jbadger3/ml_4_pheno_ooe─┤              (1,236 RxCUIs, 198K NDCs)             (13 functions)
OpenFDA FAERS API ────┘

CMS Medicare Part D ──┐
CDC VSRR Mortality ───┤── Tier 2 ──→ prescribing/mortality/supply JSONs ──→ geographic_joiner.py ──→ 3,148 county
CMS Medicaid ─────────┤              faers_signal_results.json                                       risk profiles
OpenFDA FAERS API ────┘              (204 consensus signals)              signal_detector.py
US Census ACS ────────┘                                                   (PRR, ROR, MGPS)

ChEMBL API ───────────┐
GtoPdb API ───────────┤── Tier 3 ──→ opioid_pharmacology.json ──→ nlp_miner.py ──→ Dashboard (5 pages)
PubChem API ──────────┤              (17 ingredients, receptor data)          OpioidWatchdog agent
DailyMed SPL XML ─────┤              opioid_nlp_insights.json                knowledge_indexer.py
CDCgov/Opioid_NLP ────┘              (18 drug labels mined)                  (55 RAG chunks)
```

---

## 4. Tier 1 — Opioid Classification Foundation

Tier 1 answers: **"Which drugs are opioids, what's in them, and how do you compare their doses?"**

### 4.1 The Problem

There is no single authoritative list of "all opioids." The FDA classifies drugs one way, the WHO (via ATC codes) another, and clinical pharmacology textbooks yet another. NDC codes (the barcodes on pill bottles) change constantly. Dose equivalence requires converting between drugs using Morphine Milligram Equivalents (MME), and even the CDC and academic literature disagree on some conversion factors.

### 4.2 How It Works

Four ingestion scripts run sequentially, each pulling from a different authoritative source:

**Step 1 — Drug Enumeration** (`rxclass_opioid_fetcher.py`): Queries the NLM RxClass API across three classification hierarchies (ATC, MED-RT, FDA EPC) to enumerate all drugs classified as opioids. This produces 85 unique drug entries from 11 ATC opioid classes, 3 MED-RT mechanisms, and 5 FDA pharmacologic classes.

**Step 2 — NDC Classification** (`ndc_opioid_classifier.py`): Downloads the ripl-org/historical-ndc dataset (published in JAMIA 2020, MIT license) — a pre-classified table mapping 195,451 NDC codes to opioid status from 1998 to 2018. Supplements with 1,592 post-2018 NDCs from the OpenFDA NDC API. Total: 197,043 NDCs with opioid/recovery flags.

**Step 3 — MME Mapping** (`mme_mapper.py`): Downloads the jbadger3/ml_4_pheno_ooe MME conversion dataset (12,082 RxCUI-level mappings from peer-reviewed ML phenotyping research). Cross-validates against the CDC's 14 named conversion factors. Where they disagree (tramadol, meperidine, fentanyl, buprenorphine), CDC values take priority.

**Step 4 — FAERS Baseline** (`faers_opioid_filter.py`): Queries the OpenFDA FAERS API to build baseline adverse event profiles for opioids — top 100 reactions, death reactions, demographics by sex and age, and yearly trends (7,065 data points). This baseline is used by Tier 2's signal detection.

**Step 5 — Registry Assembly** (`registry_builder.py`): Merges all four outputs into `opioid_registry.json` — the canonical data file. The runtime API (`registry.py`) exposes 13 functions for querying the registry without touching the JSON directly.

### 4.3 Key Numbers

| Metric | Value |
|--------|-------|
| Unique opioid RxCUIs | 1,236 (after Tier 1.5 scaling) |
| NDC codes classified | 197,043 (99.2% from ripl-org) |
| Opioid NDCs identified | 9,263 |
| MME conversion mappings | 12,082 (RxCUI-level) + 14 (CDC named) |
| Must-include opioids validated | 14/14 (morphine, fentanyl, oxycodone, etc.) |
| FAERS trend data points | 7,065 |
| Tests | 21 passing |

### 4.4 The Registry API

```python
from opioid_track.core.registry import is_opioid, calculate_daily_mme

is_opioid("7052")  # True — morphine
calculate_daily_mme("oxycodone", 60)
# → {'daily_mme': 90.0, 'risk_level': 'high', 'mme_factor_used': 1.5}
```

CDC risk thresholds: 50 MME/day = increased risk, 90 MME/day = high risk. Methadone uses dose-dependent tiered conversion (4 tiers up to 80+ mg/day).

---

## 5. Tier 1.5 — Product Scaling and Real-Time Sync

Tier 1 enumerated opioids at the ingredient level (e.g., "oxycodone" as a concept). Tier 1.5 expanded to product-level RxCUIs — Semantic Clinical Drugs (SCD) like "oxycodone 5 MG Oral Tablet" and Semantic Branded Drugs (SBD) like "OxyContin 10 MG Extended Release Oral Tablet." This dramatically increased the RxCUI count from 189 to 1,236.

Additionally, a real-time NDC sync module (`realtime_ndc_sync.py`) polls the OpenFDA NDC API for opioid products with marketing start dates from 2019 onward, covering drugs approved after the ripl-org dataset's cutoff.

Two new registry functions were added: `search_opioid_products("percocet")` for name-based product search and `get_newly_approved_opioids(2023)` for tracking recently approved formulations.

---

## 6. Tier 2 — External Data and Signal Detection

Tier 2 answers: **"Where are opioids being prescribed, where are people dying, and which drugs are throwing safety signals?"**

### 6.1 Prescribing Data — CMS Medicare Part D

The `cms_opioid_fetcher.py` pulls prescribing rates from CMS Medicare Part D across two datasets:

- **Geographic** (200,000 records, 2017–2023): opioid prescribing rates by state and county, year-over-year changes
- **Provider-Drug** (9,616 unique prescribers): individual NPI-level prescribing with high-prescriber flagging (235 flagged — top states: CA 22, TX 15, FL 14, NY 14)

A critical blocker was discovered and resolved during development: CMS migrated from Socrata to their `data-api/v1` in 2024, breaking all legacy dataset IDs (returning 410 Gone). The fix involved discovering new UUIDs via the `data.cms.gov/data.json` catalog.

### 6.2 Mortality Data — CDC VSRR

The `cdc_mortality_fetcher.py` pulls provisional overdose death data from the CDC's Vital Statistics Rapid Release (VSRR) system: 81,270 total records, 33,550 opioid-specific, covering 51 states and 11 years (2015–2025).

National annual summaries are structured by the **three waves of the opioid epidemic**:
- **Wave 1 (1990s–2010):** Prescription opioid overdoses (oxycodone, hydrocodone)
- **Wave 2 (2010–2013):** Heroin overdoses as prescription access tightened
- **Wave 3 (2013–present):** Illicitly manufactured fentanyl and analogues — now the dominant cause of overdose death

### 6.3 Supply Chain Data — CMS Medicaid

The original plan used the DEA's ARCOS data via the Washington Post API (`arcospy`). A major blocker occurred: the WaPo ARCOS API (`ne.washingtonpost.com`) went entirely offline. The system pivoted to CMS Medicaid Opioid Prescribing Rates as a supply chain proxy — 500,000 raw API rows covering 51 states, 2,723 counties, and 200.2 million total opioid claims.

### 6.4 Pharmacovigilance Signal Detection

Signal detection identifies drug-reaction pairs that occur more frequently than expected in the FDA's Adverse Event Reporting System (FAERS). Three standard disproportionality methods are used:

- **PRR** (Proportional Reporting Ratio) — simple frequency ratio with chi-squared
- **ROR** (Reporting Odds Ratio) — odds ratio with 95% confidence interval
- **MGPS/EBGM** (Empirical Bayes Geometric Mean) — Bayesian shrinkage to reduce false positives for rare events

A consensus signal requires at least 2 of 3 methods to flag. From 265 drug-reaction pairs analyzed across 14 drugs and 21 safety terms: **204 consensus signals** were detected.

Another blocker was resolved here: the original plan used `ChapatiDB/faerslib`, which requires a 100GB+ pre-built SQLite database. Instead, the PRR/ROR/EBGM math was ported directly and hooked into the live OpenFDA REST API, building 2x2 contingency tables on-the-fly from the 20 million+ report baseline.

### 6.5 Geographic Risk Profiles

The `geographic_joiner.py` joins CMS prescribing, CDC mortality, and Medicaid supply chain data by county FIPS code, enriched with US Census population data. Output: **3,148 county-level risk profiles**, each with a composite risk score and tier (Critical, High, Elevated, Moderate, Lower).

### 6.6 Key Numbers

| Pipeline | Runtime | Records | Output Size |
|----------|---------|---------|-------------|
| CMS Prescribing | 89.9s | 200K geo + 9.6K provider | 46 MB |
| CDC Mortality | 9.5s | 81.2K VSRR, 33.5K opioid | ~1 MB |
| Medicaid Supply Chain | 111.5s | 500K claims, 2,723 counties | ~6 MB |
| Signal Detection | 169.8s | 265 pairs → 204 consensus | ~100 KB |
| Geographic Joiner | 1.5s | 3,148 county profiles | ~1.5 MB |

---

## 7. Tier 3 — Pharmacology, NLP, and Dashboard

Tier 3 answers: **"WHY is this drug an opioid at the molecular level, what does its FDA label actually say, and can I see all of this in one place?"**

### 7.1 Receptor-Level Pharmacology

The `pharmacology_fetcher.py` queries three molecular databases for each of the 17 opioid ingredients in the registry:

**ChEMBL** — bioactivity data (Ki, IC50, EC50) at the four opioid receptors:
- **Mu (OPRM1)** — primary mediator of analgesia, euphoria, respiratory depression
- **Kappa (OPRK1)** — spinal analgesia, sedation, dysphoria
- **Delta (OPRD1)** — mood modulation, cardioprotection
- **NOP (OPRL1)** — pain modulation with sometimes anti-opioid effects

**GtoPdb** (Guide to Pharmacology) — curated ligand-receptor interactions with action types (agonist, antagonist, partial agonist). 256 interactions retrieved.

**PubChem** — molecular properties (formula, weight, SMILES), pharmacokinetics (half-life, metabolism, active metabolites).

For each ingredient, the system resolves the best receptor affinity values, generates a `why_its_an_opioid` explanation citing specific Ki values, and computes potency relative to morphine (morphine Ki / drug Ki at mu receptor).

Example: Fentanyl has a mu receptor Ki of 0.08 nM vs morphine's 1.8 nM, making it ~22x more potent at the receptor level.

16 of 17 ingredients have receptor data. The exception is meperidine, which is indexed as "pethidine" in ChEMBL.

### 7.2 Toxicology

The `toxicology_fetcher.py` adds lethality data:
- Fetches LD50 values from PubChem's toxicity data (available for 6 of 17 ingredients)
- Applies interspecies body surface area (BSA) scaling: `HED (mg/kg) = animal_LD50 × (animal_Km / human_Km)` to estimate human lethal doses
- Computes therapeutic index: `TI = LD50 / ED50` (using mu EC50 as an ED50 proxy)
- Classifies danger level by estimated human lethal dose (Extreme < 1 mg, Very High < 10 mg, High < 100 mg, Moderate < 1000 mg, Lower >= 1000 mg)

### 7.3 NLP Drug Label Mining

The `nlp_miner.py` adapts the CDC's Opioid_Involvement_NLP repository for DailyMed SPL (Structured Product Labeling) XML analysis. The CDC's original pipeline targets death certificate text; the adaptation extracted two portable components:

- **NegEx rules** — the negation detection algorithm that distinguishes "respiratory depression may occur" from "no respiratory depression was observed"
- **Opioid term mappings** — standardized opioid mention detection

For each of the 18 drugs successfully mined, the system:
1. Fetches the full SPL XML from DailyMed
2. Parses 9 sections by LOINC code (boxed warning, indications, dosage, warnings/precautions, adverse reactions, drug interactions, abuse/dependence, overdosage, clinical pharmacology)
3. Runs NegEx-based annotation on each section
4. Extracts structured data: boxed warning content, starting/max doses, respiratory depression frequency, benzodiazepine warnings, CYP enzyme interactions, DEA schedule, naloxone rescue dosing, REMS requirements

12 of 18 drugs have boxed warnings. A comparison matrix across all labels enables cross-drug safety comparison.

---

## 8. The Dashboard

The Streamlit dashboard runs standalone on port 8502 and provides five interactive pages:

```bash
streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
```

### 8.1 Drug Explorer

A deep-dive into individual opioid drugs. Search by name, ingredient, or RxCUI, then view:
- Identity card (name, schedule, category, RxCUI, active ingredients)
- Receptor binding affinity bar chart (mu/kappa/delta Ki values on log scale)
- Pharmacology metrics (potency vs morphine, half-life, molecular weight)
- Safety profile (danger level, therapeutic index, estimated lethal dose, LD50 table)
- FAERS consensus signals with PRR/ROR values
- NLP-mined label highlights (boxed warning, REMS, benzodiazepine warnings, CYP interactions)
- Related products containing the same opioid ingredient

### 8.2 Opioid Landscape

A bird's-eye view of the opioid landscape:
- Classification treemap (category → drugs, sized by FAERS report count)
- Potency comparison (horizontal bar chart ranked by mu Ki, morphine as reference)
- Danger matrix scatter plot (potency vs FAERS reports, bubble size = deaths)
- Three-waves timeline (CDC overdose deaths by opioid subtype)
- DEA schedule distribution donut chart

### 8.3 Geographic Intelligence

Epidemiological mapping adapted from `plotly/dash-opioid-epidemic-demo`:
- State choropleth with selectable metric (prescribing rate, death rate, pills per capita, risk score)
- State comparison bar charts
- Mortality timeline
- County-level detail panel

### 8.4 Signal Detection

FAERS pharmacovigilance signal exploration:
- Signal heatmap (drugs x reactions, colored by methods-flagging count)
- Signal detail panel with PRR, ROR, and EBGM values
- Top consensus signals table (sortable, ranked)

### 8.5 Watchdog Tools

Interactive tools powered by the OpioidWatchdog agent:
- **Dose Risk Calculator** — select an ingredient, enter a daily dose, see MME assessment with color-coded risk level, lethal dose proximity gauge, risk factors, and CDC-based recommendation
- **Danger Comparator** — pick two ingredients for side-by-side comparison of danger level, potency, receptor affinity, lethal dose, and therapeutic index
- **Intelligence Brief** — generate a comprehensive brief for any ingredient with expandable sections for "Why is this an opioid?", FAERS signals, and label warnings

### 8.6 Design

Dark navy base (`#0d1b2a` to `#1b2838`), teal/cyan accents (`#5eead4`) for headings and positive indicators, red (`#ef4444`) and amber (`#f59e0b`) for danger. All data is loaded once at startup via `@st.cache_data`. Missing data files show graceful "Data not available" messages instead of crashing.

---

## 9. The OpioidWatchdog Agent

The `OpioidWatchdog` class provides programmatic access to all Tier 1–3 intelligence. It auto-loads all data files and exposes 9 methods:

```python
from opioid_track.agents.opioid_watchdog import OpioidWatchdog
watchdog = OpioidWatchdog()
```

| Method | Returns | What It Does |
|--------|---------|--------------|
| `is_opioid_query("morphine")` | `bool` | Checks if a substance is a known opioid (not just present in a combo product — aspirin returns False even though aspirin/codeine exists) |
| `get_full_opioid_brief(rxcui)` | `dict` | Comprehensive brief: identity, pharmacology, safety, signals, label highlights, prescribing context |
| `answer_why_opioid("fentanyl")` | `str` | Explains opioid classification citing specific receptor Ki values |
| `compare_danger("fentanyl", "morphine")` | `str` | Side-by-side comparison with danger level, potency, lethal dose, therapeutic index, and a potency ratio conclusion |
| `get_signals_summary(rxcui)` | `str` | FAERS signal summary listing consensus signals with PRR/ROR/EBGM values |
| `get_label_warnings(rxcui)` | `str` | NLP-mined label warnings: boxed warning text, REMS status, drug interactions, overdose symptoms |
| `find_drugs_with_ingredient("codeine")` | `list[dict]` | All products in the registry containing a specific ingredient |
| `assess_dose_risk("oxycodone", 60)` | `dict` | Risk assessment: daily MME, lethal dose proximity, risk factors, and a recommendation (normal / caution / high risk) |
| `format_brief_text(rxcui)` | `str` | Plain-text intelligence brief suitable for chat interfaces or LLM context windows |

All text-returning methods cite specific numbers rather than giving vague answers. Missing data is reported explicitly (e.g., "LD50 data not available for codeine") rather than silently omitted.

---

## 10. Knowledge Chunks for RAG

The `knowledge_indexer.py` generates 55 text chunks optimized for Retrieval-Augmented Generation, stored as individual `.txt` files in `data/knowledge_chunks/` with a `manifest.json` index.

| Category | Count | Example Content |
|----------|-------|-----------------|
| Classification | 4 | Opioid categories, receptor system biology, DEA scheduling, full ingredient list |
| Pharmacology | 17 | One per ingredient: receptor affinities, potency, LD50, metabolism, half-life |
| Safety | 18 | One per NLP-mined drug: boxed warnings, REMS, interactions, overdosage |
| Epidemiology | 3 | Three waves timeline with CDC death counts, top prescribing states, top death-rate states |
| FAERS Signals | 13 | One per drug with consensus signals: reaction list with PRR/ROR/EBGM |

Target: ~500–600 tokens per chunk, ~16,500 tokens total. Framework-agnostic — works with LangChain, LlamaIndex, or any custom RAG pipeline.

---

## 11. All External Data Sources

### 11.1 GitHub Repositories (8 total)

| Repo | Tier | Purpose | License |
|------|------|---------|---------|
| [ripl-org/historical-ndc](https://github.com/ripl-org/historical-ndc) | 1 | Pre-classified NDC-to-opioid table (1998–2018, JAMIA 2020) | MIT |
| [jbadger3/ml_4_pheno_ooe](https://github.com/jbadger3/ml_4_pheno_ooe) | 1 | RxCUI→MME conversion mappings (peer-reviewed ML phenotyping) | MIT |
| [alipphardt/cdc-wonder-api](https://github.com/alipphardt/cdc-wonder-api) | 2 | CDC WONDER programmatic API client | — |
| [marc-rauckhorst/arcos-py](https://github.com/marc-rauckhorst/arcos-py) | 2 | ARCOS WaPo API wrapper (fallback, API is offline) | — |
| [ChapatiDB/faerslib](https://github.com/ChapatiDB/faerslib) | 2 | PRR/ROR/MGPS signal detection reference (math ported, not DB) | — |
| [CDCgov/Opioid_Involvement_NLP](https://github.com/CDCgov/Opioid_Involvement_NLP) | 3 | NLP negation detection (NegEx rules adapted for SPL labels) | — |
| [plotly/dash-opioid-epidemic-demo](https://github.com/plotly/dash-opioid-epidemic-demo) | 3 | Choropleth map and chart patterns (ported to Streamlit) | MIT |
| [opioiddatalab/overdosedata](https://github.com/opioiddatalab/overdosedata) | 3 | Dashboard design reference (read-only) | — |

### 11.2 Public APIs (no authentication required)

| API | Tier | Endpoints Used |
|-----|------|---------------|
| NLM RxClass | 1 | Drug enumeration by ATC, MED-RT, FDA EPC |
| NLM RxNorm | 1 | Ingredient resolution, NDC lookups |
| OpenFDA FAERS | 1, 2 | Adverse event baselines, signal detection contingency tables |
| OpenFDA NDC | 1, 1.5 | Post-2018 NDC classification, real-time sync |
| OpenFDA Labels | 1 | SPL Set ID and UNII lookups |
| CMS Data API v1 | 2 | Medicare Part D prescribing (geographic + provider-drug) |
| CMS Medicaid SDUD | 2 | Medicaid opioid prescribing rates |
| CDC VSRR (Socrata) | 2 | Provisional overdose death data |
| US Census ACS | 2 | County-level population estimates |
| ChEMBL | 3 | Bioactivity data (Ki, IC50, EC50) and mechanism of action |
| GtoPdb | 3 | Curated ligand-receptor interactions |
| PubChem PUG REST | 3 | Chemical properties, pharmacokinetics, LD50 data |
| DailyMed | 3 | SPL XML drug labels |

---

## 12. Full Directory Structure

```
opioid_track/
├── __init__.py
├── config.py                              # Central configuration (all tiers)
├── README.md
├── requirements.txt
├── TIER3_BUILD_TRACKER.md                 # Build progress tracker
│
├── vendor/                                # Cloned GitHub repositories
│   ├── cdc-wonder-api/                    #   Tier 2: alipphardt/cdc-wonder-api
│   ├── Opioid_Involvement_NLP/            #   Tier 3: CDCgov/Opioid_Involvement_NLP
│   ├── dash-opioid-epidemic-demo/         #   Tier 3: plotly/dash-opioid-epidemic-demo
│   └── overdosedata/                      #   Tier 3: opioiddatalab/overdosedata
│
├── ingestion/                             # Data fetching scripts
│   ├── __init__.py                        #   Shared retry_get utility
│   ├── rxclass_opioid_fetcher.py          #   Tier 1: RxClass API enumeration
│   ├── ndc_opioid_classifier.py           #   Tier 1: NDC classification
│   ├── mme_mapper.py                      #   Tier 1: MME factor mapping
│   ├── faers_opioid_filter.py             #   Tier 1: FAERS baseline
│   ├── realtime_ndc_sync.py               #   Tier 1.5: Post-2018 NDC sync
│   ├── cms_opioid_fetcher.py              #   Tier 2: CMS Medicare Part D
│   ├── cdc_mortality_fetcher.py           #   Tier 2: CDC VSRR mortality
│   ├── medicaid_opioid_fetcher.py         #   Tier 2: Medicaid supply chain
│   ├── pharmacology_fetcher.py            #   Tier 3: ChEMBL + GtoPdb + PubChem
│   └── toxicology_fetcher.py              #   Tier 3: LD50 + danger ranking
│
├── core/                                  # Data processing and analysis
│   ├── __init__.py
│   ├── registry_builder.py                #   Tier 1: Merges all ingestion outputs
│   ├── registry.py                        #   Tier 1: Runtime API (13 functions)
│   ├── signal_detector.py                 #   Tier 2: PRR/ROR/MGPS signal detection
│   ├── geographic_joiner.py               #   Tier 2: County-level risk profiles
│   ├── nlp_miner.py                       #   Tier 3: DailyMed SPL label mining
│   └── knowledge_indexer.py               #   Tier 3: RAG chunk generator
│
├── agents/
│   ├── __init__.py
│   └── opioid_watchdog.py                 #   Tier 3: Intelligence agent
│
├── dashboard/                             # Standalone Streamlit app
│   ├── __init__.py
│   ├── opioid_app.py                      #   Main entry point (port 8502)
│   ├── components/
│   │   ├── __init__.py
│   │   └── charts.py                      #   8 reusable Plotly chart builders
│   └── pages/
│       ├── __init__.py
│       ├── drug_explorer.py               #   Drug deep-dive
│       ├── landscape.py                   #   Classification and potency overview
│       ├── geography.py                   #   Epidemiological mapping
│       ├── signals.py                     #   FAERS signal exploration
│       └── watchdog.py                    #   Interactive watchdog tools
│
├── data/                                  # All generated data (committed to git)
│   ├── raw/
│   │   ├── ndc-opioids.csv                #   from ripl-org/historical-ndc
│   │   └── rxcui_mme_mapping.json         #   from jbadger3/ml_4_pheno_ooe
│   ├── opioid_registry.json               #   Tier 1: Canonical registry
│   ├── rxclass_opioid_enumeration.json
│   ├── ndc_opioid_lookup.json
│   ├── mme_reference.json
│   ├── faers_opioid_queries.json
│   ├── realtime_ndc_opioids.json          #   Tier 1.5
│   ├── opioid_prescribing.json            #   Tier 2: CMS data
│   ├── opioid_mortality.json              #   Tier 2: CDC data
│   ├── opioid_supply_chain.json           #   Tier 2: Medicaid data
│   ├── faers_signal_results.json          #   Tier 2: Signal detection
│   ├── faers_signal_cache.json
│   ├── opioid_geographic_profiles.json    #   Tier 2: County risk profiles
│   ├── opioid_pharmacology.json           #   Tier 3: Receptor + toxicology
│   ├── opioid_nlp_insights.json           #   Tier 3: NLP label mining
│   └── knowledge_chunks/                  #   Tier 3: RAG chunks
│       ├── manifest.json
│       └── *.txt (55 files)
│
├── tests/
│   ├── __init__.py
│   ├── test_registry.py                   #   Tier 1: 23 tests
│   ├── test_signal_detector.py            #   Tier 2: 4 tests
│   ├── test_geographic_joiner.py          #   Tier 2: 3 tests
│   └── test_pharmacology.py              #   Tier 3: 8 tests
│
└── docs/
    ├── DEV_LOG_TIER1.md
    ├── DEV_LOG_TIER1_5.md
    ├── DEV_LOG_TIER2.md
    ├── DEV_LOG_TIER3.md
    ├── TECHNICAL_TIER1.md
    ├── TECHNICAL_TIER1_5.md
    ├── TECHNICAL_TIER2.md
    ├── TECHNICAL_TIER3.md
    ├── OPIOID_TRACK_COMPLETE.md           # This document
    ├── TIER1_INSTRUCTIONS_REVISED.md
    ├── TIER2_INSTRUCTIONS_REVISED.md
    ├── TIER3_INSTRUCTIONS_REVISED.md
    └── TIER3_IMPLEMENTATION_PLAN.md
```

---

## 13. How to Run Everything

### 13.1 Prerequisites

```bash
cd TruPharma-Clinical-Intelligence
pip install -r opioid_track/requirements.txt
```

### 13.2 Clone Vendor Repos

```bash
git clone https://github.com/CDCgov/Opioid_Involvement_NLP.git opioid_track/vendor/Opioid_Involvement_NLP
git clone https://github.com/plotly/dash-opioid-epidemic-demo.git opioid_track/vendor/dash-opioid-epidemic-demo
git clone https://github.com/opioiddatalab/overdosedata.git opioid_track/vendor/overdosedata
```

### 13.3 Run Ingestion Pipelines

```bash
# Tier 1: Build opioid registry
python3 -m opioid_track.ingestion.rxclass_opioid_fetcher
python3 -m opioid_track.ingestion.ndc_opioid_classifier
python3 -m opioid_track.ingestion.mme_mapper
python3 -m opioid_track.ingestion.faers_opioid_filter
python3 -m opioid_track.core.registry_builder

# Tier 2: External data + signal detection
python3 -m opioid_track.ingestion.cms_opioid_fetcher
python3 -m opioid_track.ingestion.cdc_mortality_fetcher
python3 -m opioid_track.ingestion.medicaid_opioid_fetcher
python3 -m opioid_track.core.signal_detector
python3 -m opioid_track.core.geographic_joiner

# Tier 3: Pharmacology + NLP + knowledge chunks
python3 -m opioid_track.ingestion.pharmacology_fetcher    # ~2 min
python3 -m opioid_track.ingestion.toxicology_fetcher
python3 -m opioid_track.core.nlp_miner
python3 -m opioid_track.core.knowledge_indexer
```

### 13.4 Run Tests

```bash
pytest opioid_track/tests/ -v   # 38 tests
```

### 13.5 Launch Dashboard

```bash
streamlit run opioid_track/dashboard/opioid_app.py --server.port 8502
```

### 13.6 Use the Agent

```python
from opioid_track.agents.opioid_watchdog import OpioidWatchdog

watchdog = OpioidWatchdog()
watchdog.answer_why_opioid("fentanyl")
watchdog.compare_danger("fentanyl", "morphine")
watchdog.assess_dose_risk("oxycodone", 60)
```

---

## 14. Testing and Validation

### 14.1 Test Suite Summary

| Test File | Tier | Tests | What It Validates |
|-----------|------|-------|-------------------|
| `test_registry.py` | 1 + 1.5 | 23 | Registry loads, is_opioid, MME factors, daily MME calculation, NDC normalization, data provenance, FAERS baseline, product search, new approvals |
| `test_signal_detector.py` | 2 | 4 | FAERS client init, signal structure, source library field, cache file |
| `test_geographic_joiner.py` | 2 | 3 | Risk tier boundaries, missing data handling, output JSON integrity |
| `test_pharmacology.py` | 3 | 8 | Pharmacology data loads, morphine mu receptor Ki, morphine potency = 1.0, ≥10 ingredients with receptor data, ≥10 with explanations, ≥5 with LD50, NLP CDCgov attribution, vendor repos present |
| **Total** | | **38** | **All passing** |

### 14.2 Validation Thresholds

| Metric | Threshold | Actual |
|--------|-----------|--------|
| Opioid RxCUIs | ≥ 200 | 1,236 |
| NDC codes | ≥ 2,000 | 197,043 |
| Must-include opioids | 14/14 | 14/14 |
| FAERS consensus signals | ≥ 50 | 204 |
| County risk profiles | ≥ 1,000 | 3,148 |
| Ingredients with receptor data | ≥ 10 | 16 |
| NLP drugs mined | ≥ 10 | 18 |
| Knowledge chunks | ≥ 50 | 55 |
| Dashboard pages rendering | 5/5 | 5/5 |
| Existing TruPharma files modified | 0 | 0 |

---

## 15. Known Limitations and Blockers Resolved

### 15.1 Blockers Encountered and Resolved

| Blocker | Impact | Resolution |
|---------|--------|------------|
| WaPo ARCOS API offline | No DEA supply chain data | Pivoted to CMS Medicaid Opioid Prescribing Rates as proxy |
| faerslib requires 100GB+ SQLite DB | Cannot use faerslib as intended | Ported PRR/ROR/EBGM math directly; built 2x2 tables from live OpenFDA API |
| CMS Socrata API retired (410 Gone) | Cannot fetch prescribing data | Discovered new `data-api/v1` UUIDs via `data.cms.gov/data.json` catalog |
| ChEMBL bulk receptor queries timeout (10+ min) | Cannot fetch pharmacology data | Rewrote to per-compound queries (~2 min total) |
| CDC NLP repo targets death certificates, not labels | Cannot use pipeline directly | Extracted portable NegEx rules and term mappings; applied to SPL text |

### 15.2 Data Gaps

| Gap | Detail |
|-----|--------|
| PubChem LD50 | 11 of 17 ingredients have no LD50 in PubChem's Toxicity section (codeine, oxycodone, buprenorphine, etc.) |
| Meperidine in ChEMBL | Indexed as "pethidine"; no hits under "meperidine" |
| ARCOS temporal coverage | Only 2006–2014 publicly available (now moot since API is offline) |
| CDC VSRR data | Provisional — subject to 5–10% revision |
| CMS data lag | Medicare Part D data typically 1–2 years behind |
| Census population | Uses 2020 ACS; may not reflect recent demographic shifts |
| OpenFDA Label 404s | Labels are product-level, not ingredient-level; some RxCUIs return 404 |

### 15.3 Possible Future Enhancements

- Integrate PyTDC for additional LD50 data sources
- Add county-level choropleth (currently state-level in the dashboard)
- Connect OpioidWatchdog to main TruPharma RAG pipeline
- Add temporal trend analysis to the Watchdog Tools page
- Real-time FAERS signal monitoring (periodic re-run)
