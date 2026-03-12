"""
RxClass Opioid Fetcher
=======================
Queries the RxClass API across multiple classification hierarchies (ATC, MED-RT,
FDA EPC) to enumerate every opioid drug by RxCUI. Resolves to active ingredients
and tags with opioid category.

Usage:
    python -m opioid_track.ingestion.rxclass_opioid_fetcher
"""

import json
import os
import time

from opioid_track import config
from opioid_track.ingestion import retry_get


def fetch_class_members(class_id, rela_source, rela=None):
    """Query RxClass API for members of a drug class.

    Returns list of (rxcui, name, tty) tuples.
    """
    url = (f"{config.RXCLASS_BASE}/classMembers.json"
           f"?classId={class_id}&relaSource={rela_source}")
    if rela:
        url += f"&rela={rela}"

    try:
        resp = retry_get(url, delay_between=config.RXNAV_DELAY_SECONDS)
        data = resp.json()
    except Exception as e:
        print(f"  WARNING: Failed to fetch class members for {class_id}: {e}")
        return []

    members = []
    member_group = data.get("drugMemberGroup", {})
    drug_members = member_group.get("drugMember", [])
    if not isinstance(drug_members, list):
        drug_members = [drug_members]

    for member in drug_members:
        concept = member.get("minConcept", {})
        rxcui = concept.get("rxcui", "")
        name = concept.get("name", "")
        tty = concept.get("tty", "")
        if rxcui:
            members.append((rxcui, name, tty))

    return members


def fetch_all_opioid_rxcuis():
    """Query all three classification hierarchies and deduplicate.

    Returns dict keyed by rxcui with merged classification metadata.
    """
    rxcui_map = {}  # rxcui -> {drug_name, tty, atc_codes, atc_descs, medrt, epc}

    def _ensure_entry(rxcui, name, tty):
        if rxcui not in rxcui_map:
            rxcui_map[rxcui] = {
                "rxcui": rxcui,
                "drug_name": name,
                "tty": tty,
                "atc_codes": [],
                "atc_descriptions": [],
                "med_rt_classes": [],
                "epc_classes": [],
            }

    # 1. ATC opioid classes
    print("Querying ATC opioid classes...")
    for atc_code, desc in config.ATC_OPIOID_CLASSES.items():
        print(f"  ATC {atc_code}: {desc}")
        members = fetch_class_members(atc_code, "ATC")
        for rxcui, name, tty in members:
            _ensure_entry(rxcui, name, tty)
            if atc_code not in rxcui_map[rxcui]["atc_codes"]:
                rxcui_map[rxcui]["atc_codes"].append(atc_code)
            if desc not in rxcui_map[rxcui]["atc_descriptions"]:
                rxcui_map[rxcui]["atc_descriptions"].append(desc)
        print(f"    Found {len(members)} members")

    # 2. MED-RT mechanisms of action (rela must be lowercase "has_moa")
    print("\nQuerying MED-RT opioid mechanisms...")
    for concept_id, moa_name in config.MEDRT_OPIOID_CONCEPTS.items():
        print(f"  MED-RT {concept_id}: {moa_name}")
        members = fetch_class_members(concept_id, "MEDRT", rela="has_moa")
        for rxcui, name, tty in members:
            _ensure_entry(rxcui, name, tty)
            if moa_name not in rxcui_map[rxcui]["med_rt_classes"]:
                rxcui_map[rxcui]["med_rt_classes"].append(moa_name)
        print(f"    Found {len(members)} members")

    # 3. FDA EPC classes (use numeric class IDs with FDASPL source)
    print("\nQuerying FDA EPC opioid classes...")
    for epc_id, epc_name in config.FDA_EPC_OPIOID.items():
        print(f"  EPC {epc_id}: {epc_name}")
        members = fetch_class_members(epc_id, "FDASPL", rela="has_EPC")
        for rxcui, name, tty in members:
            _ensure_entry(rxcui, name, tty)
            if epc_name not in rxcui_map[rxcui]["epc_classes"]:
                rxcui_map[rxcui]["epc_classes"].append(epc_name)
        print(f"    Found {len(members)} members")

    print(f"\nTotal unique RxCUIs after dedup: {len(rxcui_map)}")
    return rxcui_map


def resolve_products_and_ingredients(rxcui):
    """Resolve an RxCUI to its active ingredients (IN/MIN) and products (SCD/SBD).

    Returns list of {rxcui, name, tty} dicts.
    """
    url = f"{config.RXNAV_BASE}/rxcui/{rxcui}/allrelated.json"
    try:
        resp = retry_get(url, delay_between=config.RXNAV_DELAY_SECONDS)
        data = resp.json()
    except Exception as e:
        print(f"  WARNING: Failed to resolve concepts for RxCUI {rxcui}: {e}")
        return []

    concepts = []
    concept_groups = (data.get("allRelatedGroup", {})
                      .get("conceptGroup", []))

    for group in concept_groups:
        tty = group.get("tty", "")
        if tty not in ("IN", "MIN", "SCD", "SBD"):
            continue
        for prop in group.get("conceptProperties", []):
            concepts.append({
                "rxcui": prop.get("rxcui", ""),
                "name": prop.get("name", ""),
                "tty": tty,
            })

    return concepts


def tag_opioid_category(atc_codes):
    """Determine opioid category from ATC codes. Prefer most specific."""
    category = None
    for code in sorted(atc_codes, key=len, reverse=True):
        # Try exact match first, then prefix matches
        if code in config.ATC_TO_CATEGORY:
            return config.ATC_TO_CATEGORY[code]
        # Try prefix (e.g., N02AA01 → N02AA)
        for prefix in sorted(config.ATC_TO_CATEGORY.keys(), key=len, reverse=True):
            if code.startswith(prefix):
                category = config.ATC_TO_CATEGORY[prefix]
                break
        if category:
            return category
    return "unclassified"


def main():
    """Run the full opioid enumeration pipeline."""
    print("=" * 60)
    print("RxClass Opioid Fetcher — Enumerating opioid drugs")
    print("=" * 60)

    # Step 1: Fetch and deduplicate across all hierarchies
    rxcui_map = fetch_all_opioid_rxcuis()

    # Step 2: Resolve ingredients and products for each unique RxCUI
    print(f"\nResolving products and ingredients for {len(rxcui_map)} RxCUIs...")
    resolved = 0
    for i, (rxcui, entry) in enumerate(rxcui_map.items()):
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(rxcui_map)}")
        concepts = resolve_products_and_ingredients(rxcui)
        entry["ingredients"] = [c for c in concepts if c["tty"] in ("IN", "MIN")]
        entry["products"] = [c for c in concepts if c["tty"] in ("SCD", "SBD")]
        if concepts:
            resolved += 1
    print(f"  Resolved concepts for {resolved}/{len(rxcui_map)} RxCUIs")

    # Step 3: Tag opioid category
    print("\nTagging opioid categories...")
    for entry in rxcui_map.values():
        entry["opioid_category"] = tag_opioid_category(entry["atc_codes"])
        entry["schedule"] = ""  # Will be enriched in registry_builder

    # Step 4: Convert to list and save
    results = list(rxcui_map.values())

    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.RXCLASS_OUTPUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved {len(results)} opioid entries to {config.RXCLASS_OUTPUT}")

    # Step 5: Validate
    print("\nValidation — checking MUST_INCLUDE_OPIOIDS:")
    all_names_lower = set()
    for entry in results:
        all_names_lower.add(entry["drug_name"].lower())
        for ing in entry.get("ingredients", []):
            all_names_lower.add(ing["name"].lower())

    missing = []
    for required in config.MUST_INCLUDE_OPIOIDS:
        found = any(required.lower() in name for name in all_names_lower)
        status = "OK" if found else "MISSING"
        if not found:
            missing.append(required)
        print(f"  {required}: {status}")

    if missing:
        print(f"\n  WARNING: {len(missing)} required opioids not found: {missing}")
    else:
        print(f"\n  All {len(config.MUST_INCLUDE_OPIOIDS)} required opioids found!")

    print(f"\nDone. Total opioid RxCUIs: {len(results)}")
    return results


if __name__ == "__main__":
    main()
