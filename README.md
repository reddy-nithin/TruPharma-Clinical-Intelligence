# TruPharma Clinical Intelligence

> **AI-Powered Drug Safety & Pharmacovigilance Platform**

**Team:** Salman Mirza, Amy Ngo, Nithin Songala

---

## Overview

TruPharma Clinical Intelligence is an AI-powered platform for drug safety analysis. It bridges the gap between official FDA drug labels and real-world patient evidence by combining a **Hybrid RAG pipeline**, a **biomedical Knowledge Graph**, and **pharmacovigilance signal detection**. The system delivers grounded, citation-backed answers for drug safety queries while surfacing emerging adverse event signals that diverge from official labeling.

### Target Users

| Persona | Example Task |
|---------|-------------|
| **Pharmacist** | "What are the dosage warnings and interactions for metformin?" |
| **Clinician** | "What drug interactions should I know about for warfarin?" |
| **Patient** | "What are the co-reported adverse events for prednisone?" |
| **Pharmacovigilance Analyst** | Explore FAERS signal heatmaps and label-vs-reality disparity |
| **Opioid Researcher** | Compare opioid pharmacology, demographics, and geographic prescribing patterns |

### Value Proposition

- **Faster time-to-answer** with **higher trust**: grounded answers with inline citations from FDA label evidence and real-world FAERS data
- **Knowledge Graph reasoning**: drug-ingredient-reaction network enabling multi-hop inference
- **Emerging signal detection**: surfaces FAERS adverse events not yet reflected in official labels
- **Dual interfaces**: conversational Safety Chat for point-of-care queries and an Opioid Intelligence Track for population-level analysis

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Streamlit UI (Multi-Page Frontend)                 │
│   Safety Chat  ·  Opioid Dashboard  ·  Stress Test  ·  Signal Heatmap│
└────────────┬────────────────────────┬────────────────────────────────┘
             │                        │
             ▼                        ▼
┌────────────────────────┐  ┌─────────────────────────────────────────┐
│   RAG Engine           │  │   Opioid Intelligence Track             │
│   src/rag/engine.py    │  │   opioid_track/ pipeline                │
│                        │  │                                         │
│  1. Query analysis     │  │  • Drug registry (RxNorm/NDC)           │
│     (entity + intent)  │  │  • Pharmacology & MME calculations      │
│  2. Pinecone cache     │  │  • FAERS signal detection               │
│     (24h TTL) or       │  │  • Geographic prescribing patterns      │
│     openFDA fetch      │  │  • Demographic analysis                 │
│  3. Vertex AI embed    │  │  • Watchdog agent (dose risk, compar.)  │
│     (text-embedding-   │  └──────────────────────┬──────────────────┘
│      004, 768-dim)     │                         │
│  4. Hybrid retrieval   │                         │
│     FAISS + BM25 +     │                         │
│     KG-aware boost     │                         │
│  5. Graph enrichment   │                         │
│     (KG context block) │                         │
│  6. Gemini 2.0 Flash   │                         │
│     answer generation  │                         │
│  7. CSV logging        │                         │
└────────┬───────────────┘                         │
         │                                         │
         ▼                                         │
┌─────────────────────────────────────────────────┐│
│           Biomedical Knowledge Graph            ││
│           data/kg/trupharma_kg.db (SQLite)      ││
│           or Neo4j Aura Free (cloud)            ││
│                                                 ││
│  Nodes: Drug · Ingredient · Reaction ·          ││
│         Product · DrugAlias                     ││
│  Edges: HAS_ACTIVE_INGREDIENT                   ││
│         INTERACTS_WITH (FDA label + Gemini)     ││
│         CO_REPORTED_WITH (FAERS)                ││
│         DRUG_CAUSES_REACTION (FAERS)            ││
│         LABEL_WARNS_REACTION (FDA label)        ││
│         HAS_PRODUCT (NDC)                       ││
│  Dynamic expansion: Phase 1 (2–5s) +           ││
│                     Phase 2 (background thread) ││
└─────────────────────────────────────────────────┘│
         │                                         │
         ▼                                         ▼
┌──────────────────┐  ┌───────────────┐  ┌────────────────┐
│  openFDA APIs    │  │ Google Vertex │  │ Pinecone /     │
│  /drug/label/    │  │ AI            │  │ FAISS          │
│  /drug/event/    │  │ text-embed-   │  │ Vector Store   │
│  /drug/ndc/      │  │ ding-004      │  │ (24h TTL)      │
│  RxNorm API      │  │ Gemini 2.0    │  └────────────────┘
└──────────────────┘  └───────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│               logs/product_metrics.csv                    │
│  timestamp · query · latency · evidence_ids · confidence  │
└──────────────────────────────────────────────────────────┘
```

### Data Flow — Safety Chat

1. User enters a drug-safety question via the conversational chat interface
2. `query_analyzer.py` extracts drug entities and intent (safety_check / interaction / comparison / general)
3. Pinecone is checked for a cached vector index (24h TTL); if stale, openFDA APIs are fetched
4. Text is chunked and embedded with Vertex AI `text-embedding-004` (768-dim; TF-IDF fallback)
5. Top-K evidence is retrieved via hybrid fusion (FAISS dense + BM25 sparse + KG-entity boost)
6. Knowledge Graph context is assembled: ingredients, interactions, FAERS reactions, disparity score
7. Gemini 2.0 Flash generates a citation-enforced answer using KG context + evidence + conversation history
8. The interaction is logged to `logs/product_metrics.csv`
9. Results displayed: conversational answer with inline citation pills, source badges, KG network graph, body-map symptom visualization, patient risk assessment, and query metrics

### Key Upgrade Areas

| Area | Upgrade |
|------|---------|
| **Embeddings** | Vertex AI `text-embedding-004` (768-dim) replacing SentenceTransformer |
| **Vector Store** | Pinecone cloud (with FAISS local fallback), 24h TTL caching |
| **Knowledge Graph** | Multi-type node/edge graph (Drug·Ingredient·Reaction·Product), Many-to-many, Dynamic build |
| **Graph Backend** | SQLite (default) + Neo4j Aura Free (optional cloud backend) |
| **Chat UI** | Perplexity-style `st.chat_input()` with conversation history (last 5 turns) |
| **GraphRAG** | Query entity/intent extraction, KG-aware relevance boost (+0.15) |
| **Body Map** | 3D GLB model with symptom-to-body-region hotspot visualization |
| **Risk Assessment** | Patient-specific risk calculator (age group, organ function, glucose status) |
| **Opioid Track** | Full Tier 3 intelligence module: pharmacology, demographics, geography, signals, watchdog |
| **FAERS Integration** | Real-time adverse event signals, co-reported drug analysis, label disparity scoring |
| **NDC + RxNorm** | Brand→generic resolution, product metadata, active ingredient lookup |

---

## Deployed Application

**Live App:** https://trupharma-clinical-intelligence-fhu8qhqrgjch9yhocjaeuz.streamlit.app/

---

## Setup & Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/reddy-nithin/TruPharma-Clinical-Intelligence
cd TruPharma-Clinical-Intelligence

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables (copy and edit)
cp .env.example .env
# Set GEMINI_API_KEY (required for LLM answers)
# Set GCP_PROJECT_ID + GOOGLE_APPLICATION_CREDENTIALS (for Vertex AI embeddings)
# Set PINECONE_API_KEY + PINECONE_INDEX_NAME (for cloud vector store)
# Set NEO4J_URI + NEO4J_USER + NEO4J_PASSWORD (for Neo4j KG backend, optional)

# 5. Build the knowledge graph (SQLite, ~200 drugs)
python scripts/build_kg.py --max-drugs 200

# 6. Run the Streamlit app
streamlit run src/frontend/app.py
```

### Optional: Neo4j Aura Free (Cloud KG Backend)

To use Neo4j Aura Free instead of the default SQLite knowledge graph:

1. Create a free instance at [console.neo4j.io](https://console.neo4j.io)
2. Add credentials to `.env`: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
3. Migrate existing SQLite data: `python scripts/migrate_sqlite_to_neo4j.py`

The `create_backend()` factory auto-detects Neo4j when `NEO4J_URI` is set and falls back to SQLite otherwise.

### Optional: Vertex AI Embeddings

1. Set up a Google Cloud project and enable the Vertex AI API
2. Create a service account and download the JSON key
3. Set `GCP_PROJECT_ID` and `GOOGLE_APPLICATION_CREDENTIALS` in `.env`

TF-IDF embeddings are used automatically when Vertex AI credentials are not configured.

### Optional: Pinecone Vector Store

1. Create a free Pinecone account at [pinecone.io](https://pinecone.io)
2. Create an index and add `PINECONE_API_KEY` + `PINECONE_INDEX_NAME` to `.env`

FAISS (local, in-memory) is used automatically when Pinecone is not configured.

---

## Application Modules

### Safety Chat (`src/frontend/pages/primary_demo.py`)

Conversational drug-safety Q&A with:
- **Inline citations** — numbered pill superscripts linking to evidence sources
- **Source badges** — FDA Label, FAERS, Knowledge Graph
- **KG panel** — interactive vis.js network graph (drugs, ingredients, reactions, interactions)
- **Evidence panel** — ranked evidence chunks with field labels and relevance scores
- **Body map** — 3D anatomical model with symptom hotspot overlay
- **Metrics panel** — per-query latency, confidence, retrieval method, LLM usage
- **Risk calculator** — patient-specific risk score based on age, organ function, and known interactions
- **Query history** — sidebar quick-access to recent queries

### Opioid Intelligence Track (`src/frontend/pages/opioid_dashboard.py`)

Tier 3 deep-intelligence module covering:
- **Drug Explorer** — ingredient pharmacology, MME conversions, sensitivity rankings
- **Opioid Landscape** — prescribing trends, three-wave epidemiology overview
- **Geographic Intelligence** — state-level prescribing and mortality maps
- **Demographics** — age, sex, and race breakdowns of adverse event reporters
- **Signal Detection** — FAERS consensus signals, PRR/ROR scoring
- **Watchdog Tools** — dose risk calculator, ingredient danger comparator, intelligence brief

### Stress Test (`src/frontend/pages/stress_test.py`)

Edge-case scenario validation:
- Rare input, large document, high-traffic, and conflicting-evidence scenarios
- Side-by-side comparison of normal vs. stress-condition RAG behavior

---

## Knowledge Graph

The biomedical KG is built on-demand and stored in `data/kg/trupharma_kg.db` (SQLite default).

### Node Types

| Type | Description |
|------|-------------|
| **Drug** | Pharmaceutical compound (RxCUI-resolved) |
| **Ingredient** | Active ingredient (NDC-sourced) |
| **Reaction** | Adverse event term (MedDRA via FAERS) |
| **Product** | Commercial product (NDC code) |
| **DrugAlias** | Brand/generic name alias for resolution |

### Relationship Types

| Relationship | Source |
|-------------|--------|
| `HAS_ACTIVE_INGREDIENT` | OpenFDA NDC API |
| `INTERACTS_WITH` | FDA label + Gemini extraction |
| `CO_REPORTED_WITH` | OpenFDA FAERS |
| `DRUG_CAUSES_REACTION` | OpenFDA FAERS |
| `LABEL_WARNS_REACTION` | FDA drug label |
| `HAS_PRODUCT` | OpenFDA NDC API |

### Dynamic Build (Progressive Loading)

| Phase | Scope | Latency |
|-------|-------|---------|
| **Phase 1** (synchronous) | RxNorm node + NDC ingredients + top 10 FAERS reactions | 2–5 s |
| **Phase 2** (background thread) | Full FAERS co-reported drugs + label interactions + label reaction warnings | 20–60 s |

---

## Logging & Monitoring

All query interactions are logged to `logs/product_metrics.csv`:

| Column | Description |
|--------|-------------|
| `timestamp` | UTC timestamp of the query |
| `query` | User's question (truncated to 200 chars) |
| `latency_ms` | End-to-end pipeline latency in milliseconds |
| `evidence_ids` | Chunk IDs of retrieved evidence |
| `confidence` | Heuristic confidence score (0–1) |
| `num_evidence` | Number of evidence items returned |
| `num_records` | Drug label records fetched from FDA API |
| `retrieval_method` | hybrid / dense / sparse |
| `llm_used` | Whether Gemini LLM was used |
| `answer_preview` | First 150 chars of the generated answer |

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Recommended | Google Gemini API key for LLM answer generation |
| `GCP_PROJECT_ID` | Optional | Google Cloud project for Vertex AI embeddings |
| `GCP_LOCATION` | Optional | Vertex AI region (default: `us-central1`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional | Path to GCP service account JSON |
| `PINECONE_API_KEY` | Optional | Pinecone API key for cloud vector store |
| `PINECONE_INDEX_NAME` | Optional | Pinecone index name |
| `NEO4J_URI` | Optional | Neo4j Aura connection URI |
| `NEO4J_USER` | Optional | Neo4j username (default: `neo4j`) |
| `NEO4J_PASSWORD` | Optional | Neo4j password |
| `NEO4J_DATABASE` | Optional | Neo4j database name (default: `neo4j`) |

See `.env.example` for a complete template.

---

## Production Failure Scenarios & Mitigations

| Scenario | Mitigation |
|----------|-----------|
| openFDA returns 0 results | Returns "Not enough evidence" message; query logged for analysis |
| Vertex AI unavailable | Automatic TF-IDF fallback for embeddings |
| Pinecone unavailable | Automatic FAISS (in-memory) fallback |
| Neo4j unavailable | Automatic SQLite KG fallback |
| KG not yet built for drug | Progressive loading triggered automatically via `expand_drug_async()` |
| Gemini API key missing | Extractive fallback answer generated from top evidence chunk |

---

## Deployment & Scaling

| Aspect | Approach |
|--------|----------|
| **Hosting** | Streamlit Community Cloud (free tier) |
| **Embeddings** | Vertex AI `text-embedding-004` (cloud); TF-IDF fallback (local) |
| **Vector Store** | Pinecone (cloud, 24h TTL); FAISS (local fallback) |
| **Knowledge Graph** | Neo4j Aura Free (cloud, optional); SQLite (local default) |
| **LLM** | Google Gemini 2.0 Flash via `google-genai`; extractive fallback |
| **Monitoring** | CSV-based logging; extend to cloud logging for production |
| **CI/CD** | GitHub integration with Streamlit Cloud for auto-deploy on push |

---

## Repository Structure

```
TruPharma-Clinical-Intelligence/
├── data/
│   └── kg/
│       └── trupharma_kg.db        # SQLite knowledge graph database
├── docs/
│   ├── KNOWLEDGE_GRAPH_UPGRADE.md # KG upgrade documentation
│   ├── UPGRADE_DEV_LOG.md         # Vertex AI + Pinecone + Chat UI upgrade log
│   ├── TruPharma_Technical_Architecture_Guide.md
│   └── screenshots/               # App screenshots
├── logs/
│   └── product_metrics.csv        # Query interaction logs
├── opioid_track/                  # Tier 3 Opioid Intelligence module
│   ├── agents/
│   │   └── opioid_watchdog.py     # Dose risk, danger comparator, intelligence brief
│   ├── core/                      # Registry, signal detection, NLP, demographics
│   └── dashboard/
│       └── pages/                 # Drug Explorer, Landscape, Geography, Demographics, Signals, Watchdog
├── scripts/
│   ├── build_kg.py                # Build/expand the knowledge graph
│   └── migrate_sqlite_to_neo4j.py # Migrate SQLite KG to Neo4j Aura
├── src/
│   ├── config.py                  # Vertex AI initialization (shared)
│   ├── frontend/
│   │   ├── app.py                 # Landing page (Home)
│   │   ├── theme.py               # Design system (dark theme tokens)
│   │   └── pages/
│   │       ├── primary_demo.py    # Safety Chat (conversational RAG)
│   │       ├── opioid_dashboard.py# Opioid Intelligence Track
│   │       ├── signal_heatmap.py  # Signal Heatmap Dashboard
│   │       └── stress_test.py     # Edge-case scenario validation
│   ├── ingestion/
│   │   ├── openfda_client.py      # openFDA API client (labels, FAERS, NDC)
│   │   ├── faers.py               # FAERS adverse event ingestion
│   │   ├── ndc.py                 # NDC product metadata ingestion
│   │   ├── rxnorm.py              # RxNorm entity resolution
│   │   ├── vector_store.py        # VectorStore protocol (Pinecone + FAISS)
│   │   └── vertex_embeddings.py   # Vertex AI text-embedding-004 wrapper
│   ├── kg/
│   │   ├── backend.py             # KG backend factory (SQLite / Neo4j)
│   │   ├── dynamic_builder.py     # Progressive drug expansion (Phase 1 + Phase 2)
│   │   ├── loader.py              # KG query interface
│   │   ├── schema.py              # Node/edge data models
│   │   └── builders/              # Edge builders (FAERS, NDC, labels, RxNorm)
│   └── rag/
│       ├── engine.py              # RAG pipeline: query → embed → retrieve → generate → log
│       ├── query_analyzer.py      # LLM-based entity/intent extraction
│       ├── graph_enrichment.py    # KG context assembly for LLM prompt
│       └── drug_profile.py        # Unified drug profile model
├── .env.example                   # Environment variable template
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Container definition
└── requirements.txt
```

---

## Impact Evaluation

- **Workflow improvement:** Reduces manual label scanning from 10–15 min to under 30 sec per question
- **Time-to-decision:** Estimated 80% reduction in time-to-answer for drug-label queries
- **Trust indicators:** Every answer includes evidence chunk IDs, source field labels, and confidence scores; system refuses to answer when evidence is insufficient
- **Real-world signal coverage:** FAERS adverse event data surfaces emerging risks not yet on the official label, closing the label-vs-reality gap
- **Scalability:** Graceful degradation across all optional services (Vertex AI → TF-IDF, Pinecone → FAISS, Neo4j → SQLite)

---

*TruPharma Clinical Intelligence · CS 5588 · Spring 2026*
