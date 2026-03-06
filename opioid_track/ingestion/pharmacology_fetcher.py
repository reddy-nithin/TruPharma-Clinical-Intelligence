"""
Opioid Track — Pharmacology Fetcher (Tier 3, Step 4)
=====================================================
Fetches molecular-level receptor binding data from ChEMBL, GtoPdb, and PubChem
to explain WHY each substance is classified as an opioid.

Output: opioid_track/data/opioid_pharmacology.json

Sources:
    - ChEMBL (bioactivity: Ki, IC50, EC50 at opioid receptors, per compound)
    - GtoPdb (curated ligand-receptor interactions)
    - PubChem (chemical properties, pharmacokinetics)
"""

import json
import os
import re
import time
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get

RECEPTOR_EFFECTS = {
    "mu": "analgesia, euphoria, respiratory depression, and physical dependence",
    "kappa": "dysphoria, sedation, and spinal analgesia",
    "delta": "anxiolysis, mild analgesia, and convulsant activity",
    "nop": "anxiolysis and modulation of opioid reward",
}


# ---------------------------------------------------------------------------
# ChEMBL — per-ingredient queries (fast)
# ---------------------------------------------------------------------------

def _get_chembl_client():
    from chembl_webresource_client.new_client import new_client
    return new_client


def find_chembl_compound(ingredient_name: str) -> dict | None:
    """Look up a compound in ChEMBL by preferred name."""
    client = _get_chembl_client()
    try:
        results = client.molecule.filter(pref_name__iexact=ingredient_name)
        hits = list(results)
        if hits:
            return {
                "chembl_id": hits[0].get("molecule_chembl_id"),
                "pref_name": hits[0].get("pref_name"),
                "max_phase": hits[0].get("max_phase"),
            }
    except Exception as e:
        print(f"    [WARN] ChEMBL compound lookup failed for {ingredient_name}: {e}")
    return None


def fetch_compound_activities(chembl_id: str, ingredient_name: str) -> list[dict]:
    """Fetch bioactivity records for a specific compound across opioid receptor targets."""
    client = _get_chembl_client()
    target_ids = [info["chembl_id"] for info in config.CHEMBL_OPIOID_TARGETS.values()]
    all_records = []
    for target_id in target_ids:
        try:
            results = client.activity.filter(
                molecule_chembl_id=chembl_id,
                target_chembl_id=target_id,
                standard_type__in=["Ki", "IC50", "EC50"],
                standard_units="nM",
            ).only([
                "molecule_chembl_id", "target_chembl_id",
                "standard_type", "standard_value", "standard_units",
                "pchembl_value", "assay_description",
            ])
            records = list(results)
            all_records.extend(records)
            time.sleep(config.CHEMBL_DELAY_SECONDS)
        except Exception as e:
            print(f"    [WARN] ChEMBL activity query failed for {ingredient_name}/{target_id}: {e}")
    return all_records


def fetch_chembl_mechanisms(chembl_id: str) -> list[dict]:
    """Fetch mechanism of action from ChEMBL."""
    client = _get_chembl_client()
    try:
        results = client.mechanism.filter(molecule_chembl_id=chembl_id)
        return [
            {
                "action_type": r.get("action_type"),
                "mechanism_of_action": r.get("mechanism_of_action"),
                "target_name": r.get("target_name"),
            }
            for r in results
        ]
    except Exception as e:
        print(f"    [WARN] ChEMBL mechanism query failed for {chembl_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# GtoPdb — bulk fetch per receptor (small, curated datasets)
# ---------------------------------------------------------------------------

def fetch_gtopdb_interactions(gtopdb_id: int, receptor_name: str) -> list[dict]:
    """Fetch all ligand-receptor interactions from GtoPdb for one receptor."""
    url = f"{config.GTOPDB_API_BASE}/targets/{gtopdb_id}/interactions"
    try:
        resp = retry_get(url, delay_between=0.3,
                         headers={"Accept": "application/json",
                                  "User-Agent": "TruPharma-Opioid/1.0"})
        data = resp.json()
        print(f"    [GtoPdb] {receptor_name}: {len(data)} interactions")
        return data
    except Exception as e:
        print(f"    [WARN] GtoPdb query failed for {receptor_name}: {e}")
        return []


def fetch_all_gtopdb_data() -> dict:
    """Fetch curated interactions for all 4 opioid receptors."""
    all_data = {}
    for receptor, info in config.CHEMBL_OPIOID_TARGETS.items():
        interactions = fetch_gtopdb_interactions(info["gtopdb_id"], receptor)
        ligand_index = {}
        for ix in interactions:
            lig_name = (ix.get("ligandName") or ix.get("name") or "").strip().lower()
            if not lig_name:
                continue
            entry = {
                "ligand_id": ix.get("ligandId"),
                "type": ix.get("type"),
                "action": ix.get("action"),
                "affinity": ix.get("affinity"),
                "affinity_type": ix.get("affinityParameter"),
                "endogenous": ix.get("endogenous", False),
            }
            ligand_index.setdefault(lig_name, []).append(entry)
        all_data[receptor] = {
            "gtopdb_target_id": info["gtopdb_id"],
            "total_interactions": len(interactions),
            "by_ligand_name": ligand_index,
        }
    return all_data


# ---------------------------------------------------------------------------
# PubChem
# ---------------------------------------------------------------------------

def fetch_pubchem_properties(ingredient_name: str) -> dict | None:
    """Fetch chemical properties from PubChem."""
    props = "MolecularFormula,MolecularWeight,CanonicalSMILES,InChI,XLogP,TPSA"
    url = f"{config.PUBCHEM_API_BASE}/compound/name/{ingredient_name}/property/{props}/JSON"
    try:
        resp = retry_get(url, delay_between=0.15)
        data = resp.json()
        compounds = data.get("PropertyTable", {}).get("Properties", [])
        if compounds:
            c = compounds[0]
            return {
                "cid": c.get("CID"),
                "molecular_formula": c.get("MolecularFormula"),
                "molecular_weight": c.get("MolecularWeight"),
                "smiles": c.get("CanonicalSMILES"),
                "inchi": c.get("InChI"),
                "xlogp": c.get("XLogP"),
                "tpsa": c.get("TPSA"),
            }
    except Exception as e:
        print(f"    [WARN] PubChem properties failed for {ingredient_name}: {e}")
    return None


def fetch_pubchem_pharmacology(cid: int) -> dict:
    """Fetch PK data from PubChem PUG View."""
    url = (f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
           f"?heading=Pharmacology+and+Biochemistry")
    pk_data = {
        "half_life_hours": None,
        "onset_minutes": None,
        "duration_hours": None,
        "metabolism": None,
        "active_metabolites": [],
    }
    try:
        resp = retry_get(url, delay_between=0.3)
        data = resp.json()
        for sec in data.get("Record", {}).get("Section", []):
            _extract_pk_recursive(sec, pk_data)
    except Exception:
        pass
    return pk_data


def _extract_pk_recursive(section: dict, pk_data: dict):
    heading = (section.get("TOCHeading") or "").lower()
    infos = section.get("Information", [])

    if "half" in heading and "life" in heading and pk_data["half_life_hours"] is None:
        for info in infos:
            val = _str_val(info)
            if val:
                h = _parse_hours(val)
                if h:
                    pk_data["half_life_hours"] = h
                    break

    if "metabolism" in heading and pk_data["metabolism"] is None:
        for info in infos:
            val = _str_val(info)
            if val:
                pk_data["metabolism"] = val[:500]
                break

    for sub in section.get("Section", []):
        _extract_pk_recursive(sub, pk_data)


def _str_val(info: dict) -> str | None:
    svals = info.get("Value", {}).get("StringWithMarkup", [])
    return svals[0].get("String", "") if svals else None


def _parse_hours(text: str) -> float | None:
    t = text.lower()
    m = re.search(r'(\d+\.?\d*)\s*(?:to|[-–])\s*(\d+\.?\d*)\s*(hour|hr|min)', t)
    if m:
        avg = (float(m.group(1)) + float(m.group(2))) / 2
        return round(avg / 60, 2) if "min" in m.group(3) else round(avg, 2)
    m = re.search(r'(\d+\.?\d*)\s*(hour|hr|min)', t)
    if m:
        val = float(m.group(1))
        return round(val / 60, 2) if "min" in m.group(2) else round(val, 2)
    return None


# ---------------------------------------------------------------------------
# Affinity resolution
# ---------------------------------------------------------------------------

def _resolve_affinities(ingredient_lower: str, chembl_activities: list[dict],
                         gtopdb_data: dict) -> dict:
    """Build receptor affinity map combining ChEMBL + GtoPdb data."""
    target_id_to_receptor = {info["chembl_id"]: rec
                              for rec, info in config.CHEMBL_OPIOID_TARGETS.items()}
    affinities = {}

    for receptor in ("mu", "kappa", "delta", "nop"):
        best_ki = None
        best_action = None
        best_source = None

        target_chembl = config.CHEMBL_OPIOID_TARGETS[receptor]["chembl_id"]
        for rec in chembl_activities:
            if rec.get("target_chembl_id") != target_chembl:
                continue
            if rec.get("standard_type") != "Ki":
                continue
            try:
                ki = float(rec["standard_value"])
            except (TypeError, ValueError):
                continue
            pchembl = float(rec.get("pchembl_value") or 0)
            if best_ki is None or pchembl > (affinities.get(receptor, {}).get("pchembl") or 0) or ki < best_ki:
                best_ki = ki
                best_source = "ChEMBL"

        gtopdb_receptor = gtopdb_data.get(receptor, {}).get("by_ligand_name", {})
        gtopdb_entries = gtopdb_receptor.get(ingredient_lower, [])
        for ix in gtopdb_entries:
            aff_type = (ix.get("affinity_type") or "").lower()
            try:
                aff_val = float(ix["affinity"])
            except (TypeError, ValueError):
                continue
            ki_nm = 10 ** (9 - aff_val) if aff_type in ("pki", "pkb", "pkd") else aff_val
            if ki_nm <= 0:
                continue
            action = ix.get("action", "")
            if best_ki is None or ki_nm < best_ki:
                best_ki = ki_nm
                best_action = action
                best_source = "GtoPdb"

        if best_ki is not None:
            entry = {"ki_nM": round(best_ki, 3), "source": best_source}
            if best_action:
                entry["action"] = best_action
            affinities[receptor] = entry

    return affinities


def _get_mu_ec50(chembl_activities: list[dict]) -> float | None:
    """Get best EC50 at mu receptor from ChEMBL activities."""
    mu_target = config.CHEMBL_OPIOID_TARGETS["mu"]["chembl_id"]
    best = None
    for rec in chembl_activities:
        if rec.get("target_chembl_id") != mu_target:
            continue
        if rec.get("standard_type") != "EC50":
            continue
        try:
            val = float(rec["standard_value"])
        except (TypeError, ValueError):
            continue
        if best is None or val < best:
            best = val
    return best


# ---------------------------------------------------------------------------
# Explanation generator
# ---------------------------------------------------------------------------

def generate_why_opioid(name: str, affinities: dict, mechanisms: list) -> str:
    primary_receptor = None
    primary_ki = None
    primary_action = "agonist"

    for rec in ("mu", "kappa", "delta", "nop"):
        aff = affinities.get(rec)
        if aff and (primary_ki is None or aff["ki_nM"] < primary_ki):
            primary_ki = aff["ki_nM"]
            primary_receptor = rec
            primary_action = aff.get("action", "agonist") or "agonist"

    if not primary_receptor:
        return (f"{name.capitalize()} is classified as an opioid based on its "
                f"pharmacologic class, but detailed receptor binding data is not available.")

    gene = config.CHEMBL_OPIOID_TARGETS[primary_receptor]["gene"]
    effects = RECEPTOR_EFFECTS.get(primary_receptor, "opioid effects")

    selectivity = ""
    if primary_receptor == "mu" and affinities.get("kappa", {}).get("ki_nM"):
        ratio = affinities["kappa"]["ki_nM"] / primary_ki if primary_ki else 0
        if ratio > 10:
            selectivity = f", showing {ratio:.0f}-fold selectivity over kappa"
        elif ratio > 3:
            selectivity = f", with moderate selectivity over kappa ({ratio:.1f}-fold)"

    mech_desc = ""
    if mechanisms:
        actions = [m["mechanism_of_action"] for m in mechanisms if m.get("mechanism_of_action")]
        if actions:
            mech_desc = f" {actions[0]}."

    action_word = primary_action.lower() if primary_action else "agonist"
    if "antag" in action_word:
        action_word = "antagonist"
    elif "partial" in action_word:
        action_word = "partial agonist"
    elif "agon" in action_word:
        action_word = "full agonist"
    else:
        action_word = "ligand"

    return (
        f"{name.capitalize()} is classified as an opioid because it acts as a {action_word} "
        f"at the {primary_receptor} opioid receptor ({gene}) with Ki = {primary_ki:.1f} nM"
        f"{selectivity}.{mech_desc} Its primary opioid effects — {effects} — "
        f"are mediated through {primary_receptor} receptor activation."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def get_opioid_ingredients() -> list[dict]:
    with open(config.REGISTRY_OUTPUT, "r") as f:
        reg = json.load(f)
    ingredients = {}
    for drug in reg.get("opioid_drugs", []):
        for ing in drug.get("active_ingredients", []):
            if ing.get("is_opioid_component"):
                name = (ing.get("name") or "").strip()
                if name and name.lower() not in ingredients:
                    ingredients[name.lower()] = {
                        "name": name, "rxcui": ing.get("rxcui"),
                    }
    return list(ingredients.values())


def build_pharmacology_data() -> dict:
    print("=" * 70)
    print("PHARMACOLOGY FETCHER — Tier 3, Step 4")
    print("=" * 70)

    ingredients = get_opioid_ingredients()
    print(f"\nFound {len(ingredients)} unique opioid ingredients in registry")

    # GtoPdb: small curated datasets, fetch in bulk
    print("\n--- GtoPdb receptor interactions ---")
    gtopdb_data = fetch_all_gtopdb_data()

    # Per-ingredient processing
    print("\n--- Per-ingredient pharmacology ---")
    morphine_ki_mu = None
    ingredient_pharmacology = {}
    receptor_target_stats = {r: {"chembl_hits": 0, "gtopdb_hits": 0}
                             for r in config.CHEMBL_OPIOID_TARGETS}

    for i, ing_info in enumerate(ingredients):
        name = ing_info["name"]
        name_lower = name.lower()
        rxcui = ing_info["rxcui"]
        print(f"\n[{i+1}/{len(ingredients)}] {name} (RxCUI: {rxcui})")

        # PubChem properties
        props = fetch_pubchem_properties(name)
        cid = props.get("cid") if props else None
        print(f"  PubChem: CID={cid}, MW={props.get('molecular_weight') if props else 'N/A'}")

        # ChEMBL compound ID
        chembl_compound = find_chembl_compound(name)
        chembl_id = chembl_compound.get("chembl_id") if chembl_compound else None
        print(f"  ChEMBL: {chembl_id or 'not found'}")
        time.sleep(config.CHEMBL_DELAY_SECONDS)

        # ChEMBL activities for this compound at opioid receptor targets
        chembl_activities = []
        if chembl_id:
            chembl_activities = fetch_compound_activities(chembl_id, name)
            print(f"  ChEMBL activities: {len(chembl_activities)} records at opioid targets")

        # Mechanisms
        mechanisms = []
        if chembl_id:
            mechanisms = fetch_chembl_mechanisms(chembl_id)
            time.sleep(config.CHEMBL_DELAY_SECONDS)

        # Resolve affinities from ChEMBL + GtoPdb
        affinities = _resolve_affinities(name_lower, chembl_activities, gtopdb_data)

        # Track morphine Ki at mu for potency calculations
        if name_lower == "morphine" and "mu" in affinities:
            morphine_ki_mu = affinities["mu"]["ki_nM"]

        # EC50 at mu (for therapeutic index in toxicology step)
        mu_ec50 = _get_mu_ec50(chembl_activities)

        # Potency vs morphine (second pass later for early-processed drugs)
        potency = None
        if morphine_ki_mu and affinities.get("mu", {}).get("ki_nM"):
            potency = round(morphine_ki_mu / affinities["mu"]["ki_nM"], 3)

        # Why it's an opioid
        why = generate_why_opioid(name, affinities, mechanisms)

        # PK data from PubChem
        pk_data = {"half_life_hours": None, "onset_minutes": None,
                    "duration_hours": None, "metabolism": None,
                    "active_metabolites": []}
        if cid:
            pk_data = fetch_pubchem_pharmacology(cid)

        ingredient_pharmacology[name_lower] = {
            "rxcui_ingredient": rxcui,
            "pubchem_cid": cid,
            "chembl_id": chembl_id,
            "smiles": props.get("smiles") if props else None,
            "molecular_formula": props.get("molecular_formula") if props else None,
            "molecular_weight": props.get("molecular_weight") if props else None,
            "xlogp": props.get("xlogp") if props else None,
            "receptor_affinities": affinities,
            "mu_ec50_nM": mu_ec50,
            "mechanisms_of_action": mechanisms,
            "why_its_an_opioid": why,
            "potency_vs_morphine": potency,
            "ld50_data": [],
            "therapeutic_index": None,
            "half_life_hours": pk_data.get("half_life_hours"),
            "onset_minutes": pk_data.get("onset_minutes"),
            "duration_hours": pk_data.get("duration_hours"),
            "metabolism": pk_data.get("metabolism"),
            "active_metabolites": pk_data.get("active_metabolites", []),
        }

        aff_str = ", ".join(f"{r}={a['ki_nM']}" for r, a in affinities.items())
        print(f"  Affinities: {aff_str or 'none found'}")

    # Ensure morphine = 1.0 and compute potency for all
    if "morphine" in ingredient_pharmacology:
        ingredient_pharmacology["morphine"]["potency_vs_morphine"] = 1.0

    if morphine_ki_mu:
        for name_lower, data in ingredient_pharmacology.items():
            if data["potency_vs_morphine"] is None:
                mu_ki = data["receptor_affinities"].get("mu", {}).get("ki_nM")
                if mu_ki:
                    data["potency_vs_morphine"] = round(morphine_ki_mu / mu_ki, 3)

    # Receptor target summary
    receptor_targets = {}
    for receptor, info in config.CHEMBL_OPIOID_TARGETS.items():
        receptor_targets[receptor] = {
            "chembl_id": info["chembl_id"],
            "gene": info["gene"],
            "uniprot": info["uniprot"],
            "gtopdb_id": info["gtopdb_id"],
            "gtopdb_interactions": gtopdb_data[receptor]["total_interactions"],
        }

    with_data = sum(1 for d in ingredient_pharmacology.values() if d["receptor_affinities"])

    output = {
        "metadata": {
            "sources": ["ChEMBL", "GtoPdb", "PubChem"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tier": 3,
            "step": 4,
            "total_ingredients": len(ingredient_pharmacology),
            "ingredients_with_receptor_data": with_data,
        },
        "receptor_targets": receptor_targets,
        "ingredient_pharmacology": ingredient_pharmacology,
    }
    return output


def main():
    output = build_pharmacology_data()
    os.makedirs(os.path.dirname(config.PHARMACOLOGY_OUTPUT), exist_ok=True)
    with open(config.PHARMACOLOGY_OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    meta = output["metadata"]
    print("\n" + "=" * 70)
    print("PHARMACOLOGY FETCHER — COMPLETE")
    print(f"  Total ingredients: {meta['total_ingredients']}")
    print(f"  With receptor data: {meta['ingredients_with_receptor_data']}")
    print(f"  Saved to: {config.PHARMACOLOGY_OUTPUT}")
    print("=" * 70)


if __name__ == "__main__":
    main()
