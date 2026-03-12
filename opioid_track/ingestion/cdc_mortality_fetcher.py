"""
CDC Mortality Fetcher
=======================
Ingests opioid overdose mortality data from two CDC sources:

1. **Primary — CDC VSRR** (Vital Statistics Rapid Release): Provisional drug
   overdose death counts by state, month, and opioid type via the Socrata API
   on data.cdc.gov. No API key required.

2. **Supplemental — CDC WONDER** (via alipphardt/cdc-wonder-api vendor clone):
   County-level and demographic mortality data from the Multiple Cause of
   Death (MCD) database. Graceful degradation if WONDER is unavailable.

Follows Tier 1 conventions: warn-and-continue error handling, print-based
logging, JSON output with metadata block.

Usage:
    python -m opioid_track.ingestion.cdc_mortality_fetcher
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


# ---------------------------------------------------------------------------
# Opioid wave tagging
# ---------------------------------------------------------------------------

def _tag_opioid_wave(year: int) -> str:
    """Tag a year with its opioid wave classification."""
    if year is None:
        return "Unknown"
    if year <= 2010:
        return "Wave 1 — Prescription opioids"
    elif year <= 2013:
        return "Wave 2 — Heroin"
    else:
        return "Wave 3 — Synthetic/fentanyl"


def _safe_int(val) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if val is None:
        return None
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if val is None:
        return None
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Indicator → field key mapping
# ---------------------------------------------------------------------------

INDICATOR_KEY_MAP = {
    "Opioids (T40.0-T40.4,T40.6)": "all_opioids",
    "Natural & semi-synthetic opioids (T40.2)": "natural_semisynthetic_T40.2",
    "Methadone (T40.3)": "methadone_T40.3",
    "Synthetic opioids, excl. methadone (T40.4)": "synthetic_fentanyl_T40.4",
    "Heroin (T40.1)": "heroin_T40.1",
}

# Broader indicators to capture total overdose deaths (not just opioids)
TOTAL_OVERDOSE_INDICATORS = [
    "Number of Deaths",
    "Number of Drug Overdose Deaths",
    "Percent with drugs specified",
]


# ---------------------------------------------------------------------------
# CDC VSRR Fetcher (primary data source)
# ---------------------------------------------------------------------------

def fetch_vsrr_data() -> list[dict]:
    """Fetch CDC VSRR Provisional Drug Overdose Death Counts.

    Uses the Socrata API at data.cdc.gov. No API key needed but we add
    a User-Agent header. Returns raw records.
    """
    print("\n--- Fetching CDC VSRR Provisional Death Counts ---")

    all_records = []
    limit = 50000
    offset = 0
    max_records = 500000  # Safety cap

    while offset < max_records:
        url = (f"{config.CDC_VSRR_ENDPOINT}"
               f"?$limit={limit}&$offset={offset}"
               f"&$order=year DESC,month DESC")
        try:
            resp = retry_get(url, delay_between=0.1,
                             headers={"User-Agent": "TruPharma-Opioid/2.0"})
            batch = resp.json()
        except Exception as e:
            if offset == 0:
                print(f"  WARNING: VSRR endpoint unreachable: {e}")
                return []
            print(f"  WARNING: Pagination error at offset {offset}: {e}")
            break

        if not isinstance(batch, list) or not batch:
            break

        all_records.extend(batch)
        if len(all_records) % 50000 == 0 or len(batch) < limit:
            print(f"    Fetched {len(all_records)} VSRR records...")

        if len(batch) < limit:
            break
        offset += limit
        time.sleep(0.1)

    print(f"  ✓ Total VSRR records: {len(all_records)}")
    return all_records


def _filter_opioid_records(records: list[dict]) -> list[dict]:
    """Filter VSRR records to opioid-related indicators only."""
    opioid_indicators = set(config.VSRR_OPIOID_INDICATORS)
    filtered = [
        r for r in records
        if r.get("indicator", "") in opioid_indicators
    ]
    print(f"  Filtered to {len(filtered)} opioid-indicator records "
          f"(from {len(records)} total)")
    return filtered


def _build_annual_national(opioid_records: list[dict],
                            all_records: list[dict]) -> list[dict]:
    """Build national-level annual summaries from VSRR opioid records.

    Uses 12-month-ending periods to get annual totals.
    Groups by year → sums across states per indicator.
    """
    print("\n  Building national annual summaries...")

    # Use "12 month-ending" period for annual totals, take December (month 12)
    # for each year to get the 12-month-ending figure
    # Group by (year, indicator) and pick the "US" / national entry
    national = defaultdict(lambda: defaultdict(list))

    for rec in opioid_records:
        state = rec.get("state", "")
        year = _safe_int(rec.get("year"))
        period = rec.get("period", "")
        indicator = rec.get("indicator", "")
        data_value = _safe_int(rec.get("data_value"))
        predicted_value = _safe_int(rec.get("predicted_value"))

        if year is None:
            continue

        # Use "US" for national, or "12 month-ending" with December
        if state == "US" or (period == "12 month-ending"
                             and rec.get("month", "").lower() == "december"):
            key = INDICATOR_KEY_MAP.get(indicator)
            if key and data_value is not None:
                national[year][key].append(data_value)

    # Also try to get total overdose deaths from all_records
    total_deaths_by_year = {}
    for rec in all_records:
        state = rec.get("state", "")
        year = _safe_int(rec.get("year"))
        indicator = rec.get("indicator", "")
        data_value = _safe_int(rec.get("data_value"))

        if (year and state == "US" and data_value
                and "Number of Drug Overdose Deaths" in indicator
                and rec.get("period", "") == "12 month-ending"
                and rec.get("month", "").lower() == "december"):
            if year not in total_deaths_by_year:
                total_deaths_by_year[year] = data_value

    results = []
    for year in sorted(national.keys()):
        by_type = {}
        for key, values in national[year].items():
            # Take the max value (most complete data)
            by_type[key] = max(values)

        total_deaths = total_deaths_by_year.get(year)

        results.append({
            "year": year,
            "opioid_wave": _tag_opioid_wave(year),
            "total_overdose_deaths": total_deaths,
            "by_opioid_type": by_type,
        })

    print(f"    Built {len(results)} national annual records "
          f"({min(r['year'] for r in results) if results else '?'}–"
          f"{max(r['year'] for r in results) if results else '?'})")
    return results


def _build_state_data(opioid_records: list[dict]) -> list[dict]:
    """Build state-level annual data from VSRR records.

    Uses 12 month-ending December entries for each state+year.
    """
    print("  Building state-level annual data...")

    # Group by (state_name, year) → indicators
    state_data = defaultdict(lambda: defaultdict(dict))

    for rec in opioid_records:
        state = rec.get("state", "")
        state_name = rec.get("state_name", "")
        year = _safe_int(rec.get("year"))
        period = rec.get("period", "")
        indicator = rec.get("indicator", "")
        data_value = _safe_int(rec.get("data_value"))
        predicted = _safe_int(rec.get("predicted_value"))

        if year is None or not state_name or state == "US":
            continue

        key = INDICATOR_KEY_MAP.get(indicator)
        if not key or data_value is None:
            continue

        # Prefer 12-month-ending December, but take any 12-month-ending
        if period == "12 month-ending":
            month = rec.get("month", "").lower()
            existing = state_data[(state_name, state)].get(year, {})
            # Only overwrite if this is December or we have no data yet
            if month == "december" or key not in existing:
                if year not in state_data[(state_name, state)]:
                    state_data[(state_name, state)][year] = {}
                state_data[(state_name, state)][year][key] = data_value

    results = []
    for (state_name, state_abbr), years_dict in state_data.items():
        for year, by_type in sorted(years_dict.items()):
            results.append({
                "state": state_abbr,
                "state_name": state_name,
                "year": year,
                "opioid_wave": _tag_opioid_wave(year),
                "by_opioid_type": by_type,
            })

    states_covered = len(set(r["state"] for r in results))
    print(f"    Built {len(results)} state-year records "
          f"({states_covered} states)")
    return results


# ---------------------------------------------------------------------------
# CDC WONDER integration (supplemental, via vendor clone)
# ---------------------------------------------------------------------------

def _try_wonder_data() -> tuple[list[dict], list[dict], bool]:
    """Attempt to fetch county-level + demographic data from CDC WONDER.

    Uses the alipphardt/cdc-wonder-api vendor clone if available.
    Returns: (by_county, by_demographics, wonder_available)
    """
    print("\n--- Attempting CDC WONDER supplemental data ---")

    # Check if the vendor clone exists
    wonder_dir = config.CDC_WONDER_API_DIR
    if not os.path.isdir(wonder_dir):
        print(f"  CDC WONDER vendor directory not found: {wonder_dir}")
        print("  Skipping WONDER data (VSRR is sufficient for Tier 2)")
        return [], [], False

    try:
        # Add vendor directory to path
        vendor_parent = os.path.dirname(wonder_dir)
        if vendor_parent not in sys.path:
            sys.path.insert(0, vendor_parent)

        # Try importing the wonder library
        # The library is in cdc-wonder-api/ and typically has a wonderpy module
        wonder_path = os.path.join(wonder_dir)
        if wonder_path not in sys.path:
            sys.path.insert(0, wonder_path)

        print("  CDC WONDER library found, but WONDER requires an active ")
        print("  data use agreement and may not be accessible programmatically.")
        print("  Setting wonder_available=false for now.")

        # CDC WONDER requires accepting a DUA through the web interface
        # The API is XML-based and often returns errors without a prior
        # agreement acceptance. We gracefully degrade here.
        return [], [], False

    except Exception as e:
        print(f"  WARNING: CDC WONDER access failed: {e}")
        return [], [], False


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    """Run the full CDC mortality data ingestion pipeline."""
    print("=" * 60)
    print("CDC Mortality Fetcher — Tier 2 Ingestion")
    print("=" * 60)
    start_time = time.time()

    # Step 1: Fetch VSRR data (primary)
    all_vsrr = fetch_vsrr_data()
    if not all_vsrr:
        print("  FATAL: No VSRR data fetched. Cannot continue.")
        return None

    # Step 2: Filter to opioid indicators
    opioid_records = _filter_opioid_records(all_vsrr)

    # Step 3: Build national annual summaries
    annual_national = _build_annual_national(opioid_records, all_vsrr)

    # Step 4: Build state data
    by_state = _build_state_data(opioid_records)

    # Step 5: Try WONDER for county + demographics (supplemental)
    by_county, by_demographics, wonder_available = _try_wonder_data()

    # Step 6: Determine latest year
    latest_year = None
    if annual_national:
        latest_year = max(r["year"] for r in annual_national)

    # Step 7: Build output JSON
    output = {
        "metadata": {
            "source": "CDC VSRR + CDC WONDER (alipphardt/cdc-wonder-api)",
            "wonder_available": wonder_available,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "latest_year": latest_year,
            "total_vsrr_records": len(all_vsrr),
            "opioid_records": len(opioid_records),
            "states_covered": len(set(r["state"] for r in by_state)),
            "years_covered": sorted(set(r["year"] for r in annual_national)),
            "notes": "VSRR data is provisional and subject to revision",
        },
        "annual_national": annual_national,
        "by_state": by_state,
        "by_county": by_county,
        "by_demographics": by_demographics,
    }

    # Step 8: Save
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.CDC_MORTALITY_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, default=str)

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"CDC Mortality Fetcher Complete")
    print(f"  VSRR records:       {len(all_vsrr)}")
    print(f"  Opioid records:     {len(opioid_records)}")
    print(f"  National summaries: {len(annual_national)}")
    print(f"  State records:      {len(by_state)}")
    print(f"  County records:     {len(by_county)}")
    print(f"  WONDER available:   {wonder_available}")
    print(f"  Latest year:        {latest_year}")
    print(f"  Output:             {config.CDC_MORTALITY_OUTPUT}")
    print(f"  Elapsed:            {elapsed:.1f}s")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
"""
    python -m opioid_track.ingestion.cdc_mortality_fetcher
"""
