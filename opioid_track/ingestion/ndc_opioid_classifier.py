"""
NDC Opioid Classifier
======================
Downloads pre-classified NDC→opioid lookup from ripl-org/historical-ndc
(JAMIA 2020, MIT license) and supplements with current OpenFDA NDC data.

Usage:
    python -m opioid_track.ingestion.ndc_opioid_classifier
"""

import csv
import json
import os
import re

from opioid_track import config
from opioid_track.ingestion import retry_get


def normalize_ndc(ndc_str):
    """Normalize an NDC code to 11-digit zero-padded format.

    Handles formats: 4-4-2, 5-3-2, 5-4-1, 5-4-2, plain digits.
    Returns (ndc_11digit, ndc_formatted_5_4_2).
    """
    ndc_str = ndc_str.strip()

    # Remove any non-digit, non-hyphen characters
    ndc_clean = re.sub(r'[^0-9\-]', '', ndc_str)

    if '-' in ndc_clean:
        parts = ndc_clean.split('-')
        if len(parts) == 3:
            seg1 = parts[0].zfill(5)
            seg2 = parts[1].zfill(4)
            seg3 = parts[2].zfill(2)
        elif len(parts) == 2:
            # Some NDCs come as 2 segments
            combined = ''.join(parts).zfill(11)
            seg1, seg2, seg3 = combined[:5], combined[5:9], combined[9:11]
        else:
            combined = ''.join(parts).zfill(11)
            seg1, seg2, seg3 = combined[:5], combined[5:9], combined[9:11]
    else:
        digits = ndc_clean.zfill(11)
        seg1, seg2, seg3 = digits[:5], digits[5:9], digits[9:11]

    ndc_11 = f"{seg1}{seg2}{seg3}"
    ndc_formatted = f"{seg1}-{seg2}-{seg3}"
    return ndc_11, ndc_formatted


def download_ripl_csv():
    """Download ndc-opioids.csv from ripl-org/historical-ndc if not cached."""
    os.makedirs(f"{config.OPIOID_DATA_DIR}/raw", exist_ok=True)

    if os.path.exists(config.RIPL_NDC_CSV_LOCAL):
        print(f"Using cached ndc-opioids.csv from {config.RIPL_NDC_CSV_LOCAL}")
        return config.RIPL_NDC_CSV_LOCAL

    print("Downloading ndc-opioids.csv from ripl-org/historical-ndc...")
    try:
        resp = retry_get(config.RIPL_NDC_CSV_URL, timeout=60)
        with open(config.RIPL_NDC_CSV_LOCAL, "wb") as f:
            f.write(resp.content)
        print(f"Downloaded ndc-opioids.csv ({len(resp.content):,} bytes)")
        return config.RIPL_NDC_CSV_LOCAL
    except Exception as e:
        raise FileNotFoundError(
            f"Cannot download ndc-opioids.csv: {e}\n"
            f"Manually download from: {config.RIPL_NDC_CSV_URL}\n"
            f"Save to: {config.RIPL_NDC_CSV_LOCAL}"
        ) from e


def parse_ripl_csv(csv_path):
    """Parse the ripl-org CSV into a lookup dict keyed by normalized NDC.

    Inspects the schema at runtime before parsing.
    """
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        print(f"CSV columns: {columns}")

        # Read first 3 rows to inspect
        rows = []
        for i, row in enumerate(reader):
            rows.append(row)
            if i < 3:
                print(f"  Sample row {i}: {dict(row)}")

    # Detect column names (case-insensitive matching)
    col_map = {}
    for col in columns:
        cl = col.lower().strip()
        if 'ndc' in cl and 'opioid' not in cl and 'recovery' not in cl:
            col_map['ndc'] = col
        elif 'opioid' in cl:
            col_map['opioid'] = col
        elif 'recovery' in cl:
            col_map['recovery'] = col
        elif 'drug' in cl or 'name' in cl or 'generic' in cl:
            col_map['drug_name'] = col
        elif 'rxcui' in cl:
            col_map['rxcui'] = col

    print(f"Column mapping: {col_map}")

    ndc_col = col_map.get('ndc')
    opioid_col = col_map.get('opioid')
    recovery_col = col_map.get('recovery')
    name_col = col_map.get('drug_name')
    rxcui_col = col_map.get('rxcui')

    if not ndc_col:
        raise ValueError(f"Cannot find NDC column in: {columns}")

    lookup = {}
    for row in rows:
        raw_ndc = row.get(ndc_col, "").strip()
        if not raw_ndc:
            continue

        ndc_11, ndc_formatted = normalize_ndc(raw_ndc)

        is_opioid = False
        is_recovery = False
        if opioid_col and row.get(opioid_col, "").strip():
            val = row[opioid_col].strip().lower()
            is_opioid = val in ("1", "true", "yes", "t")
        if recovery_col and row.get(recovery_col, "").strip():
            val = row[recovery_col].strip().lower()
            is_recovery = val in ("1", "true", "yes", "t")

        # If no opioid/recovery columns, assume all entries are opioid-related
        if not opioid_col and not recovery_col:
            is_opioid = True

        drug_name = row.get(name_col, "") if name_col else ""
        rxcui = row.get(rxcui_col, "") if rxcui_col else ""

        lookup[ndc_11] = {
            "ndc_formatted": ndc_formatted,
            "rxcui": str(rxcui).strip(),
            "drug_name": drug_name.strip(),
            "is_opioid": is_opioid,
            "is_recovery_drug": is_recovery,
            "source": "ripl-org-historical",
        }

    return lookup


def fetch_openfda_ndc_supplement():
    """Fetch current opioid NDC data from OpenFDA to fill post-2018 gaps."""
    print("\nFetching OpenFDA NDC supplement...")
    openfda_lookup = {}
    offset = 0
    limit = 100
    max_offset = 25000
    total_fetched = 0

    while offset < max_offset:
        url = (f"{config.OPENFDA_BASE}/ndc.json"
               f'?search=pharm_class:"opioid"&limit={limit}&skip={offset}')
        try:
            resp = retry_get(url, delay_between=config.OPENFDA_DELAY_SECONDS)
            data = resp.json()
        except Exception as e:
            print(f"  WARNING: OpenFDA NDC fetch failed at offset {offset}: {e}")
            break

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            product_ndc = item.get("product_ndc", "")
            if not product_ndc:
                continue

            ndc_11, ndc_formatted = normalize_ndc(product_ndc)

            openfda = item.get("openfda", {})
            rxcuis = openfda.get("rxcui", [])
            epc_list = openfda.get("pharm_class_epc", [])

            is_opioid = any("Opioid Agonist" in e or "Opioid Partial Agonist" in e
                            for e in epc_list)
            is_recovery = any("Opioid Antagonist" in e for e in epc_list)

            openfda_lookup[ndc_11] = {
                "ndc_formatted": ndc_formatted,
                "rxcui": rxcuis[0] if rxcuis else "",
                "drug_name": (item.get("generic_name", "") or
                              item.get("brand_name", "")),
                "is_opioid": is_opioid,
                "is_recovery_drug": is_recovery,
                "source": "openfda-current",
            }

        total_fetched += len(results)
        offset += limit

        meta = data.get("meta", {}).get("results", {})
        total_available = meta.get("total", 0)
        if offset >= total_available:
            break

    print(f"  Fetched {total_fetched} NDC entries from OpenFDA")
    return openfda_lookup


def main():
    """Run the full NDC classification pipeline."""
    print("=" * 60)
    print("NDC Opioid Classifier")
    print("=" * 60)

    # Step 1: Download and parse ripl-org CSV
    csv_path = download_ripl_csv()
    ripl_lookup = parse_ripl_csv(csv_path)
    print(f"\nRipl-org historical: {len(ripl_lookup)} NDC entries")

    # Step 2: Fetch OpenFDA supplement
    openfda_lookup = fetch_openfda_ndc_supplement()

    # Step 3: Merge (ripl-org takes priority)
    merged = dict(ripl_lookup)  # Start with ripl-org data
    new_from_openfda = 0
    for ndc, entry in openfda_lookup.items():
        if ndc not in merged:
            merged[ndc] = entry
            new_from_openfda += 1

    # Step 4: Save
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.NDC_LOOKUP_OUTPUT, "w") as f:
        json.dump(merged, f, indent=2)

    # Step 5: Summary stats
    total = len(merged)
    opioid_count = sum(1 for e in merged.values() if e["is_opioid"])
    recovery_count = sum(1 for e in merged.values() if e["is_recovery_drug"])
    ripl_count = sum(1 for e in merged.values()
                     if e["source"] == "ripl-org-historical")
    openfda_count = sum(1 for e in merged.values()
                        if e["source"] == "openfda-current")

    print(f"\n{'=' * 40}")
    print(f"NDC Classification Summary")
    print(f"{'=' * 40}")
    print(f"Total NDCs classified: {total:,}")
    print(f"  Opioid:            {opioid_count:,}")
    print(f"  Recovery:          {recovery_count:,}")
    print(f"  From ripl-org:     {ripl_count:,}")
    print(f"  From OpenFDA:      {openfda_count:,}")
    print(f"  New from OpenFDA:  {new_from_openfda:,}")
    print(f"\nSaved to {config.NDC_LOOKUP_OUTPUT}")

    return merged


if __name__ == "__main__":
    main()
