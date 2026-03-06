"""
Opioid Registry — Runtime API
===============================
Loads the opioid registry and exposes helper functions for downstream code.
Uses a singleton/lazy-load pattern to avoid import-time side effects.

Usage:
    from opioid_track.core.registry import is_opioid, get_mme_factor
    if is_opioid("7052"):
        print("Morphine is an opioid")
"""

import json
import re
from opioid_track import config

# Module-level singleton
_REGISTRY: dict | None = None


def _load():
    """Load the registry from disk."""
    global _REGISTRY
    with open(config.REGISTRY_OUTPUT, "r") as f:
        _REGISTRY = json.load(f)


def _ensure_loaded():
    """Ensure the registry is loaded. Lazy-load on first access."""
    if _REGISTRY is None:
        _load()


def refresh():
    """Clear the cached registry and force a reload from disk."""
    global _REGISTRY
    _REGISTRY = None


def normalize_ndc(ndc_str: str) -> str:
    """Normalize an NDC code to 11-digit zero-padded format."""
    ndc_str = ndc_str.strip()
    ndc_clean = re.sub(r'[^0-9\-]', '', ndc_str)

    if '-' in ndc_clean:
        parts = ndc_clean.split('-')
        if len(parts) == 3:
            seg1 = parts[0].zfill(5)
            seg2 = parts[1].zfill(4)
            seg3 = parts[2].zfill(2)
        else:
            combined = ''.join(parts).zfill(11)
            seg1, seg2, seg3 = combined[:5], combined[5:9], combined[9:11]
    else:
        digits = ndc_clean.zfill(11)
        seg1, seg2, seg3 = digits[:5], digits[5:9], digits[9:11]

    return f"{seg1}{seg2}{seg3}"


def is_opioid(rxcui: str) -> bool:
    """Check if an RxCUI is a known opioid."""
    _ensure_loaded()
    for drug in _REGISTRY.get("opioid_drugs", []):
        if drug["rxcui"] == str(rxcui):
            return True
        for ing in drug.get("active_ingredients", []):
            if ing.get("rxcui") == str(rxcui):
                return True
    return False


def is_opioid_by_ndc(ndc: str) -> bool:
    """Check if an NDC code belongs to an opioid product."""
    _ensure_loaded()
    ndc_11 = normalize_ndc(ndc)
    ndc_lookup = _REGISTRY.get("ndc_lookup", {})
    entry = ndc_lookup.get(ndc_11)
    if entry:
        return entry.get("is_opioid", False)
    return False


def get_opioid_profile(rxcui: str) -> dict | None:
    """Get the full profile for an opioid drug by RxCUI."""
    _ensure_loaded()
    for drug in _REGISTRY.get("opioid_drugs", []):
        if drug["rxcui"] == str(rxcui):
            return drug
        for ing in drug.get("active_ingredients", []):
            if ing.get("rxcui") == str(rxcui):
                return drug
    return None


def get_mme_factor(ingredient_name: str) -> float | None:
    """Get the MME conversion factor for a named ingredient."""
    _ensure_loaded()
    mme_ref = _REGISTRY.get("mme_reference", {})
    cdc_factors = mme_ref.get("cdc_factors", {})
    name_lower = ingredient_name.lower().strip()

    if name_lower in cdc_factors:
        return cdc_factors[name_lower]["mme_factor"]
    return None


def calculate_daily_mme(ingredient_name: str, daily_dose_mg: float) -> dict:
    """Calculate daily MME for a given ingredient and dose.

    Returns dict with daily_mme, risk_level, mme_factor_used.
    """
    _ensure_loaded()
    mme_ref = _REGISTRY.get("mme_reference", {})
    cdc_factors = mme_ref.get("cdc_factors", {})
    methadone_tiers = mme_ref.get("methadone_tiers", [])
    thresholds = mme_ref.get("risk_thresholds", {})

    name_lower = ingredient_name.lower().strip()

    # Methadone: tiered conversion
    if name_lower == "methadone":
        factor = methadone_tiers[-1]["mme_factor"] if methadone_tiers else 12.0
        for tier in methadone_tiers:
            if daily_dose_mg <= tier["max_daily_dose_mg"]:
                factor = tier["mme_factor"]
                break
        daily_mme = daily_dose_mg * factor
    elif name_lower in cdc_factors:
        factor = cdc_factors[name_lower]["mme_factor"]
        daily_mme = daily_dose_mg * factor
    else:
        return {
            "daily_mme": None,
            "risk_level": "unknown",
            "mme_factor_used": None,
        }

    increased = thresholds.get("increased_risk_mme", 50)
    high = thresholds.get("high_risk_mme", 90)
    risk_level = "normal"
    if daily_mme >= high:
        risk_level = "high"
    elif daily_mme >= increased:
        risk_level = "increased"

    return {
        "daily_mme": round(daily_mme, 2),
        "risk_level": risk_level,
        "mme_factor_used": factor,
    }


def list_all_opioid_rxcuis() -> list[str]:
    """Return a list of all opioid RxCUIs in the registry."""
    _ensure_loaded()
    rxcuis = set()
    for drug in _REGISTRY.get("opioid_drugs", []):
        rxcuis.add(drug["rxcui"])
        for ing in drug.get("active_ingredients", []):
            if ing.get("rxcui"):
                rxcuis.add(ing["rxcui"])
    return sorted(rxcuis)


def list_all_opioid_ndcs() -> list[str]:
    """Return a list of all NDC codes classified as opioid."""
    _ensure_loaded()
    ndc_lookup = _REGISTRY.get("ndc_lookup", {})
    return [ndc for ndc, entry in ndc_lookup.items()
            if entry.get("is_opioid", False)]


def get_opioids_by_category(category: str) -> list[dict]:
    """Get all opioid drugs in a given category (e.g., 'synthetic')."""
    _ensure_loaded()
    return [drug for drug in _REGISTRY.get("opioid_drugs", [])
            if drug.get("opioid_category", "").lower() == category.lower()]


def get_opioids_by_schedule(schedule: str) -> list[dict]:
    """Get all opioid drugs with a given DEA schedule (e.g., 'CII')."""
    _ensure_loaded()
    return [drug for drug in _REGISTRY.get("opioid_drugs", [])
            if drug.get("schedule", "").upper() == schedule.upper()]


def get_drugs_containing_ingredient(ingredient_rxcui: str) -> list[dict]:
    """Get all drugs containing a specific ingredient RxCUI."""
    _ensure_loaded()
    results = []
    for drug in _REGISTRY.get("opioid_drugs", []):
        for ing in drug.get("active_ingredients", []):
            if ing.get("rxcui") == str(ingredient_rxcui):
                results.append(drug)
                break
    return results


def get_faers_baseline() -> dict:
    """Get the FAERS baseline snapshot."""
    _ensure_loaded()
    return _REGISTRY.get("faers_baseline", {})


def search_opioid_products(query_string: str) -> list[dict]:
    """Search for opioid products by name (e.g., 'Percocet')."""
    _ensure_loaded()
    query_lower = query_string.lower().strip()
    results = []
    
    for drug in _REGISTRY.get("opioid_drugs", []):
        if drug.get("tty") in ("SCD", "SBD"):
            if query_lower in drug["drug_name"].lower():
                results.append(drug)
    return results


def get_newly_approved_opioids(year: int) -> list[dict]:
    """Get opioid NDCs approved in a specific year or later (via OpenFDA)."""
    _ensure_loaded()
    results = []
    ndc_lookup = _REGISTRY.get("ndc_lookup", {})
    
    target_year = str(year)
    for ndc, entry in ndc_lookup.items():
        if entry.get("source") == "openfda-realtime" and entry.get("is_opioid"):
            start_date = entry.get("marketing_start_date", "")
            # marketing_start_date is YYYYMMDD
            if start_date and start_date[:4] >= target_year:
                results.append(entry)
                
    return results


def registry_version() -> str:
    """Get the registry version string."""
    _ensure_loaded()
    return _REGISTRY.get("metadata", {}).get("version", "unknown")


def registry_stats() -> dict:
    """Get summary statistics about the registry."""
    _ensure_loaded()
    metadata = _REGISTRY.get("metadata", {})
    return {
        "version": metadata.get("version", "unknown"),
        "generated_at": metadata.get("generated_at", "unknown"),
        "total_opioid_rxcuis": metadata.get("total_opioid_rxcuis", 0),
        "total_opioid_ndcs": metadata.get("total_opioid_ndcs", 0),
        "total_ndc_lookup_entries": metadata.get("total_ndc_lookup_entries", 0),
        "tier": metadata.get("tier", 0),
        "data_sources": metadata.get("data_sources", {}),
    }
