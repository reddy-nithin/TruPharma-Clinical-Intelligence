"""
Opioid Track — Toxicology Fetcher (Tier 3, Step 5)
====================================================
Adds LD50 lethality data, therapeutic indices, and danger rankings
to the pharmacology file created by Step 4.

Updates: opioid_track/data/opioid_pharmacology.json

Sources:
    - PubChem PUG View (acute toxicity / LD50 data)
    - PyTDC LD50_Zhu dataset (optional, skip on failure)
    - Interspecies BSA scaling (config.KM_SCALING)
"""

import json
import os
import re
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get

# ---------------------------------------------------------------------------
# PubChem toxicity
# ---------------------------------------------------------------------------

def fetch_pubchem_toxicity(cid: int, ingredient_name: str) -> list[dict]:
    """Fetch LD50 values from PubChem PUG View Toxicity section."""
    url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
           f"?heading=Toxicity")
    ld50_entries = []
    try:
        resp = retry_get(url, delay_between=0.3)
        data = resp.json()
        for sec in data.get("Record", {}).get("Section", []):
            _extract_ld50_recursive(sec, ld50_entries, ingredient_name)
    except Exception as e:
        print(f"    [WARN] PubChem toxicity fetch failed for {ingredient_name}: {e}")
    return ld50_entries


def _extract_ld50_recursive(section: dict, entries: list, ingredient: str):
    heading = (section.get("TOCHeading") or "").lower()

    if "acute" in heading or "lethal" in heading or "ld50" in heading or "toxicity" in heading:
        for info in section.get("Information", []):
            svals = info.get("Value", {}).get("StringWithMarkup", [])
            for sv in svals:
                text = sv.get("String", "")
                parsed = _parse_ld50_text(text)
                for entry in parsed:
                    refs = info.get("Reference", [])
                    src = "PubChem"
                    if refs and isinstance(refs[0], dict):
                        src = refs[0].get("SourceName", "PubChem")
                    entry["source"] = src
                    entries.append(entry)

    for sub in section.get("Section", []):
        _extract_ld50_recursive(sub, entries, ingredient)


LD50_PATTERN = re.compile(
    r'LD50\s*'
    r'(?:\(\s*([a-zA-Z]+)\s*[,;]\s*([a-zA-Z]+)\s*\))?\s*'  # (species, route)
    r'[=:>< ]*\s*'
    r'(\d+\.?\d*)\s*'
    r'(mg/kg|g/kg|µg/kg|mcg/kg)',
    re.IGNORECASE
)

LD50_ALT_PATTERN = re.compile(
    r'LD50\s+(?:in\s+)?([a-zA-Z]+)\s*'
    r'(?:\(\s*([a-zA-Z]+)\s*\))?\s*'
    r'[=:>< ]*\s*'
    r'(\d+\.?\d*)\s*'
    r'(mg/kg|g/kg|µg/kg|mcg/kg)',
    re.IGNORECASE
)


def _parse_ld50_text(text: str) -> list[dict]:
    """Parse LD50 entries from free text."""
    results = []

    for pattern in (LD50_PATTERN, LD50_ALT_PATTERN):
        for m in pattern.finditer(text):
            species = (m.group(1) or "unknown").lower().strip()
            route = (m.group(2) or "unknown").lower().strip()
            value = float(m.group(3))
            unit = m.group(4).lower()

            if unit == "g/kg":
                value *= 1000
            elif unit in ("µg/kg", "mcg/kg"):
                value /= 1000

            if species in ("rat", "mouse", "rabbit", "dog", "human", "cat",
                           "guinea", "monkey", "pig"):
                results.append({
                    "species": species,
                    "route": route,
                    "ld50_mg_kg": value,
                    "raw_text": text[:200],
                })

    if not results and "LD50" in text.upper():
        m = re.search(r'(\d+\.?\d*)\s*(mg/kg|g/kg)', text, re.IGNORECASE)
        if m:
            value = float(m.group(1))
            if "g/kg" in m.group(2).lower() and "mg" not in m.group(2).lower():
                value *= 1000
            species = "unknown"
            route = "unknown"
            for sp in ("rat", "mouse", "rabbit", "dog", "human"):
                if sp in text.lower():
                    species = sp
                    break
            for rt in ("oral", "intravenous", "iv", "subcutaneous", "sc",
                       "intraperitoneal", "ip", "inhalation"):
                if rt in text.lower():
                    route = "oral" if rt == "oral" else rt
                    break
            results.append({
                "species": species,
                "route": route,
                "ld50_mg_kg": value,
                "raw_text": text[:200],
            })

    return results


# ---------------------------------------------------------------------------
# PyTDC (optional)
# ---------------------------------------------------------------------------

def fetch_tdc_ld50_data() -> dict:
    """Try to load LD50 data from PyTDC. Returns {smiles: ld50_mg_kg}."""
    try:
        from tdc.single_pred import Tox
        data = Tox(name="LD50_Zhu")
        df = data.get_data()
        result = {}
        for _, row in df.iterrows():
            smiles = row.get("Drug", "")
            y = row.get("Y")
            if smiles and y is not None:
                result[smiles] = float(y)
        print(f"  [PyTDC] Loaded {len(result)} LD50 entries from LD50_Zhu")
        return result
    except Exception as e:
        print(f"  [PyTDC] Skipped (not available or failed): {e}")
        return {}


# ---------------------------------------------------------------------------
# Interspecies scaling & danger ranking
# ---------------------------------------------------------------------------

def compute_human_equivalent_dose(ld50_mg_kg: float, species: str) -> float | None:
    """BSA-based interspecies scaling to estimate human equivalent dose."""
    species = species.lower()
    if species == "human":
        return ld50_mg_kg
    animal_km = config.KM_SCALING.get(species)
    human_km = config.KM_SCALING["human"]
    if not animal_km:
        return None
    hed = ld50_mg_kg * (animal_km / human_km)
    return round(hed, 4)


def select_best_ld50(entries: list[dict]) -> dict | None:
    """Select the most relevant LD50 entry, preferring rat oral."""
    if not entries:
        return None

    species_prio = {s: i for i, s in enumerate(config.TOXICOLOGY_SPECIES_PRIORITY)}
    route_prio = {r: i for i, r in enumerate(config.TOXICOLOGY_ROUTE_PRIORITY)}

    def score(e):
        sp = species_prio.get(e.get("species", ""), 99)
        rt = route_prio.get(e.get("route", ""), 99)
        return (sp, rt)

    return min(entries, key=score)


def compute_therapeutic_index(ld50_mg_kg: float, species: str,
                               ec50_nM: float | None) -> float | None:
    """Estimate therapeutic index = LD50 / ED50 (using mu EC50 as proxy)."""
    if ec50_nM is None or ec50_nM <= 0:
        return None
    hed = compute_human_equivalent_dose(ld50_mg_kg, species)
    if hed is None or hed <= 0:
        return None
    ec50_mg_kg = ec50_nM * 1e-6 * 0.001
    if ec50_mg_kg <= 0:
        return None
    ti = hed / ec50_mg_kg
    return round(ti, 1)


def classify_danger(estimated_lethal_dose_mg: float | None) -> tuple[str, int]:
    """Classify danger level based on estimated human lethal dose."""
    if estimated_lethal_dose_mg is None:
        return "Unknown", 999

    if estimated_lethal_dose_mg < 1:
        return "Extreme", 1
    elif estimated_lethal_dose_mg < 10:
        return "Very High", 2
    elif estimated_lethal_dose_mg < 100:
        return "High", 3
    elif estimated_lethal_dose_mg < 1000:
        return "Moderate", 4
    else:
        return "Lower", 5


# ---------------------------------------------------------------------------
# Cross-reference builder
# ---------------------------------------------------------------------------

def build_ingredient_product_xref() -> dict:
    """Map each ingredient to all products containing it."""
    with open(config.REGISTRY_OUTPUT) as f:
        reg = json.load(f)

    xref = {}
    for drug in reg.get("opioid_drugs", []):
        for ing in drug.get("active_ingredients", []):
            if ing.get("is_opioid_component"):
                name = (ing.get("name") or "").lower()
                if not name:
                    continue
                xref.setdefault(name, []).append({
                    "rxcui": drug.get("rxcui"),
                    "drug_name": drug.get("drug_name"),
                    "schedule": drug.get("schedule"),
                    "tty": drug.get("tty"),
                })
    return xref


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("TOXICOLOGY FETCHER — Tier 3, Step 5")
    print("=" * 70)

    with open(config.PHARMACOLOGY_OUTPUT) as f:
        pharma = json.load(f)

    ingredient_pharmacology = pharma["ingredient_pharmacology"]
    print(f"\nLoaded pharmacology data for {len(ingredient_pharmacology)} ingredients")

    # Try PyTDC
    print("\n--- PyTDC LD50 data ---")
    tdc_data = fetch_tdc_ld50_data()

    # Per-ingredient toxicology
    print("\n--- Per-ingredient toxicology ---")
    danger_rankings = []

    for i, (name_lower, data) in enumerate(ingredient_pharmacology.items()):
        cid = data.get("pubchem_cid")
        smiles = data.get("smiles")
        print(f"\n[{i+1}/{len(ingredient_pharmacology)}] {name_lower}")

        # PubChem LD50
        ld50_entries = []
        if cid:
            ld50_entries = fetch_pubchem_toxicity(cid, name_lower)
            print(f"  PubChem LD50 entries: {len(ld50_entries)}")

        # PyTDC match by SMILES
        if tdc_data and smiles and smiles in tdc_data:
            tdc_val = tdc_data[smiles]
            ld50_entries.append({
                "species": "rat",
                "route": "oral",
                "ld50_mg_kg": tdc_val,
                "source": "PyTDC/LD50_Zhu",
                "raw_text": f"PyTDC LD50_Zhu: {tdc_val} mg/kg (rat, oral, predicted)",
            })
            print(f"  PyTDC match: {tdc_val} mg/kg")

        # Deduplicate
        seen = set()
        unique_entries = []
        for e in ld50_entries:
            key = (e.get("species"), e.get("route"), e.get("ld50_mg_kg"))
            if key not in seen:
                seen.add(key)
                unique_entries.append(e)
        ld50_entries = unique_entries

        data["ld50_data"] = ld50_entries

        # Best LD50 and human equivalent
        best = select_best_ld50(ld50_entries)
        estimated_lethal_mg = None
        if best:
            hed = compute_human_equivalent_dose(best["ld50_mg_kg"], best["species"])
            if hed:
                estimated_lethal_mg = round(hed * 70, 2)
                print(f"  Best LD50: {best['ld50_mg_kg']} mg/kg ({best['species']}, {best['route']})")
                print(f"  Human equivalent: {hed} mg/kg → {estimated_lethal_mg} mg for 70 kg")

        # Therapeutic index
        mu_ec50 = data.get("mu_ec50_nM")
        ti = None
        if best and mu_ec50:
            ti = compute_therapeutic_index(best["ld50_mg_kg"], best["species"], mu_ec50)
            if ti:
                print(f"  Therapeutic index: {ti}")
        data["therapeutic_index"] = ti

        # Danger classification
        danger_level, danger_rank = classify_danger(estimated_lethal_mg)
        data["estimated_human_lethal_dose_mg"] = estimated_lethal_mg
        data["danger_level"] = danger_level
        data["danger_rank"] = danger_rank
        print(f"  Danger: {danger_level} (rank {danger_rank})")

        danger_rankings.append({
            "ingredient": name_lower,
            "estimated_lethal_dose_mg": estimated_lethal_mg,
            "danger_level": danger_level,
            "danger_rank": danger_rank,
        })

    # Sort by danger
    danger_rankings.sort(key=lambda x: (x["danger_rank"], x.get("estimated_lethal_dose_mg") or 1e9))

    # Cross-reference
    print("\n--- Building ingredient-product cross-reference ---")
    xref = build_ingredient_product_xref()
    for name_lower, data in ingredient_pharmacology.items():
        data["products_containing"] = xref.get(name_lower, [])
        print(f"  {name_lower}: {len(data['products_containing'])} products")

    # Update metadata
    pharma["metadata"]["toxicology_added_at"] = datetime.now(timezone.utc).isoformat()
    pharma["metadata"]["step"] = "4+5"
    pharma["metadata"]["ingredients_with_ld50"] = sum(
        1 for d in ingredient_pharmacology.values() if d.get("ld50_data")
    )
    pharma["danger_rankings"] = danger_rankings

    # Save
    with open(config.PHARMACOLOGY_OUTPUT, "w") as f:
        json.dump(pharma, f, indent=2)

    with_ld50 = pharma["metadata"]["ingredients_with_ld50"]
    print("\n" + "=" * 70)
    print("TOXICOLOGY FETCHER — COMPLETE")
    print(f"  Ingredients with LD50 data: {with_ld50}")
    print(f"  Danger rankings:")
    for dr in danger_rankings:
        dose = dr['estimated_lethal_dose_mg']
        dose_str = f"{dose} mg" if dose else "unknown"
        print(f"    {dr['ingredient']:18s}  {dr['danger_level']:10s}  lethal dose: {dose_str}")
    print(f"  Saved to: {config.PHARMACOLOGY_OUTPUT}")
    print("=" * 70)


if __name__ == "__main__":
    main()
