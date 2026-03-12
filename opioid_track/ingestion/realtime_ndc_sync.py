"""
Real-time NDC Sync
==================
Fetches opioid NDCs released from 2019 onwards from the OpenFDA API to ensure
clinical recency and capture product-level metadata (manufacturer, brand name).

Usage:
    python -m opioid_track.ingestion.realtime_ndc_sync
"""

import json
import os

from opioid_track import config
from opioid_track.ingestion import retry_get
from opioid_track.ingestion.ndc_opioid_classifier import normalize_ndc


def fetch_recent_ndcs():
    """Fetch NDCs approved from 2019 onward from OpenFDA."""
    print("Fetching 2019-2025 NDCs from OpenFDA...")
    all_results = []
    limit = 100
    skip = 0
    max_offset = 25000

    base_url = f"{config.OPENFDA_BASE}/ndc.json"
    
    while skip < max_offset:
        query_str = f"search={config.OPENFDA_NDC_QUERY_OPIOID}+AND+marketing_start_date:[{config.OPENFDA_RECENT_YEAR_START}+TO+{config.OPENFDA_RECENT_YEAR_END}]&limit={limit}&skip={skip}"
        url = f"{base_url}?{query_str}"
        try:
            resp = retry_get(url, delay_between=config.OPENFDA_DELAY_SECONDS)
            if resp.status_code == 404:
                # No more results
                break
            data = resp.json()
        except Exception as e:
            print(f"  WARNING: OpenFDA fetch failed at skip {skip}: {e}")
            break
            
        results = data.get("results", [])
        if not results:
            break
            
        all_results.extend(results)
        skip += limit
        
        meta = data.get("meta", {}).get("results", {})
        total_available = meta.get("total", 0)
        if skip >= total_available:
            break

    print(f"  Fetched {len(all_results)} recent NDC entries from OpenFDA")
    return all_results


def process_and_save_ndcs(raw_results):
    """Normalize and structure the raw OpenFDA results, extracting metadata."""
    processed = {}
    
    for item in raw_results:
        product_ndc = item.get("product_ndc", "")
        if not product_ndc:
            continue
            
        ndc_11, ndc_formatted = normalize_ndc(product_ndc)
        marketing_start_date = item.get("marketing_start_date", "")
        generic_name = item.get("generic_name", "")
        brand_name = item.get("brand_name", "")
        labeler_name = item.get("labeler_name", "")
        
        openfda = item.get("openfda", {})
        rxcuis = openfda.get("rxcui", [])
        
        # In FDA OpenFDA, packaging contains the package-level NDCs
        packages = item.get("packaging", [])
        pkg_ndcs = []
        for p in packages:
            p_ndc = p.get("package_ndc")
            if p_ndc:
                p_11, p_fmt = normalize_ndc(p_ndc)
                pkg_ndcs.append(p_11)
        
        entry = {
            "ndc_formatted": ndc_formatted,
            "package_ndcs": pkg_ndcs,
            "generic_name": generic_name,
            "brand_name": brand_name,
            "manufacturer": labeler_name,
            "marketing_start_date": marketing_start_date,
            "rxcui": rxcuis[0] if rxcuis else "",
            "source": "openfda-realtime",
            "is_opioid": True,
            "is_recovery_drug": False 
        }
        
        processed[ndc_11] = entry
        for p_11 in pkg_ndcs:
            processed[p_11] = entry
        
    print(f"Total structured unique NDCs (product + packages): {len(processed)}")
    
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.REALTIME_NDC_OUTPUT, "w") as f:
        json.dump(processed, f, indent=2)
        
    print(f"Saved to {config.REALTIME_NDC_OUTPUT}")
    return processed


def main():
    print("=" * 60)
    print("Real-time NDC Sync — Fetching 2019-2025 Opioid NDCs")
    print("=" * 60)
    
    raw_results = fetch_recent_ndcs()
    process_and_save_ndcs(raw_results)
    print("Done.")


if __name__ == "__main__":
    main()
