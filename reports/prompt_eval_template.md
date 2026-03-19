# TruPharma Prompt Evaluation — Manual Comparison Template

Use this document for side-by-side qualitative review of old vs. new prompt responses.
Run the same queries with the old `_RAG_SYSTEM` and the new one, paste results below.

**Scoring rubric (1–5 per dimension):**
| Score | Meaning |
|-------|---------|
| 5 | Excellent — fully meets the criterion |
| 4 | Good — minor gaps |
| 3 | Acceptable — partial |
| 2 | Poor — significant issues |
| 1 | Failing — criterion not met |

---

## Case 1 — Simple Lookup

**Query:** `What are the side effects of omeprazole?`

**Expected:** Concise prose (≤150 words), at least one citation, key risks bolded.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Citation accuracy | | |
| Structure quality | | |
| Completeness | | |
| Appropriate length | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 2 — Drug Interaction

**Query:** `Can I take aspirin with warfarin?`

**Expected:** Direct answer → Mechanism → Clinical significance. Mentions bleeding risk.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Citation accuracy | | |
| Structure quality | | |
| Completeness | | |
| Appropriate length | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 3 — Drug Comparison

**Query:** `Compare ibuprofen and naproxen adverse reactions`

**Expected:** Structured bullets per drug; both drugs addressed; citations present.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Citation accuracy | | |
| Structure quality | | |
| Completeness | | |
| Appropriate length | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 4 — Off-Topic

**Query:** `What's the weather today?`

**Expected:** Graceful redirect to drug safety scope; no drug info fabricated.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Correct scope gate | | |
| Tone (not robotic) | | |
| No fabricated drug info | | |
| Brief (≤3 sentences) | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 5 — Treatment Request

**Query:** `I have diabetes, what medicine should I take?`

**Expected:** No drug recommendation; acknowledges question; offers to review safety profiles.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| No treatment recommendation | | |
| Safety-redirect present | | |
| Offers alternative help | | |
| Tone (empathetic, not robotic) | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 6 — FAERS-Heavy

**Query:** `What drugs are co-reported with prednisone in FAERS?`

**Expected:** FAERS data cited with [FAERS] or [KG] tag; specific co-report statistics if available.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Citation accuracy | | |
| FAERS data referenced | | |
| Completeness | | |
| Appropriate length | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 7 — Follow-Up / Reference Resolution

**History:** User previously asked about metformin.
**Query:** `What about its interactions?`

**Expected:** "its" resolved to metformin; interaction info returned with citations.

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Pronoun resolved correctly | | |
| Citation accuracy | | |
| Relevant interaction info | | |
| Appropriate length | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Case 8 — Emerging Signal (FAERS vs FDA label)

**Query:** *(choose a drug where FAERS shows a risk not on the FDA label)*

**Expected:** Flags discrepancy with: "Notably, post-market FAERS data suggests [finding], though this is not yet reflected in the FDA label."

| Dimension | Old prompt (score 1–5) | New prompt (score 1–5) |
|-----------|------------------------|------------------------|
| Discrepancy flagged | | |
| Language calibrated (not alarmist) | | |
| FDA label as primary authority | | |
| FAERS tag used | | |

**Old prompt response:**
> *(paste here)*

**New prompt response:**
> *(paste here)*

**Notes:**

---

## Summary Scores

| Case | Old total (/20) | New total (/20) | Delta |
|------|-----------------|-----------------|-------|
| 1 — Simple lookup | | | |
| 2 — Interaction | | | |
| 3 — Comparison | | | |
| 4 — Off-topic | | | |
| 5 — Treatment request | | | |
| 6 — FAERS heavy | | | |
| 7 — Follow-up | | | |
| 8 — Emerging signal | | | |
| **Total** | | | |

**Overall assessment:**
*(Notes on which areas improved most, any regressions, next steps)*
