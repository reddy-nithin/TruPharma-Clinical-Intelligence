"""
query_analyzer.py · LLM-Based Query Entity & Intent Extraction
==============================================================
Uses Gemini to extract drug names, reactions, and intent from user queries.
Routes to appropriate KG query methods based on intent.
No LLM-generated Cypher — uses deterministic KnowledgeGraph methods only.
"""

import json
import re
import warnings
from typing import Any, Dict, List, Optional


_ANALYSIS_PROMPT = """You are a pharmacology query analyzer. Extract structured information from the user's drug-safety question.

Return ONLY a JSON object with these fields:
- "drugs": list of drug names mentioned (generic names preferred)
- "reactions": list of adverse reactions or side effects mentioned
- "intent": one of "safety_check", "interaction", "comparison", "general"

Intent definitions:
- "safety_check": asking about side effects, warnings, adverse reactions of a single drug
- "interaction": asking about drug-drug interactions
- "comparison": comparing two or more drugs
- "general": other drug-related questions (dosage, ingredients, etc.)

Example:
Query: "Does ibuprofen interact with warfarin?"
{"drugs": ["ibuprofen", "warfarin"], "reactions": [], "intent": "interaction"}

Query: "What are the side effects of metformin?"
{"drugs": ["metformin"], "reactions": [], "intent": "safety_check"}

Query: "Compare adverse reactions of ibuprofen and naproxen"
{"drugs": ["ibuprofen", "naproxen"], "reactions": [], "intent": "comparison"}

Now analyze this query:
"""


def analyze_query(query: str) -> Dict[str, Any]:
    """Extract drugs, reactions, and intent from a user query.

    Returns a dict with keys: drugs, reactions, intent.
    Falls back to regex extraction if LLM is unavailable.
    """
    result = _try_llm_analysis(query)
    if result:
        return result
    return _regex_fallback(query)


def _try_llm_analysis(query: str) -> Optional[Dict[str, Any]]:
    """Try LLM-based extraction via Vertex AI or direct Gemini."""
    prompt = _ANALYSIS_PROMPT + f'"{query}"'

    # Try Vertex AI first
    try:
        from src.config import is_vertex_available
        if is_vertex_available():
            import os as _os
            from google import genai
            client = genai.Client(vertexai=True,
                                  project=_os.environ.get("GCP_PROJECT_ID", ""),
                                  location=_os.environ.get("GCP_LOCATION", "us-central1"))
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if resp and resp.text:
                return _parse_response(resp.text)
    except Exception as exc:
        warnings.warn(f"Vertex AI query analysis failed: {exc}")

    # Fallback to direct Gemini API key
    import os
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
            if resp and resp.text:
                return _parse_response(resp.text)
        except Exception as exc:
            warnings.warn(f"Gemini query analysis failed: {exc}")

    return None


def _parse_response(text: str) -> Optional[Dict[str, Any]]:
    """Parse LLM JSON response into structured dict."""
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {
                "drugs": [d.strip().lower() for d in data.get("drugs", []) if isinstance(d, str)],
                "reactions": [r.strip().lower() for r in data.get("reactions", []) if isinstance(r, str)],
                "intent": data.get("intent", "general"),
            }
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _regex_fallback(query: str) -> Dict[str, Any]:
    """Regex-based fallback for query analysis when LLM is unavailable."""
    query_lower = query.lower()

    # Detect intent
    intent = "general"
    if any(kw in query_lower for kw in ("interact", "combination", "together", "with")):
        intent = "interaction"
    elif any(kw in query_lower for kw in ("compare", "comparison", "versus", "vs")):
        intent = "comparison"
    elif any(kw in query_lower for kw in ("side effect", "adverse", "reaction", "warning", "safety", "risk")):
        intent = "safety_check"

    # Extract drug-like words (heuristic: words that aren't common English)
    _STOP = {
        "what", "are", "the", "is", "of", "for", "a", "an", "in", "on", "to",
        "and", "or", "how", "does", "do", "can", "side", "effects", "warnings",
        "interactions", "dosage", "dose", "drug", "about", "with", "tell", "me",
        "information", "safety", "adverse", "reactions", "risk", "taking", "take",
        "should", "i", "my", "it", "its", "this", "that", "compare", "between",
        "any", "there", "have", "has", "been", "reported", "commonly", "most",
        "serious", "severe", "common", "drugs", "medications", "medicine",
    }
    tokens = re.findall(r"[a-zA-Z\-]+", query)
    drugs = [t.lower() for t in tokens if t.lower() not in _STOP and len(t) > 3]

    return {
        "drugs": drugs[:5],
        "reactions": [],
        "intent": intent,
    }


def get_kg_context_for_query(
    analysis: Dict[str, Any],
    kg: Any,
) -> Dict[str, Any]:
    """Retrieve structured KG data based on query analysis.

    Uses deterministic KG methods — no LLM-generated Cypher.
    """
    context: Dict[str, Any] = {
        "drugs_found": [],
        "interactions": [],
        "reactions": [],
        "co_reported": [],
        "cross_interactions": [],
    }

    if not kg:
        return context

    drugs = analysis.get("drugs", [])
    intent = analysis.get("intent", "general")

    for drug_name in drugs:
        identity = kg.get_drug_identity(drug_name)
        if identity:
            context["drugs_found"].append(identity)

            if intent in ("safety_check", "general", "comparison"):
                reactions = kg.get_drug_reactions(drug_name)
                context["reactions"].extend(reactions[:10])
                co_reported = kg.get_co_reported(drug_name)
                context["co_reported"].extend(co_reported[:10])

            if intent in ("interaction", "general", "comparison"):
                interactions = kg.get_interactions(drug_name)
                context["interactions"].extend(interactions[:10])

    # For interaction queries with 2+ drugs, check cross-interactions
    if intent == "interaction" and len(drugs) >= 2:
        for i, drug_a in enumerate(drugs):
            for drug_b in drugs[i + 1:]:
                interactions_a = kg.get_interactions(drug_a)
                for ix in interactions_a:
                    if drug_b.lower() in ix.get("drug_name", "").lower():
                        context["cross_interactions"].append({
                            "drug_a": drug_a,
                            "drug_b": drug_b,
                            "details": ix,
                        })

    return context


def format_kg_context_for_prompt(kg_context: Dict[str, Any]) -> str:
    """Format KG context into a structured text block for the LLM prompt."""
    lines = ["## Knowledge Graph Facts"]

    drugs_found = kg_context.get("drugs_found", [])
    if drugs_found:
        for d in drugs_found:
            generic = d.get("generic_name", "Unknown")
            rxcui = d.get("rxcui", "")
            brands = ", ".join(d.get("brand_names", [])[:3]) or "N/A"
            lines.append(f"- Drug: {generic} | RxCUI: {rxcui} | Brands: {brands}")
    else:
        lines.append("- No drugs matched in the Knowledge Graph")

    interactions = kg_context.get("interactions", [])
    if interactions:
        lines.append(f"\nKnown interactions ({len(interactions)}):")
        for ix in interactions[:8]:
            name = ix.get("drug_name", "")
            desc = ix.get("description", "")[:100]
            lines.append(f"  - {name}: {desc}" if desc else f"  - {name}")

    cross_ix = kg_context.get("cross_interactions", [])
    if cross_ix:
        lines.append("\nDirect cross-interactions found:")
        for cx in cross_ix:
            lines.append(f"  - {cx['drug_a']} <-> {cx['drug_b']}: {cx['details'].get('description', '')[:100]}")

    reactions = kg_context.get("reactions", [])
    if reactions:
        lines.append(f"\nTop adverse reactions (FAERS, {len(reactions)} shown):")
        for rx in reactions[:8]:
            name = rx.get("reaction", "")
            cnt = rx.get("report_count", 0)
            lines.append(f"  - {name} ({cnt:,} reports)")

    co_reported = kg_context.get("co_reported", [])
    if co_reported:
        lines.append(f"\nFrequently co-reported drugs ({len(co_reported)} shown):")
        for cr in co_reported[:5]:
            name = cr.get("drug_name", "")
            cnt = cr.get("report_count", 0)
            lines.append(f"  - {name} ({cnt:,} co-reports)")

    return "\n".join(lines)
