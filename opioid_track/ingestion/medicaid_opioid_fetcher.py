"""
Medicaid Opioid Supply Fetcher
================================
Fetches "Medicaid Opioid Prescribing Rates - by Geography" from the CMS Data API.
This serves as the official, real-world data replacement for the DEA ARCOS dataset,
which went offline. Instead of manufacturing volumes (pills), it tracks the
actual dispensing volumes (claims) and prescribing rates at the State and County
level across the nation for multiple years.

Uses the CMS Data API v1, matching the robust pagination patterns built for
the Phase 1 CMS fetcher.

Follows Tier 1 conventions: warn-and-continue error handling, print-based
logging, JSON output with metadata block.

Usage:
    python -m opioid_track.ingestion.medicaid_opioid_fetcher
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


def _standardize_fips(fips_val) -> str | None:
    """Standardize a FIPS code to 5-digit zero-padded form.
    For Medicaid data, Geo_Cd contains state FIPS (2) or county FIPS (5).
    """
    if fips_val is None:
        return None
    fips_str = str(fips_val).strip()
    if not fips_str:
        return None
    
    if len(fips_str) <= 2:
        return fips_str.zfill(2)
    return fips_str.zfill(5)


def _safe_float(val) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return None


def fetch_medicaid_data_api() -> list[dict]:
    """Fetch paginated data from CMS data API v1."""
    print("\n--- Fetching Medicaid Opioid Prescribing Data ---")
    all_records = []
    
    base_url = f"https://data.cms.gov/data-api/v1/dataset/{config.CMS_MEDICAID_GEO_UUID}/data"
    
    size = 5000
    offset = 0
    max_records = 500000

    while offset < max_records:
        url = f"{base_url}?size={size}&offset={offset}"
        try:
            resp = retry_get(url, delay_between=0.2)
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"  WARNING: CMS API unreachable: {e}")
                return []
            print(f"  WARNING: Pagination error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break
            
        all_records.extend(batch)
        print(f"    Fetched {len(all_records)} records...")
        
        if len(batch) < size:
            break
            
        offset += size
        time.sleep(0.1)

    print(f"  ✓ Total Medicaid records fetched: {len(all_records)}")
    return all_records


def _process_records(records: list[dict]) -> tuple[list[dict], list[dict], set]:
    """Process raw records into state and county outputs.
    Returns (by_state, by_county, years_covered)
    """
    print("\n--- Processing Data by Geo_Lvl ---")
    
    # We only want 'All' plan types to avoid double counting FFS vs MCO
    valid_records = [r for r in records if r.get("Plan_Type", "All") == "All"]
    
    state_agg = defaultdict(lambda: {
        "state_fips": "", "state_name": "", "total_opioid_claims": 0, "by_year": {}
    })
    
    county_agg = defaultdict(lambda: {
        "county_fips": "", "county_name": "", "total_opioid_claims": 0, "by_year": {}
    })
    
    years_covered = set()

    for rec in valid_records:
        geo_lvl = rec.get("Geo_Lvl", "")
        # National is skipped since we aggregate from state/county
        if geo_lvl not in ("State", "County"):
            continue

        year = _safe_int(rec.get("Year"))
        if not year:
            continue
            
        years_covered.add(year)
        
        geo_cd = rec.get("Geo_Cd", "").strip()
        geo_desc = rec.get("Geo_Desc", "").strip()
        claims = _safe_int(rec.get("Tot_Opioid_Clms")) or 0
        rate = _safe_float(rec.get("Opioid_Prscrbng_Rate"))
        
        metrics = {
            "year": year,
            "opioid_claims": claims,
            "prescribing_rate": rate
        }

        if geo_lvl == "State":
            fips = _standardize_fips(geo_cd)
            if not fips: continue
            
            state_agg[fips]["state_fips"] = fips
            state_agg[fips]["state_name"] = geo_desc
            state_agg[fips]["total_opioid_claims"] += claims
            state_agg[fips]["by_year"][year] = metrics
            
        elif geo_lvl == "County":
            fips = _standardize_fips(geo_cd)
            if not fips: continue
            
            county_agg[fips]["county_fips"] = fips
            county_agg[fips]["county_name"] = geo_desc
            county_agg[fips]["total_opioid_claims"] += claims
            county_agg[fips]["by_year"][year] = metrics

    # Format into lists
    by_state = []
    for fips, data in sorted(state_agg.items()):
        by_year_list = [val for _, val in sorted(data["by_year"].items())]
        by_state.append({
            "state_fips": data["state_fips"],
            "state_name": data["state_name"],
            "total_opioid_claims": data["total_opioid_claims"],
            "by_year": by_year_list
        })
        
    by_county = []
    for fips, data in sorted(county_agg.items()):
        by_year_list = [val for _, val in sorted(data["by_year"].items())]
        by_county.append({
            "county_fips": data["county_fips"],
            "county_name": data["county_name"],
            "total_opioid_claims": data["total_opioid_claims"],
            "by_year": by_year_list
        })

    print(f"  Processed {len(by_state)} states, {len(by_county)} counties")
    return by_state, by_county, years_covered


def main():
    print("=" * 60)
    print("Medicaid Supply Chain Fetcher — Tier 2 Ingestion")
    print("=" * 60)
    start_time = time.time()

    # Step 1: Fetch data
    raw_records = fetch_medicaid_data_api()
    if not raw_records:
        print("  FATAL: Could not fetch Medicaid data.")
        return None

    # Step 2: Process into output format
    by_state, by_county, years_covered = _process_records(raw_records)

    years_list = sorted(list(years_covered))

    output = {
        "metadata": {
            "source": "CMS Medicaid Opioid Prescribing Rates (data.cms.gov)",
            "metric": "Opioid Claims (proxy for ARCOS supply volume)",
            "years_covered": years_list,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_raw_records": len(raw_records),
            "states_fetched": len(by_state),
            "counties_fetched": len(by_county)
        },
        "by_state": by_state,
        "by_county": by_county,
    }

    # Step 3: Save output
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.MEDICAID_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, default=str)

    elapsed = time.time() - start_time
    total_claims = sum(s.get("total_opioid_claims", 0) for s in by_state)
    
    print(f"\n{'=' * 60}")
    print(f"Medicaid Opioid Fetcher Complete")
    print(f"  State records:      {len(by_state)}")
    print(f"  County records:     {len(by_county)}")
    print(f"  Total claims:       {total_claims:,}")
    print(f"  Years covered:      {years_list}")
    print(f"  Output:             {config.MEDICAID_OUTPUT}")
    print(f"  Elapsed:            {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
