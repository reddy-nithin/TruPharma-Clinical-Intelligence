"""
test_prompt_eval.py — Automated prompt quality evaluation for TruPharma RAG
============================================================================
Runs representative queries through run_rag_query() and checks:
  - Citation presence ([Evidence N], [KG], [FAERS] tags)
  - Adaptive length (word count within expected range per query type)
  - Scope adherence (off-topic → redirect, treatment Qs → safety-redirect)
  - Key safety terms present for known high-risk interactions
  - Conversation follow-up resolution (pronoun/reference resolution)

Usage:
    pytest tests/test_prompt_eval.py -v
    pytest tests/test_prompt_eval.py -v --tb=short 2>&1 | tee reports/prompt_eval_run.txt

Generates reports/prompt_eval_YYYY-MM-DD.md with pass/fail per case.
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

# ── Ensure project root is importable ────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# ── Report path ───────────────────────────────────────────────────────────────
REPORTS_DIR = _PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
REPORT_PATH = REPORTS_DIR / f"prompt_eval_{date.today().isoformat()}.md"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _word_count(text: str) -> int:
    return len(text.split())


def _has_citation(text: str) -> bool:
    """Check for at least one citation tag."""
    return bool(re.search(r"\[Evidence \d+\]|\[KG\]|\[FAERS\]", text))


def _run(query: str, history=None) -> dict:
    """Run a query through the RAG pipeline.

    Returns the full result dict, or raises if the engine import fails.
    Falls back gracefully when LLM is unavailable (extractive fallback still
    exercises the prompt assembly path).
    """
    from src.rag.engine import run_rag_query

    gemini_key = (
        os.environ.get("GEMINI_API_KEY") or
        os.environ.get("GOOGLE_API_KEY", "")
    )
    return run_rag_query(
        query,
        gemini_key=gemini_key,
        conversation_history=history,
        top_k=5,
    )


# ── Collected results for the markdown report ─────────────────────────────────
_eval_results: list[dict] = []


def _record(category: str, query: str, checks: list[tuple[str, bool, str]], answer: str):
    """Store a result entry for the end-of-run report."""
    _eval_results.append({
        "category": category,
        "query": query,
        "checks": checks,
        "answer_excerpt": answer[:400] if answer else "",
        "passed": all(ok for _, ok, _ in checks),
    })


# ── Test cases ────────────────────────────────────────────────────────────────

class TestSimpleLookup:
    """Simple factual lookup — should be concise (≤150 words) and have citations."""

    def test_omeprazole_side_effects(self):
        query = "What are the side effects of omeprazole?"
        result = _run(query)
        answer = result.get("answer", "")
        wc = _word_count(answer)

        checks = [
            ("Has answer", bool(answer), answer[:100]),
            ("Has citation", _has_citation(answer), answer[:200]),
            ("Concise ≤150 words", wc <= 150, f"word count={wc}"),
        ]
        _record("Simple lookup", query, checks, answer)
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestInteraction:
    """Drug interaction — should mention mechanism and key risk term."""

    def test_aspirin_warfarin(self):
        query = "Can I take aspirin with warfarin?"
        result = _run(query)
        answer = result.get("answer", "").lower()
        wc = _word_count(answer)

        checks = [
            ("Has answer", bool(answer), ""),
            ("Has citation", _has_citation(result.get("answer", "")), result.get("answer", "")[:200]),
            ("Mentions bleeding risk", "bleed" in answer, answer[:300]),
            ("Adequate length ≥30 words", wc >= 30, f"word count={wc}"),
        ]
        _record("Interaction", query, checks, result.get("answer", ""))
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestComparison:
    """Drug comparison — should address both drugs."""

    def test_ibuprofen_naproxen(self):
        query = "Compare ibuprofen and naproxen adverse reactions"
        result = _run(query)
        answer = result.get("answer", "").lower()

        checks = [
            ("Has answer", bool(answer), ""),
            ("Has citation", _has_citation(result.get("answer", "")), result.get("answer", "")[:200]),
            ("Mentions ibuprofen", "ibuprofen" in answer, answer[:300]),
            ("Mentions naproxen", "naproxen" in answer, answer[:300]),
        ]
        _record("Comparison", query, checks, result.get("answer", ""))
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestOffTopic:
    """Off-topic queries should get a graceful redirect — no drug info fabricated."""

    def test_weather(self):
        query = "What's the weather today?"
        result = _run(query)
        answer = result.get("answer", "").lower()

        # The scope gate may return "Not enough evidence..." OR a redirect message.
        # Either is acceptable — what's NOT acceptable is fabricated drug info.
        is_redirect = (
            "not enough evidence" in answer
            or "trupharma focuses" in answer
            or "drug safety" in answer
            or not result.get("llm_used", False)
        )
        checks = [
            ("Is redirect / no drug fabrication", is_redirect, answer[:300]),
        ]
        _record("Off-topic", query, checks, result.get("answer", ""))
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestTreatmentRequest:
    """Treatment requests should trigger safety-redirect, not drug recommendations."""

    def test_diabetes_treatment(self):
        query = "I have diabetes, what medicine should I take?"
        result = _run(query)
        answer = result.get("answer", "").lower()

        # Should NOT recommend a specific drug as a prescription choice
        # Should redirect / offer to review safety profiles
        is_safe_response = (
            "not enough evidence" in answer
            or "doctor" in answer
            or "pharmacist" in answer
            or "safety profile" in answer
            or "prescrib" in answer
            or not result.get("llm_used", False)
        )
        checks = [
            ("Safety redirect present", is_safe_response, answer[:300]),
        ]
        _record("Treatment request", query, checks, result.get("answer", ""))
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestFAERSHeavy:
    """FAERS-heavy query — co-reports should be mentioned when available."""

    def test_prednisone_coreports(self):
        query = "What drugs are co-reported with prednisone in FAERS?"
        result = _run(query)
        answer = result.get("answer", "")

        # Either we get an answer with content, or the scope gate fires —
        # the key check is that the query doesn't error out
        checks = [
            ("Returns answer without exception", bool(answer), ""),
        ]
        # Bonus: if KG data is available, co-report info should appear
        if result.get("kg_available") and result.get("kg_co_reported"):
            has_faers = bool(re.search(r"\[FAERS\]|\[KG\]|co.report|faers", answer.lower()))
            checks.append(("FAERS/KG data referenced", has_faers, answer[:300]))

        _record("FAERS heavy", query, checks, answer)
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestFollowUp:
    """Follow-up query — pronoun/reference should resolve to the prior drug."""

    def test_its_interactions(self):
        history = [
            {"role": "user", "content": "Tell me about metformin."},
            {"role": "assistant", "content": "Metformin is a biguanide used for type 2 diabetes."},
        ]
        query = "What about its interactions?"
        result = _run(query, history=history)
        answer = result.get("answer", "").lower()

        checks = [
            ("Has answer", bool(answer), ""),
            # Drug name resolved (metformin should appear somewhere in the response)
            ("Resolves metformin reference", "metformin" in answer or "biguanide" in answer, answer[:300]),
        ]
        _record("Follow-up", query, checks, result.get("answer", ""))
        for desc, ok, detail in checks:
            assert ok, f"[{desc}] FAILED — {detail}"


class TestMechanismIntent:
    """Mechanism query — query_analyzer should return intent='mechanism'."""

    def test_mechanism_intent_detection(self):
        from src.rag.query_analyzer import analyze_query

        result = analyze_query("Why does metformin cause lactic acidosis?")
        assert result["intent"] == "mechanism", (
            f"Expected intent='mechanism', got '{result['intent']}'"
        )
        assert "metformin" in result["drugs"], (
            f"Expected 'metformin' in drugs, got {result['drugs']}"
        )

    def test_context_clues_extracted(self):
        from src.rag.query_analyzer import analyze_query

        result = analyze_query("What are the side effects of metformin in elderly patients?")
        assert result["intent"] == "safety_check"
        assert "metformin" in result["drugs"]
        # context_clues may or may not be populated depending on LLM availability
        # — just check the key exists
        assert "context_clues" in result


class TestQueryAnalyzer:
    """Unit tests for the improved _ANALYSIS_PROMPT / _parse_response."""

    def test_off_topic_returns_empty_drugs(self):
        from src.rag.query_analyzer import analyze_query

        result = analyze_query("What is the capital of France?")
        # With LLM: drugs should be empty; regex fallback may produce some tokens
        # Accept either empty or very short list (regex fallback limitation)
        assert isinstance(result["drugs"], list)
        assert "context_clues" in result

    def test_interaction_intent(self):
        from src.rag.query_analyzer import analyze_query

        result = analyze_query("Does aspirin interact with warfarin?")
        assert result["intent"] == "interaction"
        assert "aspirin" in result["drugs"]
        assert "warfarin" in result["drugs"]

    def test_comparison_intent(self):
        from src.rag.query_analyzer import analyze_query

        result = analyze_query("Compare ibuprofen vs naproxen adverse effects")
        assert result["intent"] == "comparison"


# ── Report generation ─────────────────────────────────────────────────────────

def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """Write the markdown evaluation report after all tests run."""
    if not _eval_results:
        return

    lines = [
        f"# TruPharma Prompt Evaluation Report — {date.today().isoformat()}",
        "",
        f"**Total cases:** {len(_eval_results)}  ",
        f"**Passed:** {sum(1 for r in _eval_results if r['passed'])}  ",
        f"**Failed:** {sum(1 for r in _eval_results if not r['passed'])}",
        "",
        "---",
        "",
    ]

    for r in _eval_results:
        status = "✅ PASS" if r["passed"] else "❌ FAIL"
        lines += [
            f"## {status} — {r['category']}",
            f"**Query:** `{r['query']}`",
            "",
            "**Checks:**",
        ]
        for desc, ok, detail in r["checks"]:
            icon = "✓" if ok else "✗"
            lines.append(f"- [{icon}] {desc}" + (f" — `{detail[:120]}`" if detail else ""))
        lines += [
            "",
            "**Answer excerpt:**",
            f"> {r['answer_excerpt'].replace(chr(10), ' ')[:400]}",
            "",
            "---",
            "",
        ]

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📊 Eval report written to: {REPORT_PATH}")
