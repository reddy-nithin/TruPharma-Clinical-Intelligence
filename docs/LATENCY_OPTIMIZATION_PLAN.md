# TruPharma Latency Optimization Plan

## Context

The TruPharma chat app currently takes **4-12s best case** (Pinecone cache hit) and **20-30s+ worst case** (new drug, cache miss) per query. The main RAG pipeline (`run_rag_query()` in `engine.py`) is entirely sequential, creates fresh API clients on every call, has a confirmed caching bug, and performs redundant work. There is no true LLM streaming — the UI fakes a typewriter effect after blocking for the full response.

---

## Tier 1: Quick Wins (3-8s savings, low risk)

### 1.1 Fix `_KG_LOADED` bug — KG re-initializes every call
- **File:** `src/kg/loader.py:335`
- **Bug:** `_KG_LOADED` is never set to `True` after successful load. The "fast path" at line 303 is never reached, so the SQLite backend is re-opened on every `load_kg()` call (called 4+ times per query).
- **Fix:** Add `_KG_LOADED = True` after line 335 (`_KG_INSTANCE = KnowledgeGraph(backend)`). Also add it after line 331 (path not found) and line 339 (exception) so failed loads aren't retried endlessly.

### 1.2 Singleton `genai.Client` — stop recreating per LLM call
- **Files:** `src/rag/engine.py:407-409,427-428`, `src/rag/query_analyzer.py:~83,~97`, `src/kg/builders/label_edges.py:~59,~71`
- **Problem:** `genai.Client(vertexai=True, ...)` instantiated on every LLM call (2+ per query). Each does gRPC channel setup + credential resolution.
- **Fix:** Create `src/clients.py` with a `get_gemini_client()` singleton. Replace all inline `genai.Client(...)` calls with it.

### 1.3 Singleton `TextEmbeddingModel`
- **File:** `src/ingestion/vertex_embeddings.py:60`
- **Problem:** `TextEmbeddingModel.from_pretrained("text-embedding-004")` loaded fresh every `embed_texts()` call.
- **Fix:** Module-level `_cached_model` singleton, loaded once on first call.

### 1.4 Singleton `PineconeStore`
- **File:** `src/rag/engine.py:~655`, `src/ingestion/vector_store.py`
- **Problem:** `create_vector_store()` creates a new `Pinecone()` client per query (network calls for `list_indexes()`, index connect).
- **Fix:** Add `get_vector_store()` to `src/clients.py`, cache the store instance.

### 1.5 Deduplicate `_drug_is_known()` double-call
- **File:** `src/rag/engine.py:579,605`
- **Problem:** Same function called twice with the same drug name. Each call hits KG + 1-2 RxNorm HTTP calls.
- **Fix:** Cache result from line 579 in a local variable. At line 605, only re-call if `drug_name` changed (via conversation history resolution at lines 582-588).

### 1.6 Remove redundant LLM retry
- **File:** `src/rag/engine.py:856-860`
- **Problem:** If `_call_gemini()` returns None, it's retried with identical args. `_call_gemini` already tries Vertex AI then direct API key, so the retry is guaranteed to fail again.
- **Fix:** Delete lines 856-860. The `_fallback_answer` at line 862 already handles this case.

---

## Tier 2: Streaming + Caching (5-15s perceived savings, moderate risk)

### 2.1 Real LLM streaming
- **Files:** `src/rag/engine.py`, `src/frontend/pages/primary_demo.py:~1719-1743`
- **Problem:** `_call_gemini()` uses `generate_content()` (blocking). UI fakes typewriter with `time.sleep(0.01)` per word after full response arrives.
- **Fix:**
  - Add `_call_gemini_stream()` using `generate_content_stream()` that yields text chunks
  - Refactor `run_rag_query()` into: `prepare_rag_query()` (steps 0-5) + streaming LLM call + `finalize_rag_query()` (post-processing)
  - Keep backward-compatible `run_rag_query()` wrapper
  - Update `primary_demo.py` to stream chunks directly into the UI via `st.empty()`, removing the fake typewriter loop

### 2.2 RxNorm HTTP response caching
- **File:** `src/ingestion/rxnorm.py`
- **Problem:** `resolve_drug_name()` makes 4-8 sequential uncached HTTP calls per drug. Same drug data re-fetched across queries.
- **Fix:** Add `@functools.lru_cache(maxsize=256)` to individual lookup functions: `get_rxcui_by_name`, `get_drug_info`, `get_approximate_match`, `get_spelling_suggestions`, `get_related_brands`, `get_generic_from_brand`.

### 2.3 Eliminate redundant KG enrichment
- **File:** `src/rag/engine.py:874-929`
- **Problem:** KG enrichment (interactions, reactions, co-reported) re-does lookups already performed by `get_kg_context_for_query()` at line 560.
- **Fix:** Pass `kg_ctx` dict from line 560 through to the enrichment step. Reuse existing data instead of re-querying.

---

## Tier 3: Pipeline Parallelization (2-5s savings, higher complexity)

### 3.1 Use LLM-extracted drug name
- **File:** `src/rag/engine.py:565-566`
- **Problem:** Drug name extracted twice — once by `analyze_query()` LLM call (line 557, returns `drugs` list) and once by `_extract_drug_name()` regex (line 566).
- **Fix:** Use `query_analysis["drugs"][0]` when available, falling back to `_extract_drug_name()`.

### 3.2 Parallel Pinecone check + openFDA fetch
- **File:** `src/rag/engine.py:~650-787`
- **Problem:** Sequential: check Pinecone cache (~0.5-1s) → on miss, fetch from openFDA (~2-5s).
- **Fix:** Use `ThreadPoolExecutor` to run both in parallel. If cache hits, discard the openFDA result.

### 3.3 Background Pinecone upsert
- **File:** `src/rag/engine.py:~760-786`
- **Problem:** Pinecone cache upsert is synchronous, blocking the response.
- **Fix:** Move upsert to a daemon thread. User doesn't need to wait for cache population.

---

## Implementation Order

| Step | Item | Time | Risk | Savings |
|------|------|------|------|---------|
| 1 | 1.1 Fix `_KG_LOADED` bug | 5 min | None | 0.1-0.5s |
| 2 | 1.6 Remove redundant retry | 2 min | None | 2-8s on failure |
| 3 | 1.2-1.4 Client singletons (`src/clients.py`) | 30 min | Low | 1-3s |
| 4 | 1.5 Deduplicate `_drug_is_known()` | 10 min | Low | 0.5-2s |
| 5 | 2.2 RxNorm LRU cache | 15 min | Low | 1-4s |
| 6 | 2.3 Eliminate redundant KG enrichment | 20 min | Low | 0.5-1s |
| 7 | 2.1 Real LLM streaming | 2-3 hrs | Moderate | 3-10s perceived |
| 8 | 3.3 Background Pinecone upsert | 15 min | Low | 0.5-1s |
| 9 | 3.1 Use LLM-extracted drug name | 10 min | Low | ~0.1s |
| 10 | 3.2 Parallel Pinecone/openFDA | 1 hr | Moderate | 1-3s |

## Expected Results

| Scenario | Current | After Tier 1 | After Tier 2 | After All |
|----------|---------|-------------|-------------|-----------|
| Cache hit | 4-12s | 2-5s | 1-3s (streaming) | 1-2s (streaming) |
| Cache miss | 20-30s+ | 12-20s | 8-15s (streaming) | 6-12s (streaming) |

## Verification

1. **Functional:** Run the app with `streamlit run src/frontend/app.py`, query known drugs (e.g., "metformin side effects") and new drugs to test both cache hit/miss paths
2. **Latency:** Check `logs/product_metrics.csv` — compare `latency_ms` before/after each tier
3. **Regression:** Verify KG enrichment data still appears in the UI detail panels, citations still render, confidence scores are consistent
4. **Streaming:** Verify text appears incrementally in the chat bubble instead of all-at-once

## Critical Files

- `src/rag/engine.py` — Main pipeline, most changes here
- `src/kg/loader.py` — KG caching bug fix
- `src/ingestion/vertex_embeddings.py` — Embedding model singleton
- `src/ingestion/rxnorm.py` — HTTP response caching
- `src/ingestion/vector_store.py` — Pinecone client reuse
- `src/rag/query_analyzer.py` — Gemini client reuse
- `src/frontend/pages/primary_demo.py` — Streaming UI update
- `src/clients.py` — New file for shared client singletons
