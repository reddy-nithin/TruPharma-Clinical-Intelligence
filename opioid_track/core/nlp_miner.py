"""
Opioid Track — NLP Label Miner (Tier 3, Step 6)
=================================================
Adapts CDCgov/Opioid_Involvement_NLP for DailyMed SPL drug labels.
Fetches structured product labels, parses by LOINC section, and runs
the CDC negation-aware annotator to extract safety insights.

Output: opioid_track/data/opioid_nlp_insights.json

Sources:
    - DailyMed SPL XML labels (NLM)
    - CDCgov/Opioid_Involvement_NLP (negex-based annotation)
"""

import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from opioid_track import config
from opioid_track.ingestion import retry_get

HL7_NS = "{urn:hl7-org:v3}"


# ---------------------------------------------------------------------------
# CDC NLP vendor integration
# ---------------------------------------------------------------------------

def _load_negex_rules() -> list:
    """Load negation rules from the CDC vendor repo."""
    vendor = Path(config.CDC_NLP_VENDOR_DIR)
    sys.path.insert(0, str(vendor))
    from negex_adjusted import sortRules

    triggers_path = vendor / "data" / "negex_triggers.txt"
    with triggers_path.open(encoding="utf-8-sig") as f:
        rules = sortRules(f.readlines())
    return rules


def _load_term_mappings() -> dict:
    """Load opioid term→category mappings from the CDC vendor data."""
    vendor = Path(config.CDC_NLP_VENDOR_DIR)
    mappings_path = vendor / "data" / "FY18_term_mappings.txt"
    term_map = {}
    with mappings_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.lower().startswith("term"):
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                term_map[parts[0].strip().lower()] = parts[1].strip().upper()
    return term_map


def _build_opioid_regex(term_map: dict) -> re.Pattern:
    """Build a compiled regex from term mappings, sorted longest-first."""
    terms = sorted(term_map.keys(), key=len, reverse=True)
    escaped = [re.escape(t) for t in terms]
    pattern = r"\b(?:" + "|".join(escaped) + r")s?\b"
    return re.compile(pattern, re.IGNORECASE)


def annotate_text(text: str, opioid_regex: re.Pattern, negrules: list,
                  safety_terms: list[str]) -> dict:
    """Run CDC-style negation-aware annotation on a text block.

    Returns dict with confirmed mentions, negated mentions, and safety flags.
    """
    from negex_adjusted import negTagger
    from nltk.tokenize import sent_tokenize

    confirmed = set()
    negated = set()
    safety_confirmed = set()
    safety_negated = set()

    sentences = [s for s in sent_tokenize(text) if len(s.strip()) > 2]

    for sentence in sentences:
        # Opioid term detection with negation
        matches = set(m.lower() for m in re.findall(opioid_regex, sentence))
        for match in matches:
            tagger = negTagger(sentence=sentence, phrases=[match],
                               rules=negrules, negP=False)
            if tagger.getNegationFlag() == "affirmed":
                confirmed.add(match)
            else:
                negated.add(match)

        # Safety term detection
        for term in safety_terms:
            if re.search(re.escape(term), sentence, re.IGNORECASE):
                tagger = negTagger(sentence=sentence,
                                   phrases=[term.lower()],
                                   rules=negrules, negP=False)
                if tagger.getNegationFlag() == "affirmed":
                    safety_confirmed.add(term)
                else:
                    safety_negated.add(term)

    return {
        "opioid_mentions_confirmed": sorted(confirmed),
        "opioid_mentions_negated": sorted(negated),
        "safety_terms_confirmed": sorted(safety_confirmed),
        "safety_terms_negated": sorted(safety_negated),
    }


# ---------------------------------------------------------------------------
# DailyMed SPL fetching & parsing
# ---------------------------------------------------------------------------

def fetch_spl_set_id(drug_name: str) -> str | None:
    """Search DailyMed for an SPL set ID by drug name."""
    url = f"{config.DAILYMED_BASE}/spls.json?drug_name={drug_name}&page=1&pagesize=1"
    try:
        resp = retry_get(url, delay_between=0.3)
        data = resp.json()
        results = data.get("data", [])
        if results:
            return results[0].get("setid")
    except Exception:
        pass
    return None


def fetch_spl_xml(spl_set_id: str) -> str | None:
    """Fetch raw SPL XML from DailyMed."""
    url = f"{config.DAILYMED_BASE}/spls/{spl_set_id}.xml"
    try:
        resp = retry_get(url, delay_between=0.5, timeout=60)
        return resp.text
    except Exception as e:
        print(f"    [WARN] SPL XML fetch failed for {spl_set_id}: {e}")
        return None


def _extract_text_recursive(element) -> str:
    """Recursively extract all text from an XML element."""
    parts = []
    if element.text:
        parts.append(element.text.strip())
    for child in element:
        parts.append(_extract_text_recursive(child))
        if child.tail:
            parts.append(child.tail.strip())
    return " ".join(p for p in parts if p)


def parse_spl_sections(xml_text: str) -> dict[str, str]:
    """Parse SPL XML and extract text by LOINC section code."""
    sections = {}
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return sections

    loinc_to_name = {v: k for k, v in config.SPL_OPIOID_SECTIONS.items()}

    for component in root.iter(f"{HL7_NS}component"):
        for section in component.iter(f"{HL7_NS}section"):
            code_el = section.find(f"{HL7_NS}code")
            if code_el is None:
                continue
            loinc = code_el.get("code", "")
            if loinc not in loinc_to_name:
                continue

            section_name = loinc_to_name[loinc]
            text_el = section.find(f"{HL7_NS}text")
            if text_el is not None:
                text = _extract_text_recursive(text_el)
                if text:
                    sections[section_name] = text

    return sections


def _extract_tables_from_section(xml_text: str, loinc_code: str) -> list[dict]:
    """Extract table data from a specific SPL section."""
    tables = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return tables

    for component in root.iter(f"{HL7_NS}component"):
        for section in component.iter(f"{HL7_NS}section"):
            code_el = section.find(f"{HL7_NS}code")
            if code_el is None or code_el.get("code", "") != loinc_code:
                continue
            for table in section.iter(f"{HL7_NS}table"):
                rows = []
                for tr in table.iter(f"{HL7_NS}tr"):
                    cells = []
                    for td in list(tr) + list(tr.iter(f"{HL7_NS}td")) + list(tr.iter(f"{HL7_NS}th")):
                        if td.tag in (f"{HL7_NS}td", f"{HL7_NS}th"):
                            cells.append(_extract_text_recursive(td))
                    if cells:
                        rows.append(cells)
                if rows:
                    tables.append({"rows": rows})
    return tables


# ---------------------------------------------------------------------------
# Structured extraction from label sections
# ---------------------------------------------------------------------------

DOSE_PATTERN = re.compile(
    r'(\d+\.?\d*)\s*(mg|mcg|µg|micrograms?)\b', re.IGNORECASE
)
MAX_DOSE_PATTERN = re.compile(
    r'(?:maximum|max(?:imum)?\.?\s*(?:recommended\s*)?(?:daily\s*)?dose|'
    r'not\s+exceed|should\s+not\s+exceed)\s*[:\-]?\s*'
    r'(\d+\.?\d*)\s*(mg|mcg|µg)',
    re.IGNORECASE
)
SCHEDULE_PATTERN = re.compile(
    r'\b(schedule\s+(?:II|III|IV|V|2|3|4|5)|C-?(?:II|III|IV|V))\b',
    re.IGNORECASE
)
CYP_PATTERN = re.compile(
    r'\b(CYP\s*(?:3A4|2D6|2B6|2C19|2C9|1A2))\b', re.IGNORECASE
)
NALOXONE_DOSE_PATTERN = re.compile(
    r'naloxone[^.]*?(\d+\.?\d*)\s*(?:to\s*(\d+\.?\d*)\s*)?'
    r'(mg|mcg)\s*(?:IV|IM|IN|SC|intraven|intramuscul|intranas)',
    re.IGNORECASE
)


def extract_boxed_warning_data(text: str | None, annotations: dict | None) -> dict:
    result = {
        "present": text is not None and len(text or "") > 20,
        "paragraph_count": 0,
        "key_warnings": [],
        "full_text": None,
    }
    if not text:
        return result

    paragraphs = [p.strip() for p in re.split(r'\n\s*\n|(?<=[.!])\s{2,}', text) if p.strip()]
    result["paragraph_count"] = max(len(paragraphs), 1)
    result["full_text"] = text[:2000]

    warning_keywords = ["addiction", "respiratory depression", "neonatal",
                        "benzodiazepine", "death", "fatal", "rems",
                        "abuse", "misuse", "overdose"]
    if annotations:
        for term in annotations.get("safety_terms_confirmed", []):
            result["key_warnings"].append(term)
    for kw in warning_keywords:
        if re.search(r'\b' + re.escape(kw) + r'\b', text, re.IGNORECASE):
            if kw not in [w.lower() for w in result["key_warnings"]]:
                result["key_warnings"].append(kw)

    return result


def extract_dosage_data(text: str | None) -> dict:
    result = {
        "starting_dose": None,
        "max_daily_dose_mg": None,
        "doses_found": [],
    }
    if not text:
        return result

    doses = DOSE_PATTERN.findall(text)
    for val, unit in doses:
        v = float(val)
        if unit.lower() in ("mcg", "µg", "micrograms", "microgram"):
            v /= 1000
        result["doses_found"].append(f"{val} {unit}")

    if doses:
        first_val = float(doses[0][0])
        first_unit = doses[0][1]
        if first_unit.lower() in ("mcg", "µg"):
            first_val /= 1000
        result["starting_dose"] = f"{doses[0][0]} {doses[0][1]}"

    max_match = MAX_DOSE_PATTERN.search(text)
    if max_match:
        v = float(max_match.group(1))
        u = max_match.group(2)
        if u.lower() in ("mcg", "µg"):
            v /= 1000
        result["max_daily_dose_mg"] = v

    return result


def extract_adverse_reactions(text: str | None, annotations: dict | None) -> dict:
    result = {
        "resp_depression_mentioned": False,
        "reaction_frequencies": [],
        "safety_terms_detected": [],
    }
    if not text:
        return result

    if re.search(r'respiratory\s+depression', text, re.IGNORECASE):
        result["resp_depression_mentioned"] = True

    freq_pattern = re.compile(
        r'(\w[\w\s]{2,40}?)\s*[:\(]\s*(\d+\.?\d*)\s*%', re.IGNORECASE
    )
    for m in freq_pattern.finditer(text[:5000]):
        result["reaction_frequencies"].append({
            "reaction": m.group(1).strip(),
            "frequency_pct": float(m.group(2)),
        })

    if annotations:
        result["safety_terms_detected"] = annotations.get("safety_terms_confirmed", [])

    return result


def extract_drug_interactions(text: str | None) -> dict:
    result = {
        "benzo_warning": False,
        "cyp_interactions": [],
        "contraindicated_classes": [],
    }
    if not text:
        return result

    if re.search(r'benzodiazepine', text, re.IGNORECASE):
        result["benzo_warning"] = True

    cyp_matches = CYP_PATTERN.findall(text)
    result["cyp_interactions"] = sorted(set(m.upper().replace(" ", "") for m in cyp_matches))

    contraindicated_patterns = [
        r'contraindicated.*?with\s+([\w\s,]+)',
        r'must\s+not\s+be\s+used\s+with\s+([\w\s,]+)',
    ]
    for pat in contraindicated_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            result["contraindicated_classes"].append(m.group(1).strip()[:100])

    return result


def extract_abuse_dependence(text: str | None) -> dict:
    result = {"schedule": None, "abuse_potential": None}
    if not text:
        return result

    sched = SCHEDULE_PATTERN.search(text)
    if sched:
        result["schedule"] = sched.group(1).strip()

    for level, keywords in [
        ("high", [r"high\s+potential\s+for\s+abuse", r"substantial\s+risk"]),
        ("moderate", [r"moderate\s+(?:potential|risk)", r"less\s+potential\s+for\s+abuse"]),
        ("low", [r"low\s+(?:potential|risk)\s+for\s+abuse"]),
    ]:
        for kw in keywords:
            if re.search(kw, text, re.IGNORECASE):
                result["abuse_potential"] = level
                break
        if result["abuse_potential"]:
            break

    return result


def extract_overdosage(text: str | None) -> dict:
    result = {
        "naloxone_rescue_dose": None,
        "symptoms": [],
    }
    if not text:
        return result

    naloxone_match = NALOXONE_DOSE_PATTERN.search(text)
    if naloxone_match:
        low = naloxone_match.group(1)
        high = naloxone_match.group(2)
        unit = naloxone_match.group(3)
        if high:
            result["naloxone_rescue_dose"] = f"{low} to {high} {unit}"
        else:
            result["naloxone_rescue_dose"] = f"{low} {unit}"

    symptom_keywords = [
        "respiratory depression", "miosis", "hypotension", "bradycardia",
        "pulmonary edema", "skeletal muscle flaccidity", "cold", "clammy skin",
        "coma", "apnea", "cardiac arrest", "circulatory collapse",
        "somnolence", "stupor",
    ]
    if text:
        for sym in symptom_keywords:
            if re.search(re.escape(sym), text, re.IGNORECASE):
                result["symptoms"].append(sym)

    return result


def check_rems(full_xml_text: str | None) -> dict:
    result = {"rems_required": False, "rems_type": None}
    if not full_xml_text:
        return result

    if re.search(r'Risk\s+Evaluation\s+and\s+Mitigation', full_xml_text, re.IGNORECASE):
        result["rems_required"] = True
        if re.search(r'ETASU', full_xml_text, re.IGNORECASE):
            result["rems_type"] = "ETASU + Medication Guide"
        elif re.search(r'Medication\s+Guide', full_xml_text, re.IGNORECASE):
            result["rems_type"] = "Medication Guide"
        else:
            result["rems_type"] = "REMS"

    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def get_opioid_drugs_for_nlp() -> list[dict]:
    """Get list of opioid drugs that have SPL data or are worth querying."""
    with open(config.REGISTRY_OUTPUT, "r") as f:
        reg = json.load(f)

    drugs = []
    seen_names = set()
    for drug in reg.get("opioid_drugs", []):
        name = (drug.get("drug_name") or "").strip()
        if not name or name.lower() in seen_names:
            continue

        ingredients = drug.get("active_ingredients", [])
        opioid_ingredients = [i for i in ingredients if i.get("is_opioid_component")]
        if not opioid_ingredients:
            continue

        tty = drug.get("tty", "")
        if tty not in ("SCD", "SBD", "GPCK", "BPCK", "IN", "MIN", "BN"):
            continue

        spl_ids = drug.get("spl_set_ids", [])
        schedule = drug.get("schedule", "")

        if tty in ("SCD", "SBD") or spl_ids:
            seen_names.add(name.lower())
            drugs.append({
                "rxcui": drug["rxcui"],
                "drug_name": name,
                "tty": tty,
                "schedule": schedule,
                "spl_set_ids": spl_ids,
                "opioid_ingredients": [i["name"] for i in opioid_ingredients],
                "opioid_category": drug.get("opioid_category", ""),
                "mme_conversion_factor": drug.get("mme_conversion_factor"),
            })

    drugs.sort(key=lambda d: d["drug_name"])
    return drugs


def mine_single_drug(drug: dict, opioid_regex: re.Pattern, negrules: list,
                     safety_terms: list[str]) -> dict | None:
    """Mine NLP insights from a single drug's DailyMed label."""
    name = drug["drug_name"]

    # Resolve SPL set ID
    spl_id = None
    if drug.get("spl_set_ids"):
        spl_id = drug["spl_set_ids"][0]
    else:
        search_name = drug["opioid_ingredients"][0] if drug["opioid_ingredients"] else name
        spl_id = fetch_spl_set_id(search_name)
        if not spl_id:
            spl_id = fetch_spl_set_id(name.split()[0])

    if not spl_id:
        print(f"    No SPL found")
        return None

    # Fetch XML
    xml_text = fetch_spl_xml(spl_id)
    if not xml_text:
        return None

    # Parse sections
    sections = parse_spl_sections(xml_text)
    if not sections:
        print(f"    No parseable sections")
        return None

    print(f"    Sections found: {', '.join(sections.keys())}")

    # Annotate each section
    section_annotations = {}
    for sec_name, sec_text in sections.items():
        ann = annotate_text(sec_text, opioid_regex, negrules, safety_terms)
        section_annotations[sec_name] = ann

    # Extract structured data
    boxed = extract_boxed_warning_data(
        sections.get("boxed_warning"),
        section_annotations.get("boxed_warning"),
    )
    dosage = extract_dosage_data(sections.get("dosage_admin"))
    adverse = extract_adverse_reactions(
        sections.get("adverse_reactions"),
        section_annotations.get("adverse_reactions"),
    )
    interactions = extract_drug_interactions(sections.get("drug_interactions"))
    abuse = extract_abuse_dependence(sections.get("abuse_dependence"))
    overdosage = extract_overdosage(sections.get("overdosage"))
    rems = check_rems(xml_text)

    # Compute max daily MME if possible
    max_daily_mme = None
    mme_factor = drug.get("mme_conversion_factor")
    if mme_factor and dosage.get("max_daily_dose_mg"):
        max_daily_mme = round(dosage["max_daily_dose_mg"] * mme_factor, 1)

    return {
        "drug_name": name,
        "rxcui": drug["rxcui"],
        "spl_set_id": spl_id,
        "opioid_ingredients": drug["opioid_ingredients"],
        "opioid_category": drug["opioid_category"],
        "schedule": drug["schedule"] or abuse.get("schedule"),
        "sections_parsed": list(sections.keys()),
        "section_annotations": {
            sec: {
                "opioid_mentions": ann["opioid_mentions_confirmed"],
                "negated_mentions": ann["opioid_mentions_negated"],
                "safety_flags": ann["safety_terms_confirmed"],
            }
            for sec, ann in section_annotations.items()
        },
        "boxed_warning": boxed,
        "dosage": dosage,
        "max_daily_mme": max_daily_mme,
        "adverse_reactions": adverse,
        "drug_interactions": interactions,
        "abuse_dependence": abuse,
        "overdosage": overdosage,
        "rems": rems,
    }


def build_comparison_matrix(drug_insights: list[dict]) -> list[dict]:
    """Build cross-drug comparison matrix for quick dashboard display."""
    matrix = []
    for d in drug_insights:
        matrix.append({
            "drug_name": d["drug_name"],
            "rxcui": d["rxcui"],
            "max_daily_dose_mg": d["dosage"].get("max_daily_dose_mg"),
            "max_daily_mme": d.get("max_daily_mme"),
            "resp_depression_in_label": d["adverse_reactions"].get("resp_depression_mentioned", False),
            "boxed_warning_count": d["boxed_warning"].get("paragraph_count", 0),
            "benzo_warning": d["drug_interactions"].get("benzo_warning", False),
            "rems_required": d["rems"].get("rems_required", False),
            "rems_type": d["rems"].get("rems_type"),
            "schedule": d.get("schedule"),
            "naloxone_rescue_dose": d["overdosage"].get("naloxone_rescue_dose"),
            "cyp_interactions": d["drug_interactions"].get("cyp_interactions", []),
            "nlp_source": "CDCgov/Opioid_Involvement_NLP",
        })
    return matrix


def build_nlp_insights() -> dict:
    print("=" * 70)
    print("NLP LABEL MINER — Tier 3, Step 6")
    print("  Adapted from CDCgov/Opioid_Involvement_NLP")
    print("=" * 70)

    # Load CDC NLP components
    print("\n--- Loading CDC NLP vendor components ---")
    negrules = _load_negex_rules()
    print(f"  Negation rules loaded: {len(negrules)}")

    term_map = _load_term_mappings()
    print(f"  Term mappings loaded: {len(term_map)}")

    opioid_regex = _build_opioid_regex(term_map)
    safety_terms = config.OPIOID_SAFETY_TERMS

    # Get drugs to process
    drugs = get_opioid_drugs_for_nlp()
    print(f"\n  Candidate drugs for NLP mining: {len(drugs)}")

    # Limit to reasonable batch (unique ingredient-based labels)
    ingredient_seen = set()
    filtered = []
    for d in drugs:
        key = tuple(sorted(d["opioid_ingredients"]))
        if key not in ingredient_seen:
            ingredient_seen.add(key)
            filtered.append(d)
        if len(filtered) >= 30:
            break

    print(f"  Filtered to {len(filtered)} unique-ingredient drugs")

    # Process each drug
    print("\n--- Mining DailyMed labels ---")
    all_insights = []
    for i, drug in enumerate(filtered):
        print(f"\n[{i+1}/{len(filtered)}] {drug['drug_name']}")
        try:
            result = mine_single_drug(drug, opioid_regex, negrules, safety_terms)
            if result:
                all_insights.append(result)
                print(f"    OK — {len(result['sections_parsed'])} sections, "
                      f"boxed={result['boxed_warning']['present']}")
            else:
                print(f"    SKIP — no label data")
        except Exception as e:
            print(f"    ERROR — {e}")
        time.sleep(0.2)

    # Build comparison matrix
    comparison = build_comparison_matrix(all_insights)

    output = {
        "metadata": {
            "nlp_source": "CDCgov/Opioid_Involvement_NLP",
            "data_source": "DailyMed SPL XML Labels",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tier": 3,
            "step": 6,
            "total_drugs_processed": len(all_insights),
            "total_drugs_attempted": len(filtered),
            "sections_targeted": list(config.SPL_OPIOID_SECTIONS.keys()),
        },
        "drug_label_insights": all_insights,
        "comparison_matrix": comparison,
    }
    return output


def main():
    output = build_nlp_insights()
    os.makedirs(os.path.dirname(config.NLP_INSIGHTS_OUTPUT), exist_ok=True)
    with open(config.NLP_INSIGHTS_OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    meta = output["metadata"]
    print("\n" + "=" * 70)
    print("NLP LABEL MINER — COMPLETE")
    print(f"  Total drugs mined: {meta['total_drugs_processed']}")
    print(f"  NLP source: {meta['nlp_source']}")
    print(f"  Saved to: {config.NLP_INSIGHTS_OUTPUT}")
    print("=" * 70)


if __name__ == "__main__":
    main()
