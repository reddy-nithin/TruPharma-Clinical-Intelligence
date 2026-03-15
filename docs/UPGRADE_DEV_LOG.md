# TruPharma Upgrade Dev Log: Vertex AI + Pinecone + Chat UI

## 2026-03-12 — Session 1: Full Upgrade Implementation

### Branch
`feature/vertex-pinecone-upgrade` (from `main`)

### Phase 1: Vertex AI Integration
- Created `src/config.py` — shared Vertex AI initialization (project, location, credentials from env/secrets)
- Created `src/ingestion/vertex_embeddings.py` — Vertex AI `text-embedding-004` wrapper (768-dim, batching, retry)
- Modified `src/ingestion/openfda_client.py` — replaced SentenceTransformer embedding with Vertex AI `embed_texts()`
- Modified `src/rag/engine.py` — updated `_embed_query()` and `_call_gemini()` to use vertexai SDK
- Modified `src/kg/builders/label_edges.py` — updated `_extract_via_gemini()` to use vertexai SDK
- Updated `requirements.txt` — added `google-cloud-aiplatform>=1.38.0`
- Updated `.env.example` — added `GCP_PROJECT_ID`, `GCP_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS`

**Decisions:**
- Kept TF-IDF fallback for when Vertex AI is unavailable (graceful degradation)
- Vertex AI init happens once at import time via `src/config.py`
- For Streamlit Cloud: reads service account JSON from `st.secrets` and writes to temp file

### Phase 2: Pinecone Integration
- Created `src/ingestion/vector_store.py` — VectorStore protocol with PineconeStore + FaissStore implementations
- Modified `src/rag/engine.py` — cache-aware query flow (check Pinecone first, skip API if fresh)
- Updated `requirements.txt` — added `pinecone-client>=3.0.0`
- Updated `.env.example` — added `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`

**Decisions:**
- Deterministic vector IDs: `{drug_name}_{field}_{chunk_index}`
- 24h TTL for cache freshness
- Delete-then-upsert strategy for drug data refresh
- Factory function: PineconeStore if `PINECONE_API_KEY` set, else FaissStore fallback

### Phase 3: Conversational Chat Interface
- Rewrote `src/frontend/pages/primary_demo.py` — replaced text_area+button with `st.chat_input()` + `st.chat_message()`
- Added conversation memory via `st.session_state.messages`
- Updated `_call_gemini()` in engine.py to accept conversation history
- Added source citation badges (FDA Label, FAERS, Knowledge Graph)
- Added safety disclaimer banner

**Decisions:**
- Last 5 messages passed as conversation context to Gemini
- Kept sidebar for advanced settings
- Expandable sections for evidence, KG data, metrics within each assistant message

### Phase 4: Improved GraphRAG Fusion
- Created `src/rag/query_analyzer.py` — LLM-based entity/intent extraction from queries
- Enhanced `src/rag/engine.py` — structured context assembly, KG-aware relevance boost
- Enhanced `src/rag/graph_enrichment.py` — improved context formatting

**Decisions:**
- No LLM-generated Cypher — deterministic KG methods only
- Intent categories: safety_check, interaction, comparison, general
- KG-aware boost: +0.15 score for chunks mentioning KG entities
- Structured prompt format with separate sections for KG facts, evidence, conversation history

### Test Results
- TBD (will be updated after verification runs)
