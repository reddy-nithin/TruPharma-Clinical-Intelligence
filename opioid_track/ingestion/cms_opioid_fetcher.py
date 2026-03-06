"""
CMS Opioid Prescribing Fetcher
================================
Ingests CMS Medicare Part D opioid prescribing data from two sources:

1. **Geographic prescribing**: State/county opioid prescribing rates, claims,
   and prescriber counts via the CMS Socrata API (data.cms.gov).
2. **Provider-Drug prescribing**: Provider-level opioid prescribing filtered to
   opioid ingredients from the Tier 1 registry. High prescribers are flagged
   at the 99th percentile per state+specialty.

Follows Tier 1 conventions: warn-and-continue error handling, print-based
logging, JSON output with metadata block.

Usage:
    python -m opioid_track.ingestion.cms_opioid_fetcher
"""

import csv
import io
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone

import requests

from opioid_track import config
from opioid_track.ingestion import retry_get


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_opioid_ingredient_names() -> list[str]:
    """Build a lowercase list of opioid ingredient names from the Tier 1 registry.

    We pull ingredient names directly from the registry JSON rather than
    importing the registry module to avoid heavy loading during development.
    Falls back to config.MUST_INCLUDE_OPIOIDS if the registry file is missing.
    """
    try:
        with open(config.REGISTRY_OUTPUT, "r") as f:
            registry = json.load(f)
        names = set()
        for drug in registry.get("opioid_drugs", []):
            # Collect IN/MIN tty ingredient names
            for ing in drug.get("active_ingredients", []):
                if ing.get("tty") in ("IN", "MIN"):
                    names.add(ing["name"].lower())
            # Also add the drug_name itself for IN entries
            if drug.get("tty") == "IN":
                names.add(drug["drug_name"].lower())
        print(f"  Loaded {len(names)} opioid ingredient names from registry")
        return sorted(names)
    except FileNotFoundError:
        print("  WARNING: Registry not found, falling back to MUST_INCLUDE_OPIOIDS")
        return [n.lower() for n in config.MUST_INCLUDE_OPIOIDS]


def _is_opioid_drug(generic_name: str, opioid_names: list[str]) -> bool:
    """Case-insensitive substring match against the opioid ingredient list."""
    if not generic_name:
        return False
    gn_lower = generic_name.lower()
    for opioid in opioid_names:
        if opioid in gn_lower or gn_lower in opioid:
            return True
    return False


def _standardize_fips(fips_code: str | None) -> str | None:
    """Standardize a FIPS code to 5-digit zero-padded form.

    State FIPS: 2-digit. County FIPS: 5-digit (2-digit state + 3-digit county).
    Returns None for national-level or invalid entries.
    """
    if not fips_code:
        return None
    fips_str = str(fips_code).strip()
    # Remove any non-digit characters
    fips_clean = "".join(c for c in fips_str if c.isdigit())
    if not fips_clean:
        return None
    if len(fips_clean) <= 2:
        # State-level FIPS
        return fips_clean.zfill(2)
    # County-level FIPS
    return fips_clean.zfill(5)


def _safe_float(val) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# CMS Data API — Geographic Prescribing
# ---------------------------------------------------------------------------

# CMS data API v1 dataset UUIDs (primary — CMS migrated off Socrata in 2024)
CMS_GEO_DATASET_UUID = "94d00f36-73ce-4520-9b3f-83cd3cded25c"
CMS_PROVIDER_DRUG_DATASET_UUID = "9552739e-3d05-4c1b-8eff-ecabf391e2e5"

# Legacy Socrata resource IDs (fallback — most return 410 Gone now)
CMS_GEO_RESOURCE_IDS = [
    "yb2j-f3fp",  # 2023 release
    "e4ka-3ncx",  # 2022 release
    "6wg9-kwip",  # 2021 release
]


def _fetch_cms_data_api_paginated(dataset_uuid: str, label: str = "",
                                   page_size: int = 5000,
                                   max_records: int = 200000) -> list[dict]:
    """Fetch records from CMS data API v1 with pagination.

    CMS data API v1 uses ?size=N&offset=M parameters (not Socrata syntax).
    Returns all fetched records, or an empty list on failure.
    """
    all_records = []
    offset = 0
    print(f"  Querying {label} via CMS data API v1...")

    while offset < max_records:
        url = (f"https://data.cms.gov/data-api/v1/dataset"
               f"/{dataset_uuid}/data?size={page_size}&offset={offset}")
        try:
            resp = retry_get(url, delay_between=0.15)
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"  WARNING: {label} unreachable: {e}")
                return []
            print(f"  WARNING: Pagination error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break

        all_records.extend(batch)
        if len(all_records) % 10000 == 0 or len(batch) < page_size:
            print(f"    Fetched {len(all_records)} records so far...")

        if len(batch) < page_size:
            break  # Last page
        offset += page_size
        time.sleep(0.1)

    if all_records:
        print(f"  ✓ Total {label} records: {len(all_records)}")
    return all_records


def _discover_cms_dataset_uuid(keyword: str) -> str | None:
    """Discover a CMS dataset UUID by searching the data.json catalog."""
    print(f"  Searching CMS data.json catalog for: {keyword}")
    try:
        resp = retry_get("https://data.cms.gov/data.json",
                         delay_between=0.1, timeout=60)
        catalog = resp.json()
        for ds in catalog.get("dataset", []):
            title = ds.get("title", "").lower()
            if all(w in title for w in keyword.lower().split()):
                identifier = ds.get("identifier", "")
                # Extract UUID from identifier URL
                # e.g., "https://data.cms.gov/data-api/v1/dataset/{uuid}/data-viewer"
                if "/dataset/" in identifier:
                    uuid = identifier.split("/dataset/")[1].split("/")[0]
                    print(f"  Discovered UUID: {uuid} (from: {ds.get('title', '')})")
                    return uuid
    except Exception as e:
        print(f"  WARNING: Catalog search failed: {e}")
    return None


def fetch_geographic_prescribing() -> list[dict]:
    """Fetch Medicare Part D Opioid Prescribing by Geography data.

    Tries CMS data API v1 first (primary), then catalog discovery,
    then legacy Socrata IDs as fallback.

    Returns a list of geographic prescribing records.
    """
    print("\n--- Fetching CMS Geographic Prescribing Data ---")

    # Strategy 1: CMS data API v1 with known UUID (primary)
    records = _fetch_cms_data_api_paginated(
        CMS_GEO_DATASET_UUID,
        label="CMS Geo (Part D Opioid Prescribing)"
    )
    if records:
        return records

    # Strategy 2: Discover UUID from catalog
    discovered_uuid = _discover_cms_dataset_uuid(
        "Medicare Part D Opioid Prescribing Rates Geography")
    if discovered_uuid and discovered_uuid != CMS_GEO_DATASET_UUID:
        records = _fetch_cms_data_api_paginated(
            discovered_uuid,
            label=f"CMS Geo (discovered: {discovered_uuid})"
        )
        if records:
            return records

    # Strategy 3: Legacy Socrata endpoints (most return 410 now)
    for resource_id in CMS_GEO_RESOURCE_IDS:
        records = _fetch_socrata_paginated(
            f"https://data.cms.gov/resource/{resource_id}.json",
            label=f"CMS Geo Socrata ({resource_id})"
        )
        if records:
            return records

    print("  WARNING: All CMS geographic data sources failed. "
          "Will produce empty geographic section.")
    return []


def _fetch_socrata_paginated(base_url: str, label: str = "",
                             limit: int = 5000,
                             max_records: int = 200000) -> list[dict]:
    """Fetch records from a Socrata API endpoint with pagination.

    Returns all fetched records, or an empty list on failure.
    """
    all_records = []
    offset = 0
    print(f"  Querying {label}...")

    while offset < max_records:
        url = f"{base_url}?$limit={limit}&$offset={offset}"
        try:
            resp = retry_get(url, delay_between=0.1)
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"  WARNING: {label} unreachable: {e}")
                return []
            print(f"  WARNING: Pagination error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break

        all_records.extend(batch)
        print(f"    Fetched {len(all_records)} records so far...")

        if len(batch) < limit:
            break  # Last page
        offset += limit
        time.sleep(0.1)

    if all_records:
        print(f"  ✓ Total geographic records: {len(all_records)}")
    return all_records


def _parse_geographic_records(raw_records: list[dict]) -> list[dict]:
    """Parse raw CMS geographic prescribing records into standardized format.

    Handles varying column names across dataset versions.
    """
    parsed = []
    # Map possible column names to our standard fields
    field_maps = {
        "geo_level": ["prscrbr_geo_lvl", "geo_lvl", "prscrbr_geo_level"],
        "geo_desc": ["prscrbr_geo_desc", "geo_desc", "geography_description",
                      "prscrbr_geo_nm"],
        "geo_code": ["prscrbr_geo_cd", "geo_cd", "fips_code", "geo_code"],
        "opioid_claims": ["tot_opioid_clms", "opioid_claims",
                          "total_opioid_claims"],
        "prescribing_rate": ["opioid_prscrbng_rate", "opioid_prescribing_rate",
                             "opioid_rate"],
        "prescriber_count": ["tot_opioid_prscrbrs", "opioid_prescribers",
                             "total_opioid_prescribers"],
        "yoy_change": ["opioid_prscrbng_rate_1y_chg", "yoy_change",
                        "opioid_rate_change"],
        "year": ["year", "prscrbr_year", "data_year"],
    }

    def _get_field(record: dict, field_key: str):
        """Try multiple column name variants to find a value."""
        for col_name in field_maps.get(field_key, []):
            # Try exact match
            if col_name in record:
                return record[col_name]
            # Try case-insensitive
            for k, v in record.items():
                if k.lower() == col_name.lower():
                    return v
        return None

    for raw in raw_records:
        geo_level = _get_field(raw, "geo_level")
        geo_desc = _get_field(raw, "geo_desc") or ""
        geo_code = _get_field(raw, "geo_code")
        fips = _standardize_fips(geo_code)

        # Determine state and county from geo_desc and geo_level
        state = ""
        county = ""
        geo_lvl_str = str(geo_level).lower() if geo_level else ""

        if geo_lvl_str == "national" or geo_desc.lower() == "national":
            state = "National"
        elif geo_lvl_str in ("state", "st"):
            state = geo_desc
        elif geo_lvl_str in ("county", "ct"):
            county = geo_desc
            # Try to extract state from county name (e.g., "Autauga County, AL")
            if "," in geo_desc:
                parts = geo_desc.rsplit(",", 1)
                county = parts[0].strip()
                state = parts[1].strip()

        record = {
            "fips_code": fips,
            "state": state,
            "county": county,
            "geo_level": geo_lvl_str or "unknown",
            "year": _safe_int(_get_field(raw, "year")),
            "total_opioid_claims": _safe_int(_get_field(raw, "opioid_claims")),
            "total_opioid_prescribers": _safe_int(
                _get_field(raw, "prescriber_count")),
            "opioid_prescribing_rate": _safe_float(
                _get_field(raw, "prescribing_rate")),
            "year_over_year_change": _safe_float(
                _get_field(raw, "yoy_change")),
        }
        parsed.append(record)

    return parsed


# ---------------------------------------------------------------------------
# CMS Provider-Drug Data (large CSV, chunked processing)
# ---------------------------------------------------------------------------

# Known Socrata resource IDs for Provider-Drug data
CMS_PROVIDER_DRUG_RESOURCE_IDS = [
    "77gb-8z53",  # 2023 release
    "4eya-endk",  # 2022 release
]


def fetch_provider_drug_data(opioid_names: list[str]) -> list[dict]:
    """Fetch and filter CMS Medicare Part D Provider-Drug data for opioids.

    This dataset is very large (1.38M+ rows). We stream it in chunks via
    the CMS data API v1 and filter to opioid rows only.

    Args:
        opioid_names: Lowercase list of opioid ingredient names for matching.

    Returns:
        List of opioid prescriber records (filtered to opioids, most recent year).
    """
    print("\n--- Fetching CMS Provider-Drug Data ---")

    # Strategy 1: CMS data API v1 with known UUID (primary)
    records = _fetch_provider_drug_cms_api(
        CMS_PROVIDER_DRUG_DATASET_UUID, opioid_names,
        label="Provider-Drug (CMS API v1)"
    )
    if records:
        return records

    # Strategy 2: Legacy Socrata endpoints (fallback)
    for resource_id in CMS_PROVIDER_DRUG_RESOURCE_IDS:
        records = _fetch_provider_drug_socrata(resource_id, opioid_names)
        if records:
            return records

    print("  WARNING: All CMS Provider-Drug sources failed. "
          "Will produce empty provider section.")
    return []


def _fetch_provider_drug_cms_api(dataset_uuid: str,
                                  opioid_names: list[str],
                                  label: str = "") -> list[dict]:
    """Fetch provider-drug data via CMS data API v1, filtering each page
    for opioid rows.

    The full dataset is 1.38M+ rows. We paginate through and filter
    in-flight, keeping only opioid rows. Returns the most recent year only.
    """
    print(f"  Trying {label} (UUID: {dataset_uuid})...")
    page_size = 5000
    offset = 0
    max_offset = 500_000  # Safety cap — we don't need all 1.38M rows
    all_opioid_rows = []
    years_seen = set()
    total_scanned = 0

    while offset < max_offset:
        url = (f"https://data.cms.gov/data-api/v1/dataset"
               f"/{dataset_uuid}/data?size={page_size}&offset={offset}")
        try:
            resp = retry_get(url, delay_between=0.15)
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"    WARNING: {label} unreachable: {e}")
                return []
            print(f"    WARNING: Page error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break

        total_scanned += len(batch)

        for row in batch:
            gnrc_name = (row.get("Gnrc_Name") or row.get("gnrc_name")
                         or row.get("generic_drug_name") or "")
            if _is_opioid_drug(gnrc_name, opioid_names):
                all_opioid_rows.append(row)
                yr = (row.get("Year") or row.get("year")
                      or row.get("Prscrbr_Year") or "")
                if yr:
                    years_seen.add(str(yr))

        if total_scanned % 50000 == 0 or len(batch) < page_size:
            print(f"    Scanned {total_scanned} rows, "
                  f"found {len(all_opioid_rows)} opioid rows...")

        if len(batch) < page_size:
            break
        offset += page_size
        time.sleep(0.05)

    if not all_opioid_rows:
        return []

    print(f"  ✓ Found {len(all_opioid_rows)} opioid prescriber rows "
          f"across years: {sorted(years_seen)}")

    # Keep only the most recent year
    if years_seen:
        most_recent = max(years_seen)
        all_opioid_rows = [
            r for r in all_opioid_rows
            if str(r.get("Year") or r.get("year")
                   or r.get("Prscrbr_Year") or "") == most_recent
        ]
        print(f"  Filtered to most recent year ({most_recent}): "
              f"{len(all_opioid_rows)} rows")

    return all_opioid_rows

def _fetch_provider_drug_socrata(resource_id: str,
                                  opioid_names: list[str]) -> list[dict]:
    """Fetch provider-drug data via Socrata API, filtering server-side where
    possible and client-side for opioid matching.

    We fetch in pages and filter each page against the opioid ingredient list.
    Only the most recent year is kept (most recent year seen in responses).
    """
    print(f"  Trying Socrata provider-drug endpoint: {resource_id}")
    base_url = f"https://data.cms.gov/resource/{resource_id}.json"
    limit = 5000
    offset = 0
    max_offset = 2_000_000  # Safety cap
    all_opioid_rows = []
    years_seen = set()
    total_scanned = 0

    while offset < max_offset:
        url = f"{base_url}?$limit={limit}&$offset={offset}"
        try:
            resp = retry_get(url, delay_between=0.15)
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"    WARNING: Provider-drug {resource_id} unreachable: {e}")
                return []
            print(f"    WARNING: Page error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break

        total_scanned += len(batch)

        for row in batch:
            gnrc_name = (row.get("gnrc_name") or row.get("Gnrc_Name")
                         or row.get("generic_drug_name") or "")
            if _is_opioid_drug(gnrc_name, opioid_names):
                all_opioid_rows.append(row)
                yr = (row.get("year") or row.get("prscrbr_year")
                      or row.get("data_year"))
                if yr:
                    years_seen.add(str(yr))

        if total_scanned % 50000 == 0 or len(batch) < limit:
            print(f"    Scanned {total_scanned} rows, "
                  f"found {len(all_opioid_rows)} opioid rows...")

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(0.05)

    if not all_opioid_rows:
        return []

    print(f"  ✓ Found {len(all_opioid_rows)} opioid prescriber rows "
          f"across years: {sorted(years_seen)}")

    # Keep only the most recent year
    if years_seen:
        most_recent = max(years_seen)
        all_opioid_rows = [
            r for r in all_opioid_rows
            if str(r.get("year") or r.get("prscrbr_year")
                   or r.get("data_year") or "") == most_recent
        ]
        print(f"  Filtered to most recent year ({most_recent}): "
              f"{len(all_opioid_rows)} rows")

    return all_opioid_rows


def _parse_provider_records(raw_rows: list[dict],
                             opioid_names: list[str]) -> list[dict]:
    """Parse raw provider-drug rows into standardized provider records.

    Groups by NPI and aggregates opioid prescribing across drugs.
    """
    # Group by NPI
    npi_groups = defaultdict(list)
    for row in raw_rows:
        npi = (row.get("prscrbr_npi") or row.get("npi")
               or row.get("Prscrbr_NPI") or "unknown")
        npi_groups[npi].append(row)

    providers = []
    for npi, rows in npi_groups.items():
        first = rows[0]
        specialty = (first.get("prscrbr_type") or first.get("specialty")
                     or first.get("Prscrbr_Type") or "Unknown")
        state = (first.get("prscrbr_state_abrvtn")
                 or first.get("prscrbr_state") or first.get("state")
                 or first.get("Prscrbr_State_Abrvtn") or "")

        total_claims = 0
        total_cost = 0.0
        total_bene = 0
        top_drugs = {}

        for r in rows:
            claims = _safe_int(r.get("tot_clms") or r.get("total_claims")
                              or r.get("Tot_Clms") or 0) or 0
            cost = _safe_float(r.get("tot_drug_cst")
                              or r.get("total_drug_cost")
                              or r.get("Tot_Drug_Cst") or 0) or 0.0
            bene = _safe_int(r.get("tot_benes") or r.get("bene_count")
                            or r.get("Tot_Benes") or 0) or 0
            drug = (r.get("gnrc_name") or r.get("Gnrc_Name")
                    or r.get("generic_drug_name") or "Unknown")

            total_claims += claims
            total_cost += cost
            total_bene += bene

            if drug not in top_drugs:
                top_drugs[drug] = 0
            top_drugs[drug] += claims

        # Sort top drugs by claims descending, keep top 5
        sorted_drugs = sorted(top_drugs.items(), key=lambda x: x[1],
                               reverse=True)[:5]

        providers.append({
            "npi": npi,
            "specialty": specialty,
            "state": state,
            "opioid_claims": total_claims,
            "opioid_drug_cost": round(total_cost, 2),
            "opioid_bene_count": total_bene,
            "is_high_prescriber": False,  # Will be set by flag_high_prescribers
            "top_opioid_drugs": [
                {"drug_name": name, "claims": cnt}
                for name, cnt in sorted_drugs
            ],
        })

    return providers


def flag_high_prescribers(providers: list[dict]) -> list[dict]:
    """Flag high prescribers — those above the 99th percentile of opioid
    claims within their state+specialty group.

    Modifies records in-place and returns the list.
    """
    print("\n--- Flagging High Prescribers (99th percentile) ---")

    # Group by state + specialty
    groups = defaultdict(list)
    for p in providers:
        key = (p["state"], p["specialty"])
        groups[key].append(p)

    flagged_count = 0
    for (state, specialty), group in groups.items():
        if len(group) < 10:
            # Skip tiny groups — not meaningful for percentile
            continue

        claims_list = sorted([p["opioid_claims"] for p in group])
        idx_99 = int(len(claims_list) * 0.99)
        threshold = claims_list[min(idx_99, len(claims_list) - 1)]

        if threshold <= 0:
            continue

        for p in group:
            if p["opioid_claims"] >= threshold and p["opioid_claims"] > 0:
                p["is_high_prescriber"] = True
                flagged_count += 1

    print(f"  Flagged {flagged_count} high prescribers out of "
          f"{len(providers)} total")
    return providers


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    """Run the full CMS opioid prescribing ingestion pipeline."""
    print("=" * 60)
    print("CMS Opioid Prescribing Fetcher — Tier 2 Ingestion")
    print("=" * 60)
    start_time = time.time()

    # Step 1: Build opioid ingredient list from Tier 1 registry
    print("\nStep 1: Loading opioid ingredient names from registry...")
    opioid_names = _build_opioid_ingredient_names()

    # Step 2: Fetch geographic prescribing data
    raw_geo = fetch_geographic_prescribing()
    geo_records = _parse_geographic_records(raw_geo) if raw_geo else []
    years_covered = sorted(set(
        r["year"] for r in geo_records if r.get("year")
    ))

    # Step 3: Fetch provider-drug data (filtered to opioids)
    raw_provider = fetch_provider_drug_data(opioid_names)
    provider_records = _parse_provider_records(
        raw_provider, opioid_names) if raw_provider else []

    # Step 4: Flag high prescribers
    if provider_records:
        provider_records = flag_high_prescribers(provider_records)

    # Step 5: Build output JSON
    output = {
        "metadata": {
            "source": "CMS Medicare Part D",
            "years_covered": years_covered,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "geographic_records": len(geo_records),
            "provider_records": len(provider_records),
            "high_prescribers": sum(
                1 for p in provider_records if p.get("is_high_prescriber")),
            "opioid_ingredients_matched": len(opioid_names),
        },
        "by_geography": geo_records,
        "by_provider": provider_records,
    }

    # Step 6: Save
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.CMS_PRESCRIBING_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, default=str)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"CMS Fetcher Complete")
    print(f"  Geographic records: {len(geo_records)}")
    print(f"  Provider records:   {len(provider_records)}")
    print(f"  High prescribers:   {output['metadata']['high_prescribers']}")
    print(f"  Years covered:      {years_covered}")
    print(f"  Output:             {config.CMS_PRESCRIBING_OUTPUT}")
    print(f"  Elapsed:            {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
