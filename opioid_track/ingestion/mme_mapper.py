"""
MME Mapper
===========
Downloads RxCUI→MME mapping from jbadger3/ml_4_pheno_ooe (MIT license)
and cross-validates against CDC Clinical Practice Guideline 2022 factors.

Usage:
    python -m opioid_track.ingestion.mme_mapper
"""

import json
import os
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


def download_jbadger_json():
    """Download rxcui_mme_mapping.json from jbadger3/ml_4_pheno_ooe if not cached."""
    os.makedirs(f"{config.OPIOID_DATA_DIR}/raw", exist_ok=True)

    if os.path.exists(config.JBADGER_MME_JSON_LOCAL):
        print(f"Using cached rxcui_mme_mapping.json from {config.JBADGER_MME_JSON_LOCAL}")
        with open(config.JBADGER_MME_JSON_LOCAL, "r") as f:
            return json.load(f)

    print("Downloading rxcui_mme_mapping.json from jbadger3/ml_4_pheno_ooe...")
    try:
        resp = retry_get(config.JBADGER_MME_JSON_URL, timeout=60)
        data = resp.json()
        with open(config.JBADGER_MME_JSON_LOCAL, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Downloaded rxcui_mme_mapping.json ({len(data)} entries)")
        return data
    except Exception as e:
        print(f"WARNING: Failed to download jbadger3 MME mapping: {e}")
        print("Falling back to CDC factors only.")
        return None


def inspect_and_parse_mme_json(raw_data):
    """Inspect the JSON schema and parse into a normalized rxcui→mme dict.

    Handles both {rxcui: float} and {rxcui: {field: value}} formats.
    """
    if not raw_data:
        return {}

    # Inspect first 3 entries
    sample_keys = list(raw_data.keys())[:3]
    print(f"\nJSON schema inspection:")
    for k in sample_keys:
        print(f"  Key: {k!r} → Value: {raw_data[k]!r}")

    rxcui_mme = {}
    for rxcui_str, value in raw_data.items():
        if isinstance(value, (int, float)):
            rxcui_mme[str(rxcui_str)] = {
                "mme_factor": float(value),
                "drug_name": "",
                "source": "jbadger3/ml_4_pheno_ooe",
            }
        elif isinstance(value, dict):
            # Adaptive: look for mme-related keys
            factor = None
            name = ""
            for k, v in value.items():
                kl = k.lower()
                if 'mme' in kl or 'factor' in kl or 'conversion' in kl:
                    try:
                        factor = float(v)
                    except (ValueError, TypeError):
                        pass
                if 'name' in kl or 'drug' in kl:
                    name = str(v)
            if factor is not None:
                rxcui_mme[str(rxcui_str)] = {
                    "mme_factor": factor,
                    "drug_name": name,
                    "source": "jbadger3/ml_4_pheno_ooe",
                }
        else:
            try:
                rxcui_mme[str(rxcui_str)] = {
                    "mme_factor": float(value),
                    "drug_name": "",
                    "source": "jbadger3/ml_4_pheno_ooe",
                }
            except (ValueError, TypeError):
                print(f"  WARNING: Skipping unparseable entry: {rxcui_str}={value!r}")

    print(f"Parsed {len(rxcui_mme)} RxCUI→MME mappings from jbadger3")
    return rxcui_mme


def resolve_ingredient_rxcui(ingredient_name):
    """Look up the RxCUI for a named ingredient via RxNorm API."""
    url = (f"{config.RXNAV_BASE}/rxcui.json"
           f"?name={ingredient_name}&search=1")
    try:
        resp = retry_get(url, delay_between=config.RXNAV_DELAY_SECONDS)
        data = resp.json()
        id_group = data.get("idGroup", {})
        rxcui_list = id_group.get("rxnormId", [])
        if rxcui_list:
            return rxcui_list[0]
    except Exception as e:
        print(f"  WARNING: RxNorm lookup failed for {ingredient_name}: {e}")
    return None


def cross_validate(rxcui_mme, cdc_factors):
    """Cross-validate jbadger3 RxCUI map against CDC named-ingredient factors."""
    print("\nCross-validating jbadger3 vs CDC factors...")
    discrepancies = []

    for name, cdc_factor in cdc_factors.items():
        rxcui = resolve_ingredient_rxcui(name)
        if not rxcui:
            print(f"  {name}: Could not resolve RxCUI")
            continue

        if rxcui in rxcui_mme:
            jbadger_factor = rxcui_mme[rxcui]["mme_factor"]
            ratio = abs(jbadger_factor - cdc_factor) / cdc_factor if cdc_factor else 0
            status = "OK" if ratio <= 0.20 else "DISCREPANCY"
            if status == "DISCREPANCY":
                discrepancies.append({
                    "ingredient": name,
                    "rxcui": rxcui,
                    "cdc_factor": cdc_factor,
                    "jbadger_factor": jbadger_factor,
                    "deviation_pct": round(ratio * 100, 1),
                })
            print(f"  {name} (RxCUI {rxcui}): CDC={cdc_factor}, "
                  f"jbadger={jbadger_factor} [{status}]")
        else:
            print(f"  {name} (RxCUI {rxcui}): Not in jbadger3 map")

    if discrepancies:
        print(f"\n  {len(discrepancies)} discrepancies found (CDC factors always win)")
    else:
        print(f"\n  No discrepancies found!")
    return discrepancies


def calculate_daily_mme(ingredient_name, daily_dose_mg, cdc_factors=None):
    """Calculate daily MME for a given ingredient and dose.

    Args:
        ingredient_name: Name of the opioid ingredient (case-insensitive).
        daily_dose_mg: Total daily dose in mg.
        cdc_factors: Optional dict of CDC factors (defaults to config).

    Returns:
        Dict with daily_mme, risk_level, mme_factor_used.
    """
    if cdc_factors is None:
        cdc_factors = config.CDC_MME_FACTORS

    name_lower = ingredient_name.lower().strip()

    # Special case: methadone uses tiered conversion
    if name_lower == "methadone":
        factor = config.METHADONE_MME_TIERS[-1][1]  # Default to highest
        for max_dose, tier_factor in config.METHADONE_MME_TIERS:
            if daily_dose_mg <= max_dose:
                factor = tier_factor
                break
        daily_mme = daily_dose_mg * factor
    elif name_lower in cdc_factors:
        factor = cdc_factors[name_lower]
        daily_mme = daily_dose_mg * factor
    else:
        return {
            "daily_mme": None,
            "risk_level": "unknown",
            "mme_factor_used": None,
            "error": f"No MME factor found for {ingredient_name}",
        }

    risk_level = "normal"
    if daily_mme >= 90:
        risk_level = "high"
    elif daily_mme >= 50:
        risk_level = "increased"

    return {
        "daily_mme": round(daily_mme, 2),
        "risk_level": risk_level,
        "mme_factor_used": factor,
    }


def main():
    """Run the full MME mapping pipeline."""
    print("=" * 60)
    print("MME Mapper — Building MME reference data")
    print("=" * 60)

    # Step 1: Download jbadger3 data
    raw_data = download_jbadger_json()

    # Step 2: Parse
    rxcui_mme = inspect_and_parse_mme_json(raw_data)

    # Step 3: Cross-validate
    cross_validate(rxcui_mme, config.CDC_MME_FACTORS)

    # Step 4: Build reference structure
    cdc_factors_ref = {}
    for name, factor in config.CDC_MME_FACTORS.items():
        cdc_factors_ref[name] = {
            "mme_factor": factor,
            "source": "CDC Clinical Practice Guideline 2022",
            "notes": "reference standard" if name == "morphine" else "per mg oral",
        }
    # Special notes
    if "fentanyl" in cdc_factors_ref:
        cdc_factors_ref["fentanyl"]["notes"] = "transdermal mcg/hr to MME"

    methadone_tiers = [
        {"max_daily_dose_mg": max_dose, "mme_factor": factor}
        for max_dose, factor in config.METHADONE_MME_TIERS
    ]

    reference = {
        "cdc_factors": cdc_factors_ref,
        "rxcui_mme_map": rxcui_mme,
        "methadone_tiers": methadone_tiers,
        "risk_thresholds": {
            "increased_risk_mme": 50,
            "high_risk_mme": 90,
        },
        "metadata": {
            "primary_rxcui_source": "jbadger3/ml_4_pheno_ooe",
            "named_ingredient_source": "CDC Clinical Practice Guideline 2022",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "rxcui_entries": len(rxcui_mme),
            "cdc_entries": len(cdc_factors_ref),
        },
    }

    # Step 5: Save
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.MME_REFERENCE_OUTPUT, "w") as f:
        json.dump(reference, f, indent=2)

    print(f"\n{'=' * 40}")
    print(f"MME Reference Summary")
    print(f"{'=' * 40}")
    print(f"CDC named factors:    {len(cdc_factors_ref)}")
    print(f"RxCUI MME mappings:   {len(rxcui_mme)}")
    print(f"Methadone tiers:      {len(methadone_tiers)}")
    print(f"\nSaved to {config.MME_REFERENCE_OUTPUT}")

    return reference


if __name__ == "__main__":
    main()
