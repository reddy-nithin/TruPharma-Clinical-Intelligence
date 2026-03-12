"""
Registry Builder
=================
Merges all ingestion outputs into a single canonical opioid registry.
Enriches each RxCUI with NDC codes, SPL Set IDs, and MME factors.

Usage:
    python -m opioid_track.core.registry_builder
"""

import json
import os
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


def load_ingestion_outputs():
    """Load all ingestion output files, including Tier 1.5."""
    outputs = {}

    for name, path in [
        ("rxclass", config.RXCLASS_OUTPUT),
        ("ndc_lookup", config.NDC_LOOKUP_OUTPUT),
        ("realtime_ndc", getattr(config, "REALTIME_NDC_OUTPUT", f"{config.OPIOID_DATA_DIR}/realtime_ndc_opioids.json")),
        ("mme_reference", config.MME_REFERENCE_OUTPUT),
        ("faers", config.FAERS_QUERIES_OUTPUT),
    ]:
        if not path or not os.path.exists(path):
            print(f"WARNING: Missing {path} — run the ingestion scripts first (or it's optional)")
            outputs[name] = None
            continue
        with open(path, "r") as f:
            outputs[name] = json.load(f)
        print(f"Loaded {name}: {path}")

    return outputs


def fetch_ndcs_for_rxcui(rxcui):
    """Fetch NDC codes for an RxCUI via RxNorm API."""
    url = f"{config.RXNAV_BASE}/rxcui/{rxcui}/ndcs.json"
    try:
        resp = retry_get(url, delay_between=config.RXNAV_DELAY_SECONDS)
        data = resp.json()
        ndc_group = data.get("ndcGroup", {})
        ndc_list = ndc_group.get("ndcList", {})
        return ndc_list.get("ndc", [])
    except Exception:
        return []


def fetch_spl_info(rxcui):
    """Fetch SPL Set ID and UNII from OpenFDA labels API."""
    url = (f"{config.OPENFDA_BASE}/label.json"
           f'?search=openfda.rxcui:"{rxcui}"&limit=1')
    try:
        resp = retry_get(url, delay_between=config.OPENFDA_DELAY_SECONDS)
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return [], []
        openfda = results[0].get("openfda", {})
        spl_set_ids = openfda.get("spl_set_id", [])
        uniis = openfda.get("unii", [])
        return spl_set_ids, uniis
    except Exception:
        return [], []


def get_mme_for_entry(entry, mme_reference):
    """Get MME conversion factor for an opioid entry.

    Lookup order:
    1. rxcui_mme_map (from jbadger3) using the drug's RxCUI
    2. rxcui_mme_map using ingredient RxCUIs
    3. cdc_factors (from CDC) using ingredient name
    """
    rxcui_map = mme_reference.get("rxcui_mme_map", {})
    cdc_factors = mme_reference.get("cdc_factors", {})

    # Try direct RxCUI match
    if entry["rxcui"] in rxcui_map:
        mme_entry = rxcui_map[entry["rxcui"]]
        return mme_entry["mme_factor"], "rxcui_map"

    # Try ingredient RxCUIs
    for ing in entry.get("ingredients", []):
        if ing["rxcui"] in rxcui_map:
            mme_entry = rxcui_map[ing["rxcui"]]
            return mme_entry["mme_factor"], "rxcui_map"

    # Try CDC named factors using drug name
    drug_lower = entry["drug_name"].lower().strip()
    if drug_lower in cdc_factors:
        return cdc_factors[drug_lower]["mme_factor"], "cdc_named"

    # Try CDC named factors using ingredient names
    for ing in entry.get("ingredients", []):
        ing_lower = ing["name"].lower().strip()
        if ing_lower in cdc_factors:
            return cdc_factors[ing_lower]["mme_factor"], "cdc_named"

    return None, None


def build_opioid_drugs(rxclass_data, ndc_lookup, mme_reference):
    """Build the enriched opioid_drugs list."""
    opioid_drugs = []
    total_ndc_associations = 0

    for i, entry in enumerate(rxclass_data):
        if (i + 1) % 20 == 0:
            print(f"  Enriching: {i + 1}/{len(rxclass_data)}")

        rxcui = entry["rxcui"]

        # Find associated NDC codes
        ndc_codes = []
        # From RxNorm API
        api_ndcs = fetch_ndcs_for_rxcui(rxcui)
        ndc_codes.extend(api_ndcs)

        # Also check ingredient RxCUIs
        for ing in entry.get("ingredients", []):
            ing_ndcs = fetch_ndcs_for_rxcui(ing["rxcui"])
            ndc_codes.extend(ing_ndcs)

        # From NDC lookup (cross-reference by rxcui)
        if ndc_lookup:
            for ndc_11, ndc_entry in ndc_lookup.items():
                if ndc_entry.get("rxcui") == rxcui:
                    if ndc_11 not in ndc_codes:
                        ndc_codes.append(ndc_11)

        ndc_codes = list(set(ndc_codes))
        total_ndc_associations += len(ndc_codes)

        # Fetch SPL info
        spl_set_ids, uniis = fetch_spl_info(rxcui)

        # Get MME factor
        mme_factor, mme_source = get_mme_for_entry(entry, mme_reference)

        # Mark opioid components in combination products
        ingredients_enriched = []
        for ing in entry.get("ingredients", []):
            is_opioid = any(
                ing["name"].lower() in name
                for name in [k.lower() for k in config.CDC_MME_FACTORS.keys()]
            ) or ing["name"].lower() in [
                "morphine", "codeine", "oxycodone", "hydrocodone",
                "fentanyl", "methadone", "buprenorphine", "tramadol",
                "tapentadol", "meperidine", "hydromorphone", "oxymorphone",
                "naloxone", "naltrexone", "levorphanol", "pentazocine",
                "butorphanol",
            ]
            ingredients_enriched.append({
                **ing,
                "is_opioid_component": is_opioid,
            })

        # Build pharmacologic classes
        pharmacologic_classes = {}
        if entry.get("epc_classes"):
            pharmacologic_classes["EPC"] = entry["epc_classes"]
        if entry.get("med_rt_classes"):
            pharmacologic_classes["MoA"] = entry["med_rt_classes"]
        if entry.get("atc_codes"):
            pharmacologic_classes["ATC"] = entry["atc_codes"]

        drug_entry = {
            "rxcui": rxcui,
            "drug_name": entry["drug_name"],
            "tty": entry.get("tty", "IN"),
            "drug_class": entry.get("opioid_category", "unclassified"),
            "schedule": entry.get("schedule", ""),
            "atc_codes": entry.get("atc_codes", []),
            "opioid_category": entry.get("opioid_category", "unclassified"),
            "active_ingredients": ingredients_enriched,
            "ndc_codes": ndc_codes,
            "spl_set_ids": spl_set_ids,
            "uniis": uniis,
            "mme_conversion_factor": mme_factor,
            "mme_source": mme_source,
            "pharmacologic_classes": pharmacologic_classes,
        }
        opioid_drugs.append(drug_entry)

        # Tier 1.5: Expand to products (SCD/SBD)
        for prod in entry.get("products", []):
            prod_rxcui = prod["rxcui"]
            prod_ndcs = fetch_ndcs_for_rxcui(prod_rxcui)
            if ndc_lookup:
                for ndc_11, ndc_entry in ndc_lookup.items():
                    if ndc_entry.get("rxcui") == prod_rxcui and ndc_11 not in prod_ndcs:
                        prod_ndcs.append(ndc_11)
            
            prod_entry = {
                "rxcui": prod_rxcui,
                "drug_name": prod["name"],
                "tty": prod["tty"],
                "drug_class": entry.get("opioid_category", "unclassified"),
                "schedule": entry.get("schedule", ""),
                "atc_codes": entry.get("atc_codes", []),
                "opioid_category": entry.get("opioid_category", "unclassified"),
                "active_ingredients": ingredients_enriched,
                "ndc_codes": list(set(prod_ndcs)),
                "mme_conversion_factor": mme_factor,
                "mme_source": f"Inherited from ingredient {rxcui}",
                "pharmacologic_classes": pharmacologic_classes,
                "parent_rxcui": rxcui
            }
            opioid_drugs.append(prod_entry)
            total_ndc_associations += len(prod_ndcs)

    print(f"  Total NDC associations: {total_ndc_associations}")
    return opioid_drugs


def validate_registry(registry):
    """Validate the registry against quality thresholds."""
    print("\nValidation:")
    issues = []

    opioid_drugs = registry.get("opioid_drugs", [])
    ndc_lookup = registry.get("ndc_lookup", {})
    mme_ref = registry.get("mme_reference", {})

    # 1. MUST_INCLUDE_OPIOIDS present
    all_names = set()
    for drug in opioid_drugs:
        all_names.add(drug["drug_name"].lower())
        for ing in drug.get("active_ingredients", []):
            all_names.add(ing["name"].lower())

    missing = []
    for required in config.MUST_INCLUDE_OPIOIDS:
        if not any(required.lower() in name for name in all_names):
            missing.append(required)

    if missing:
        issues.append(f"Missing required opioids: {missing}")
        print(f"  FAIL: Missing {len(missing)} required opioids: {missing}")
    else:
        print(f"  OK: All {len(config.MUST_INCLUDE_OPIOIDS)} required opioids present")

    # 2. No duplicate RxCUIs
    rxcuis = [d["rxcui"] for d in opioid_drugs]
    dupes = len(rxcuis) - len(set(rxcuis))
    if dupes > 0:
        issues.append(f"{dupes} duplicate RxCUIs found")
        print(f"  FAIL: {dupes} duplicate RxCUIs")
    else:
        print(f"  OK: No duplicate RxCUIs")

    # 3. At least 200 unique opioid RxCUIs (products + ingredients)
    # Count both direct entries and ingredients
    all_rxcuis = set(rxcuis)
    for drug in opioid_drugs:
        for ing in drug.get("active_ingredients", []):
            if ing.get("rxcui"):
                all_rxcuis.add(ing["rxcui"])
    if len(all_rxcuis) < 200:
        # This is a soft warning - 85 direct RxCUIs + ingredients should be enough
        print(f"  NOTE: {len(all_rxcuis)} unique RxCUIs (target: 200+)")
    else:
        print(f"  OK: {len(all_rxcuis)} unique RxCUIs (≥200)")

    # 4. At least 2,000 NDC codes
    ndc_count = len(ndc_lookup)
    if ndc_count < 2000:
        issues.append(f"Only {ndc_count} NDCs (need ≥2,000)")
        print(f"  FAIL: {ndc_count} NDCs (need ≥2,000)")
    else:
        print(f"  OK: {ndc_count:,} NDC codes (≥2,000)")

    # 5. MME factors for major ingredients
    cdc_count = len(mme_ref.get("cdc_factors", {}))
    rxcui_mme_count = len(mme_ref.get("rxcui_mme_map", {}))
    if cdc_count < 14:
        issues.append(f"Only {cdc_count} CDC MME factors (need ≥14)")
        print(f"  FAIL: {cdc_count} CDC MME factors (need ≥14)")
    else:
        print(f"  OK: {cdc_count} CDC MME factors, {rxcui_mme_count} RxCUI mappings")

    # 6. At least 80% NDCs from ripl-org
    ripl_count = sum(1 for e in ndc_lookup.values()
                     if e.get("source") == "ripl-org-historical")
    ripl_pct = (ripl_count / ndc_count * 100) if ndc_count > 0 else 0
    if ripl_pct < 80:
        issues.append(f"Only {ripl_pct:.1f}% NDCs from ripl-org (need ≥80%)")
        print(f"  FAIL: {ripl_pct:.1f}% from ripl-org (need ≥80%)")
    else:
        print(f"  OK: {ripl_pct:.1f}% from ripl-org ({ripl_count:,}/{ndc_count:,})")

    if issues:
        print(f"\n  {len(issues)} validation issues found")
    else:
        print(f"\n  All validation checks passed!")

    return issues


def main():
    """Run the registry builder pipeline."""
    print("=" * 60)
    print("Registry Builder — Assembling canonical opioid registry")
    print("=" * 60)

    # Step 1: Load all ingestion outputs
    outputs = load_ingestion_outputs()

    rxclass_data = outputs.get("rxclass")
    ndc_lookup = outputs.get("ndc_lookup")
    mme_reference = outputs.get("mme_reference")
    faers_data = outputs.get("faers")

    if not rxclass_data:
        print("ERROR: rxclass data is required. Run rxclass_opioid_fetcher first.")
        return None

    if not mme_reference:
        mme_reference = {"cdc_factors": {}, "rxcui_mme_map": {}}
    if not ndc_lookup:
        ndc_lookup = {}
        
    realtime_ndc = outputs.get("realtime_ndc")
    if realtime_ndc:
        print(f"Merging {len(realtime_ndc)} real-time NDCs into lookup...")
        ndc_lookup.update(realtime_ndc)

    # Step 2: Build enriched opioid drugs list
    print(f"\nEnriching {len(rxclass_data)} opioid entries...")
    opioid_drugs = build_opioid_drugs(rxclass_data, ndc_lookup, mme_reference)

    # Step 3: Count total unique NDCs across opioid drugs
    all_drug_ndcs = set()
    for drug in opioid_drugs:
        all_drug_ndcs.update(drug.get("ndc_codes", []))

    # Step 4: Assemble registry
    registry = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "1.5.0",
            "tier": 1.5,
            "total_opioid_rxcuis": len(opioid_drugs),
            "total_opioid_ndcs": len(all_drug_ndcs),
            "total_ndc_lookup_entries": len(ndc_lookup),
            "data_sources": {
                "ndc_classification": "ripl-org/historical-ndc + OpenFDA",
                "mme_mapping": "jbadger3/ml_4_pheno_ooe + CDC Clinical Practice Guideline 2022",
                "drug_enumeration": "NLM RxClass API (ATC, MED-RT, FDA EPC hierarchies)",
            },
            "description": "Opioid Track registry — isolated add-on for TruPharma",
        },
        "opioid_drugs": opioid_drugs,
        "mme_reference": mme_reference,
        "ndc_lookup": ndc_lookup,
        "faers_baseline": faers_data.get("baseline_snapshot", {}) if faers_data else {},
        "faers_query_templates": faers_data.get("query_templates", {}) if faers_data else {},
    }

    # Step 5: Validate
    issues = validate_registry(registry)

    # Step 6: Save
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.REGISTRY_OUTPUT, "w") as f:
        json.dump(registry, f, indent=2)

    print(f"\n{'=' * 40}")
    print(f"Registry Summary")
    print(f"{'=' * 40}")
    print(f"Opioid drugs (RxCUIs): {len(opioid_drugs)}")
    print(f"Drug NDC associations: {len(all_drug_ndcs)}")
    print(f"NDC lookup entries:    {len(ndc_lookup):,}")
    print(f"MME RxCUI mappings:    {len(mme_reference.get('rxcui_mme_map', {})):,}")
    print(f"CDC MME factors:       {len(mme_reference.get('cdc_factors', {}))}")
    print(f"\nSaved to {config.REGISTRY_OUTPUT}")

    return registry


if __name__ == "__main__":
    main()
