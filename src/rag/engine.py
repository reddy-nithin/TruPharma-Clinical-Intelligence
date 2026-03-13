"""
engine.py  ·  TruPharma RAG Back-End
=====================================
Wraps openfda_rag helpers with:
  - Hybrid retrieval (dense + sparse + optional rerank)
  - LLM-grounded answer generation (Google Gemini or extractive fallback)
  - Interaction logging to logs/product_metrics.csv
"""

import gc
import os
import sys
import re
import csv
import time
import json
import warnings
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

# ── Ensure project root is importable ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.ingestion.openfda_client import (
    TextChunk,
    SubChunk,
    build_artifacts,
    build_openfda_query,
    tokenize,
)
from src.kg.loader import load_kg, reload_kg
from src.rag.drug_profile import _extract_drug_name

# ── Silence noisy libraries ──────────────────────────────────
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")
warnings.filterwarnings("ignore", message=".*unauthenticated.*")

# ══════════════════════════════════════════════════════════════
#  CONFIGURATION
# ══════════════════════════════════════════════════════════════

FIELD_ALLOWLIST = None  # None = include ALL fields (blocklist filters the noise)

FIELD_BLOCKLIST = {
    "spl_product_data_elements",
    "spl_indexing_data_elements",
    "effective_time",
    "set_id",
    "id",
    "version",
    "openfda",
    "package_label_principal_display_panel",
}

API_BASE = "https://api.fda.gov/drug/label.json"
DEFAULT_LIMIT = 20
DEFAULT_MAX_REC = 20
USE_SENTENCE_TRANSFORMERS = False

# ── Logging paths ────────────────────────────────────────────
LOG_DIR = _PROJECT_ROOT / "logs"
LOG_CSV = LOG_DIR / "product_metrics.csv"
LOG_COLS = [
    "timestamp",
    "query",
    "latency_ms",
    "evidence_ids",
    "confidence",
    "num_evidence",
    "num_records",
    "retrieval_method",
    "llm_used",
    "answer_preview",
]


# ══════════════════════════════════════════════════════════════
#  RETRIEVAL HELPERS
# ══════════════════════════════════════════════════════════════

# ── Dynamic KG expansion metadata (set per-query) ────────────
_dynamic_build_result: Dict[str, Any] = {}


def _drug_is_known(name: str) -> bool:
    """
    Fast check: is *name* a recognised drug (via local KG then RxNorm)?

    Used to gate out-of-scope queries (e.g. economic projections, general
    science) that would otherwise retrieve incidental keyword matches from
    FDA label text.

    Check order:
      1. KG alias table  — O(1), local SQLite / Neo4j
      2. RxNorm exact-match + concept lookup  — 1-2 HTTP calls
      3. If RxNorm confirms drug but KG doesn't have it → dynamic expansion
      4. If RxNorm is unreachable, return True (benefit of the doubt)
    """
    global _dynamic_build_result
    _dynamic_build_result = {}  # reset per-query

    try:
        kg = load_kg()
        if kg:
            if kg.get_drug_identity(name):
                return True
            if kg.get_ingredient_drugs(name):
                return True
    except Exception:
        pass

    try:
        from src.ingestion.rxnorm import get_rxcui_by_name, get_drug_info

        rxcui = get_rxcui_by_name(name)
        drug_info = get_drug_info(name) if not rxcui else {}
        is_known_drug = bool(rxcui or drug_info.get("rxcuis"))

        if is_known_drug:
            # Drug exists in RxNorm but not in our KG → dynamic expansion
            try:
                from src.kg.dynamic_builder import expand_drug_async, get_build_status
                build_result = expand_drug_async(name)
                _dynamic_build_result = {
                    "kg_dynamic": True,
                    "kg_build_status": get_build_status(name),
                    "kg_build_phase1_time": build_result.get("elapsed_s", 0),
                }
            except Exception:
                pass  # Dynamic expansion is best-effort
            # Reload the cached KG so the new drug is visible for
            # KG enrichment within this same query.
            try:
                reload_kg()
            except Exception:
                pass
            return True
    except Exception:
        return True  # benefit of the doubt

    return False


def _embed_query(query, embedder_type, embedder_model, vectorizer):
    """Embed a query using the same method that was used during indexing."""
    if embedder_type == "vertex_ai":
        try:
            from src.ingestion.vertex_embeddings import embed_query as vertex_embed
            result = vertex_embed(query)
            if result is not None:
                return result
        except Exception:
            pass
        return None
    if embedder_type == "sentence_transformers":
        try:
            from src.ingestion.openfda_client import _get_st_model
        except ImportError:
            return None
        name = embedder_model or "sentence-transformers/all-MiniLM-L6-v2"
        return _get_st_model(name).encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
    if embedder_type == "tfidf" and vectorizer is not None:
        from sklearn.preprocessing import normalize as sk_normalize
        return sk_normalize(vectorizer.transform([query])).toarray().astype(np.float32)
    return None


def _dense(query, index, corpus, e_type, e_model, vec, k=15):
    """Dense (vector) search via FAISS inner-product index."""
    if index is None or not corpus:
        return []
    qv = _embed_query(query, e_type, e_model, vec)
    if qv is None:
        return []
    n = min(k, index.ntotal)
    scores, idxs = index.search(qv.astype(np.float32), n)
    return [
        (float(s), corpus[int(i)])
        for s, i in zip(scores[0], idxs[0])
        if int(i) >= 0
    ]


def _sparse(query, bm25, corpus, k=15):
    """Sparse (BM25) keyword search."""
    if bm25 is None or not corpus:
        return []
    scores = bm25.get_scores(tokenize(query))
    top = np.argsort(scores)[::-1][:k]
    return [(float(scores[i]), corpus[int(i)]) for i in top]


def _fuse(dense_res, sparse_res, alpha=0.5, k=15):
    """Reciprocal-rank fusion of dense + sparse results."""
    cid = lambda it: getattr(it, "chunk_id", str(it))
    dr = {cid(it): r for r, (_, it) in enumerate(dense_res, 1)}
    sr = {cid(it): r for r, (_, it) in enumerate(sparse_res, 1)}
    bucket: Dict[str, Any] = {}
    for _, it in list(dense_res) + list(sparse_res):
        bucket.setdefault(cid(it), it)
    fused = []
    for key, obj in bucket.items():
        d = dr.get(key, len(dense_res) + 1)
        s = sr.get(key, len(sparse_res) + 1)
        fused.append((alpha / d + (1 - alpha) / s, obj))
    fused.sort(key=lambda x: x[0], reverse=True)
    return fused[:k]


def _try_rerank(query, items, top_k):
    """Best-effort cross-encoder rerank; falls back silently."""
    try:
        from sentence_transformers import CrossEncoder
        if not hasattr(_try_rerank, "_model"):
            _try_rerank._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        scores = _try_rerank._model.predict([(query, it.text) for it in items])
        ranked = sorted(zip(scores, items), key=lambda x: x[0], reverse=True)
        return [it for _, it in ranked[:top_k]]
    except Exception:
        return list(items)[:top_k]


# ══════════════════════════════════════════════════════════════
#  ANSWER GENERATION
# ══════════════════════════════════════════════════════════════

_RAG_SYSTEM = (
    "You are TruPharma Assistant, an AI-powered drug safety information tool.\n"
    "Use the provided evidence and knowledge graph data to answer drug safety questions.\n"
    "Cite sources using bracket notation: [FDA Label N] for label evidence, "
    "[FAERS] for adverse event data, [KG] for knowledge graph facts.\n"
    "Keep the answer concise (3-6 sentences). If the evidence is insufficient, "
    "respond exactly:\n"
    '"Not enough evidence in the retrieved context."'
    "\nDo NOT fabricate facts. If conversation history is provided, maintain continuity."
)


def _build_prompt(question: str, evidence: list, kg_context: str = "") -> str:
    """Construct a structured RAG prompt with KG context and evidence citations."""
    lines = [f'{e["cite"]}  {e["content"]}' for e in evidence]
    block = "\n\n".join(lines)

    sections = [_RAG_SYSTEM, ""]

    if kg_context:
        sections.append(kg_context)
        sections.append("")

    sections.append(f"## Retrieved Evidence (Vector Search)\n{block}")
    sections.append("")
    sections.append(f"## User Question\n{question}")
    sections.append("")
    sections.append("Answer (with citations):")

    return "\n".join(sections)



def _call_gemini(
    prompt: str,
    api_key: str = "",
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Optional[str]:
    """Call Gemini for grounded answer generation. Tries Vertex AI first, then direct API.

    Parameters
    ----------
    prompt : str
        The RAG prompt with evidence and question.
    api_key : str
        Direct Gemini API key (fallback if Vertex AI unavailable).
    conversation_history : list, optional
        List of {"role": "user"/"assistant", "content": str} dicts for
        conversational context. Last N messages are prepended to the prompt.
    """
    # Build full prompt with conversation history
    full_prompt = prompt
    if conversation_history:
        history_lines = []
        for msg in conversation_history[-5:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_lines.append(f"{role}: {msg['content'][:500]}")
        if history_lines:
            history_block = "\n".join(history_lines)
            full_prompt = f"Conversation History:\n{history_block}\n\n{prompt}"

    # Try Vertex AI via new google.genai SDK first
    try:
        from src.config import is_vertex_available
        if is_vertex_available():
            from google import genai
            client = genai.Client(vertexai=True, project=os.environ.get("GCP_PROJECT_ID", ""),
                                  location=os.environ.get("GCP_LOCATION", "us-central1"))
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)
            if resp and resp.text:
                return resp.text.strip()
    except Exception as exc:
        warnings.warn(f"Vertex AI Gemini error: {exc}")

    # Fallback to direct Gemini API key
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=full_prompt)
            if resp and resp.text:
                return resp.text.strip()
        except Exception as exc:
            warnings.warn(f"Gemini direct API error: {exc}")

    return None


def _fallback_answer(question: str, evidence: list, n: int = 5) -> str:
    """
    Extractive fallback answer generator — no external LLM required.
    Selects the most relevant sentences from evidence and formats with citations.
    """
    if not evidence:
        return "Not enough evidence in the retrieved context."

    total = sum(len((e.get("content") or "").strip()) for e in evidence)
    if total < 200:
        return "Not enough evidence in the retrieved context."

    q_tok = set(tokenize(question))
    cands = []
    for e in evidence:
        cite = e["cite"]
        for sent in re.split(r"(?<=[.!?])\s+|\n+", (e.get("content") or "")):
            sent = sent.strip()
            if len(sent) < 30:
                continue
            s_tok = set(tokenize(sent))
            overlap = len(q_tok & s_tok)
            bonus = 2 if re.search(r"\d", sent) else 0
            cands.append((overlap + bonus, sent, cite))

    cands.sort(key=lambda x: x[0], reverse=True)
    picked, seen = [], set()
    for sc, sent, cite in cands:
        if sc <= 0:
            break
        key = sent[:60].lower()
        if key in seen:
            continue
        seen.add(key)
        picked.append(f"{sent} {cite}")
        if len(picked) >= n:
            break

    if not picked:
        return "Not enough evidence in the retrieved context."
    return "\n\n".join(picked)


def _confidence(evidence: list, answer: str) -> float:
    """Heuristic confidence score based on evidence coverage and citations."""
    if "Not enough evidence" in answer:
        return 0.0
    n = len(evidence)
    cites = len(re.findall(r"\[.*?\]", answer))
    return round(min(1.0, 0.30 + 0.08 * n + 0.04 * cites), 2)


# ══════════════════════════════════════════════════════════════
#  CSV LOGGING
# ══════════════════════════════════════════════════════════════

def _ensure_log():
    """Create the log directory and CSV header if they don't exist."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_CSV.exists():
        with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=LOG_COLS).writeheader()


def log_row(row: Dict[str, Any]):
    """Append one interaction row to the product metrics CSV."""
    _ensure_log()
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS)
        w.writerow({k: row.get(k, "") for k in LOG_COLS})


def read_logs(last_n: int = 20) -> List[Dict[str, str]]:
    """Read the most recent log rows for display."""
    if not LOG_CSV.exists():
        return []
    with open(LOG_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-last_n:]


# ══════════════════════════════════════════════════════════════
#  MAIN RAG PIPELINE
# ══════════════════════════════════════════════════════════════

def run_rag_query(
    query: str,
    *,
    gemini_key: str = "",
    method: str = "hybrid",
    top_k: int = 5,
    use_rerank: bool = False,
    api_limit: int = DEFAULT_LIMIT,
    max_records: int = DEFAULT_MAX_REC,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    End-to-end RAG pipeline:
      openFDA API fetch  ->  chunk  ->  index  ->  retrieve  ->  generate  ->  log
    """
    t0 = time.time()

    # 0 ── Analyze query for intent and entities (GraphRAG fusion)
    query_analysis = None
    kg_context_text = ""
    try:
        from src.rag.query_analyzer import analyze_query, get_kg_context_for_query, format_kg_context_for_prompt
        query_analysis = analyze_query(query)
        _kg_for_analysis = load_kg()
        if _kg_for_analysis and query_analysis:
            kg_ctx = get_kg_context_for_query(query_analysis, _kg_for_analysis)
            kg_context_text = format_kg_context_for_prompt(kg_ctx)
    except Exception:
        pass

    # 1 ── Extract drug name and build a drug-scoped openFDA query
    drug_name = _extract_drug_name(query)
    if drug_name and len(drug_name) > 2:
        # Scope the API search to the specific drug to avoid irrelevant
        # labels (e.g. MEKINIST) dominating keyword-only searches.
        # Use OR so both generic names (e.g. "tirzepatide") and brand
        # names (e.g. "Zepbound") are matched.
        search_q = (
            f'openfda.generic_name:"{drug_name}"'
            f' OR openfda.brand_name:"{drug_name}"'
        )
    else:
        search_q = build_openfda_query(query, fields=FIELD_ALLOWLIST)

    # 1b ── Scope gate: reject queries that don't reference any drug
    if not _drug_is_known(drug_name):
        lat = round((time.time() - t0) * 1000, 1)
        oos_answer = "Not enough evidence in the retrieved context."
        log_row({
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "query": query[:200],
            "latency_ms": lat,
            "evidence_ids": "",
            "confidence": 0.0,
            "num_evidence": 0,
            "num_records": 0,
            "retrieval_method": method,
            "llm_used": False,
            "answer_preview": oos_answer[:150],
        })
        return {
            "answer": oos_answer,
            "evidence": [],
            "latency_ms": lat,
            "confidence": 0.0,
            "num_records": 0,
            "search_query": search_q,
            "drug_name": drug_name,
            "prompt": "",
            "llm_used": False,
            "method": method,
            "kg_interactions": [],
            "kg_co_reported": [],
            "kg_reactions": [],
            "kg_ingredients": [],
            "kg_available": False,
        }

    # 2 ── Check vector cache (Pinecone) for fresh results
    cache_hit = False
    vector_store = None
    try:
        from src.ingestion.vector_store import create_vector_store
        vector_store = create_vector_store()
        if hasattr(vector_store, 'has_fresh_vectors') and drug_name:
            cache_hit = vector_store.has_fresh_vectors(drug_name)
    except Exception:
        pass

    if cache_hit and vector_store and drug_name:
        # Cache hit — retrieve directly from Pinecone, skip openFDA fetch
        try:
            qv = _embed_query(query, "vertex_ai", "text-embedding-004", None)
            if qv is None:
                cache_hit = False  # Can't query without embeddings
            else:
                cached_results = vector_store.get_drug_vectors(drug_name, qv, top_k=max(20, top_k * 3))
                corpus = []
                for cr in cached_results:
                    meta = cr.get("metadata", {})
                    corpus.append(TextChunk(
                        chunk_id=cr["id"],
                        doc_id=meta.get("doc_id", ""),
                        field=meta.get("field", ""),
                        text=meta.get("text", ""),
                    ))
                n_recs = 0
                n_enriched = 0
                n_chunks = len(corpus)
                items = corpus[:max(20, top_k * 3)]
        except Exception:
            cache_hit = False

    if not cache_hit:
        # 2b ── Fetch + chunk + index (in-memory, no disk save)
        #       Load the KG so chunks are enriched with graph context before
        #       embedding — improves retrieval for multi-hop pharma queries.
        kg = load_kg()
        try:
            arts = build_artifacts(
                api_search=search_q,
                field_allowlist=FIELD_ALLOWLIST,
                field_blocklist=FIELD_BLOCKLIST,
                include_table_fields=False,
                min_chars=40,
                use_st=USE_SENTENCE_TRANSFORMERS,
                save=False,
                save_vectorizer=False,
                api_base_url=API_BASE,
                api_limit=api_limit,
                api_max_records=max_records,
                verbose=False,
                kg=kg,
            )
        except RuntimeError as exc:
            lat = round((time.time() - t0) * 1000, 1)
            if "404" in str(exc) or "Not Found" in str(exc):
                err_answer = "Not enough evidence in the retrieved context."
            else:
                err_answer = f"Error fetching data from openFDA: {exc}"
            log_row({
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "query": query[:200],
                "latency_ms": lat,
                "evidence_ids": "",
                "confidence": 0.0,
                "num_evidence": 0,
                "num_records": 0,
                "retrieval_method": method,
                "llm_used": False,
                "answer_preview": err_answer[:150],
            })
            return {
                "answer": err_answer,
                "evidence": [],
                "latency_ms": lat,
                "confidence": 0.0,
                "num_records": 0,
                "search_query": search_q,
                "drug_name": _extract_drug_name(query),
                "prompt": "",
                "llm_used": False,
                "method": method,
            }

        corpus = arts["record_chunks"]
        index = arts["faiss_A"]
        bm25 = arts["bm25_A"]
        emb = (arts.get("manifest", {}).get("embedder") or {})
        e_type = emb.get("type")
        e_model = emb.get("model")
        vec = arts.get("vectorizer")
        counts = (arts.get("manifest", {}).get("counts") or {})
        n_recs = counts.get("records", 0)
        n_enriched = counts.get("graph_enriched_chunks", 0)
        n_chunks = counts.get("record_chunks", 0)

        # 3 ── Retrieve
        pool = max(20, top_k * 3)
        if method == "dense":
            items = [it for _, it in _dense(query, index, corpus, e_type, e_model, vec, pool)]
        elif method == "sparse":
            items = [it for _, it in _sparse(query, bm25, corpus, pool)]
        else:
            d = _dense(query, index, corpus, e_type, e_model, vec, pool)
            s = _sparse(query, bm25, corpus, pool)
            items = [it for _, it in _fuse(d, s, 0.5, pool)]

        # 3b ── Upsert fresh vectors to cache
        if vector_store and drug_name and corpus:
            try:
                vecs = arts.get("faiss_A")
                if vecs is not None and hasattr(vecs, 'ntotal') and vecs.ntotal > 0:
                    import faiss as _faiss
                    n_total = vecs.ntotal
                    dim = 768 if e_type == "vertex_ai" else vecs.d
                    all_vecs = np.zeros((n_total, dim), dtype=np.float32)
                    for i in range(n_total):
                        all_vecs[i] = vecs.reconstruct(i)

                    # Delete old vectors for this drug, then upsert new
                    vector_store.delete_by_filter({"drug_name": drug_name})

                    cache_ids = []
                    cache_meta = []
                    for i, chunk in enumerate(corpus[:n_total]):
                        cache_ids.append(f"{drug_name}_{chunk.field}_{i:04d}")
                        cache_meta.append({
                            "drug_name": drug_name,
                            "doc_id": chunk.doc_id,
                            "field": chunk.field,
                            "text": chunk.text[:1000],
                            "ingested_at": time.time(),
                        })
                    vector_store.upsert(cache_ids, all_vecs[:len(cache_ids)], cache_meta)
            except Exception:
                pass  # Cache upsert is best-effort

        del arts, index, bm25, corpus, vec
        gc.collect()

    # 4 ── Optional rerank with KG-aware boost
    if use_rerank and items:
        items = _try_rerank(query, items, top_k)
    else:
        items = items[:top_k]

    # 4b ── KG-aware reordering: prioritize chunks mentioning known KG entities
    if query_analysis and items:
        try:
            kg_drugs = set(query_analysis.get("drugs", []))
            if kg_drugs:
                kg_items = []
                non_kg_items = []
                for it in items:
                    text_lower = it.text.lower()
                    if any(d in text_lower for d in kg_drugs):
                        kg_items.append(it)
                    else:
                        non_kg_items.append(it)
                # Put KG-matched items first, then others, keeping top_k total
                items = (kg_items + non_kg_items)[:top_k]
        except Exception:
            pass

    # 5 ── Build evidence pack (keep raw chunk_id for post-processing)
    evidence = [
        {
            "cite": f"[Evidence {i}]",
            "_raw_id": it.chunk_id,
            "content": it.text[:1200],
            "doc_id": it.doc_id,
            "field": it.field,
        }
        for i, it in enumerate(items, 1)
    ]

    # 5b ── KG-aware relevance boost: boost chunks mentioning KG entities
    if query_analysis and evidence:
        try:
            kg_drugs = set(query_analysis.get("drugs", []))
            for ev in evidence:
                content_lower = ev.get("content", "").lower()
                for drug in kg_drugs:
                    if drug in content_lower:
                        ev["_kg_boosted"] = True
                        break
        except Exception:
            pass

    # 6 ── Generate answer (Gemini LLM or extractive fallback)
    prompt = _build_prompt(query, evidence, kg_context=kg_context_text)
    llm_used = False
    answer = None

    answer = _call_gemini(prompt, gemini_key, conversation_history=conversation_history)
    if answer:
        llm_used = True

    if not llm_used and gemini_key:
        # Retry with direct API key if Vertex AI failed
        answer = _call_gemini(prompt, gemini_key)
        if answer:
            llm_used = True

    if answer is None:
        answer = _fallback_answer(query, evidence)

    # 6b ── Normalize citations: replace any raw chunk IDs the LLM
    #        may have emitted with the clean [Evidence N] labels.
    for ev in evidence:
        answer = answer.replace(f"[{ev['_raw_id']}]", ev["cite"])

    # 7 ── Compute confidence
    conf = _confidence(evidence, answer)
    lat = round((time.time() - t0) * 1000, 1)

    # 8 ── Knowledge Graph enrichment (additive, graceful degradation)
    kg_data = {
        "kg_interactions": [],
        "kg_co_reported": [],
        "kg_reactions": [],
        "kg_ingredients": [],
        "kg_available": False,
    }
    try:
        kg = load_kg()
        if kg:
            # drug_name already extracted above — reuse it

            # Strategy 1: try the raw extracted name directly (uses alias table — fast, reliable)
            if kg.get_drug_identity(drug_name):
                lookup = drug_name
            else:
                # Strategy 2: RxNorm resolution as fallback
                # Handles brand-name queries (e.g. "Zepbound" → rxcui for tirzepatide)
                # where the KG stores the drug under its generic/rxcui ID.
                try:
                    from src.ingestion.rxnorm import resolve_drug_name
                    rxnorm = resolve_drug_name(drug_name)
                    # Try rxcui first, then generic name, then original
                    for candidate in [
                        rxnorm.get("rxcui"),
                        rxnorm.get("generic_name"),
                        drug_name,
                    ]:
                        if candidate and kg.get_drug_identity(candidate):
                            lookup = candidate
                            break
                    else:
                        lookup = rxnorm.get("rxcui") or rxnorm.get("generic_name") or drug_name
                except Exception:
                    lookup = drug_name

            identity = kg.get_drug_identity(lookup)
            if identity:
                kg_data["kg_interactions"] = kg.get_interactions(lookup)
                kg_data["kg_co_reported"] = kg.get_co_reported(lookup)
                kg_data["kg_reactions"] = kg.get_drug_reactions(lookup)
                kg_data["kg_ingredients"] = kg.get_ingredients(lookup)
                kg_data["kg_identity"] = identity
            else:
                ingredient_drugs = kg.get_ingredient_drugs(drug_name)
                if ingredient_drugs:
                    kg_data["kg_ingredient_match"] = {
                        "ingredient": drug_name,
                        "drugs": ingredient_drugs,
                    }

            kg_data["kg_available"] = True
            kg_data["_drug_name"] = drug_name
    except Exception:
        pass  # Graceful degradation

    # 9 ── Log interaction to CSV
    ev_ids = [e["cite"] for e in evidence]
    log_row({
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "query": query[:200],
        "latency_ms": lat,
        "evidence_ids": "; ".join(ev_ids),
        "confidence": conf,
        "num_evidence": len(evidence),
        "num_records": n_recs,
        "retrieval_method": method,
        "llm_used": llm_used,
        "answer_preview": (answer or "")[:150],
    })

    return {
        "answer": answer,
        "evidence": evidence,
        "latency_ms": lat,
        "confidence": conf,
        "num_records": n_recs,
        "search_query": search_q,
        "drug_name": kg_data.get("_drug_name", _extract_drug_name(query)),
        "prompt": prompt,
        "llm_used": llm_used,
        "method": method,
        "graph_enriched_chunks": n_enriched,
        "total_chunks": n_chunks,
        **kg_data,
        **_dynamic_build_result,
    }
