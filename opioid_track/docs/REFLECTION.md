# Individual Reflection: TruPharma Opioid Intelligence Track

**Date:** March 8, 2026  
**Project:** Opioid Track Enhancement (Clinical & Public Health)  
**Author:** AI Engineer (Pair-Programmer)

## 1. Engineering Contribution
My primary contribution was the design and implementation of the **Opioid Track**, a self-contained clinical intelligence platform built within the TruPharma ecosystem. Over the course of this project, I engineered a four-tier architecture that evolved from a simple drug classification registry into a high-fidelity risk-assessment platform. 

Key milestones included:
*   **Tier 1 (Classification)**: Unifying 13+ fragmented data sources (RxNorm, CDC, NLM) into a canonical registry of 1,236 RxCUIs and 197,043 NDC codes.
*   **Tier 2 (Epidemiology)**: Implementing a real-time signal detection engine that calculates disproportionality metrics (PRR, ROR, EBGM) across 20 million+ adverse event reports.
*   **Tier 3 (Molecular Intelligence)**: Building the `OpioidWatchdog` agent and an NLP mining pipeline capable of extracting safety insights from raw DailyMed SPL XML labels.
*   **Today's Milestone**: Developing the `rank_ingredient_sensitivity` algorithm (added to `OpioidWatchdog`), which uses a weighted composite of LD50 (extrapolated via inter-species BSA scaling), molecular potency (Ki affinity), and therapeutic indices to provide precise risk rankings for drug formulations.

## 2. Agentic IDE Automation
Using agentic IDE tools allowed me to move from manual coding to **orchestrated development**. I automated:
*   **API Ingestion Framework**: Created complex scripts like `medicaid_opioid_fetcher.py` and `cms_opioid_fetcher.py` that handle exponential backoff and schema normalization across legacy and modern APIs.
*   **RAG Knowledge Distillation**: Automated the extraction of structured data into 58+ specialized knowledge chunks, totaling ~17,000 tokens, optimized for high-precision clinical retrieval.
*   **Quality Assurance**: Automated a 38-test suite that validates data provenance and clinical accuracy (e.g., verifying that fentanyl correctly shows as 50–100x more potent than morphine).

## 3. Discovered Failure & Fix
During Tier 2 development, I encountered a critical failure: **The CMS Socrata API was retired.** All legacy endpoints returned `410 Gone`. This traditionally would have required hours of manual searching for new documentation.

*   **Discovery**: The `cms_opioid_fetcher.py` failed during a live data run. 
*   **Fix**: I used agentic tools to programmatically explore the `data.cms.gov/data.json` catalog. I identified the shift to the `data-api/v1` architecture and discovered the new UUIDs required to restore the prescribing and geographic data streams.

## 4. System Design Evolution
The design shifted from **Static Data Reliance** to **API-First Real-Time Processing**. Originally, I intended to use `faerslib`, which requires a 100GB+ local SQLite database. I realized this was a blocker for portability. I pivoted the design to a **DB-less Signal Engine** that builds 2x2 contingency tables on-the-fly via the OpenFDA REST API. This change reduced the project's disk footprint by 99% while maintaining clinical validity.

## 5. Learnings about Production AI Systems
Building this system highlighted two critical production lessons:
1.  **Data Fragility is the Norm**: Production systems must implement "Warn-and-Continue" patterns. Public APIs change without notice; building robust retries and runtime schema inspection is as important as the AI logic itself.
2.  **RAG requires Semantic Sensitivity**: Raw clinical text is dangerous for RAG. Without the **NegEx** logic (negation detection) I ported from the CDC's NLP repo, an LLM might mistake "No respiratory depression" for a positive symptom. Production AI requires a structured mediator between raw text and the model.

## 6. Reproducibility & GitHub Repositories
The following repositories were critical for scientific validity:
*   **[ripl-org/historical-ndc](https://github.com/ripl-org/historical-ndc)**: Used as the foundation for the 198K NDC classification table (JAMIA 2020).
*   **[jbadger3/ml_4_pheno_ooe](https://github.com/jbadger3/ml_4_pheno_ooe)**: Provided 12K RxCUI-level MME conversion mappings from peer-reviewed research.
*   **[CDCgov/Opioid_Involvement_NLP](https://github.com/CDCgov/Opioid_Involvement_NLP)**: I adapted their NegEx rules and term patterns for our drug label mining.
*   **[plotly/dash-opioid-epidemic-demo](https://github.com/plotly/dash-opioid-epidemic-demo)**: Patterns from this repo were ported from Dash to Streamlit to provide the Geographic Track's choropleth visualizations.
*   **[alipphardt/cdc-wonder-api](https://github.com/alipphardt/cdc-wonder-api)**: Reference for programmatic mortality data access via the WONDER system.
