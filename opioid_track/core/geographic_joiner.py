"""
Geographic Data Joiner
======================
Merges the three tier-2 datasets:
1. CMS Prescribing Data (by_county)
2. CDC Mortality Data (by_state)
3. Medicaid Supply Chain Data (by_county)

Fetches Population from the 2020 ACS via Census API to compute per-capita metrics.
Constructs a unified county-level risk profile.

Usage:
    python -m opioid_track.core.geographic_joiner
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
import requests

from opioid_track import config

STATE_ABBREV = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
    "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH",
    "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
    "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA",
    "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN",
    "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC"
}
ABBREV_STATE = {v: k for k, v in STATE_ABBREV.items()}

def load_json(filepath: str) -> dict:
    with open(filepath, "r") as f:
        return json.load(f)

def fetch_census_population() -> dict:
    """Fetch 2020 ACS 5-year population for all counties and states."""
    print("\n--- Fetching Census Population Data ---")
    
    pops = {"county": {}, "state": defaultdict(int)}
    
    url = f"{config.CENSUS_API_BASE}/2020/acs/acs5"
    params = {
        "get": "NAME,B01003_001E",
        "for": "county:*",
        "in": "state:*",
        "key": config.CENSUS_API_KEY
    }
    
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        # Format: [["NAME", "B01003_001E", "state", "county"], ["Autauga County, Alabama", "55639", "01", "001"], ...]
        headers = data[0]
        rows = data[1:]
        
        for row in rows:
            pop = int(row[1]) if row[1] else 0
            state_fips = row[2]
            county_fips = row[3]
            fips = f"{state_fips}{county_fips}"
            
            pops["county"][fips] = pop
            
            # extract state name from the full name string (e.g. "Autauga County, Alabama")
            parts = row[0].split(", ")
            if len(parts) == 2:
                state_name = parts[1]
                pops["state"][state_name] += pop
                
        print(f"  ✓ Fetched population for {len(pops['county'])} counties")
    except Exception as e:
        print(f"  WARNING: Census API failed: {e}")
        print("  Proceeding without population data (per-capita will be null)")
        
    return pops

def min_max_scale(val, min_v, max_v):
    if val is None or max_v == min_v: return 0.0
    s = (val - min_v) / (max_v - min_v)
    return max(0.0, min(1.0, s))

def build_master_table():
    print("\n--- Loading Tier 2 Datasets ---")
    
    cms = load_json(config.CMS_PRESCRIBING_OUTPUT)
    cdc = load_json(config.CDC_MORTALITY_OUTPUT)
    supply = load_json(config.MEDICAID_OUTPUT)
    
    pops = fetch_census_population()
    
    print("  Organizing master indices...")
    # CMS Index: FIPS -> CMS data
    cms_idx = {}
    for r in cms.get("by_geography", []):
        if r.get("geo_level") == "county" and r.get("fips_code"):
            fips = r["fips_code"].zfill(5)
            # Latest year (2023)
            if fips not in cms_idx or r["year"] == 2023:
                cms_idx[fips] = r
                
    # Supply Chain (Medicaid claims) Index: FIPS -> Supply data
    supply_idx = {}
    for r in supply.get("by_county", []):
        fips = r["county_fips"].zfill(5)
        supply_idx[fips] = r
        
    # CDC State Index: State Abbrev -> CDC state latest year
    cdc_state_idx = {}
    for r in cdc.get("by_state", []):
        state_abbr = r["state"]
        # Take latest year (often 2023/2024/2025 based on available data)
        # We ensure we just capture the max year entry for the state
        if state_abbr not in cdc_state_idx or r["year"] >= cdc_state_idx[state_abbr]["year"]:
            cdc_state_idx[state_abbr] = r
            
    print("\n--- Constructing Unified Geographic Profiles ---")
    master = {}
    
    # Base it on the superset of FIPS from CMS and Supply
    all_fips = set(cms_idx.keys()) | set(supply_idx.keys()) | set(pops["county"].keys())
    
    raw_metrics = []
    
    for fips in all_fips:
        cms_r = cms_idx.get(fips, {})
        sup_r = supply_idx.get(fips, {})
        
        # State abbreviation resolution
        state_name = None
        state_abbr = None
        county_name = None
        
        # Try finding State/County from CMS
        if cms_r:
            state_name = cms_r.get("state")
            county_name = cms_r.get("county")
            
        # If CMS gave empty strings and format was "State:County", parse it
        if not state_name and county_name and ":" in county_name:
            parts = county_name.split(":")
            state_name, county_name = parts[0], parts[1]

        # Try Medicaid proxy if CMS was missing
        if not state_name and sup_r:
            st_co = sup_r.get("county_name", "")
            if ":" in st_co:
                parts = st_co.split(":")
                state_name, county_name = parts[0], parts[1]
                
        if not state_name or state_name == "National":
            continue
            
        state_abbr = STATE_ABBREV.get(state_name)
        if not state_abbr: continue
        
        c_pop = pops["county"].get(fips)
        s_pop = pops["state"].get(state_name)
        
        cdc_r = cdc_state_idx.get(state_abbr, {})
        state_deaths = cdc_r.get("by_opioid_type", {}).get("all_opioids")
        state_death_rate = None
        if state_deaths and s_pop and s_pop > 0:
            state_death_rate = (state_deaths / s_pop) * 100000.0  # deaths per 100k
            
        cms_rate = cms_r.get("opioid_prescribing_rate")
        
        sup_claims = sup_r.get("total_opioid_claims", 0)
        claims_per_capita = None
        # Medicaid covers 2016-2023 usually, 8 years
        if sup_claims and c_pop and c_pop > 0:
            claims_per_capita = (sup_claims / 8.0) / c_pop

        entry = {
            "fips_code": fips,
            "state_abbr": state_abbr,
            "state": state_name,
            "county": county_name,
            "population": c_pop,
            "data_sources": sum(1 for x in [cms_r, cdc_r, sup_r] if x),
            "cms_data": {
                "prescribing_rate": cms_rate,
                "latest_year": cms_r.get("year")
            } if cms_r else None,
            "cdc_state_data": {
                "opioid_deaths_total": state_deaths,
                "death_rate_per_100k": round(state_death_rate, 2) if state_death_rate else None,
                "latest_year": cdc_r.get("year")
            } if cdc_r else None,
            "medicaid_supply": {
                "total_claims": sup_claims,
                "claims_per_capita_annual_avg": round(claims_per_capita, 2) if claims_per_capita else None
            } if sup_r else None
        }
        
        raw_metrics.append((
            fips,
            cms_rate or 0,
            state_death_rate or 0,
            claims_per_capita or 0,
            entry
        ))
        
    print(f"  Built {len(raw_metrics)} county records. Computing risk tiers...")
    
    # 1. Gather mins/maxes for scaling
    val_cms = [m[1] for m in raw_metrics if m[1] > 0]
    val_cdc = [m[2] for m in raw_metrics if m[2] > 0]
    val_sup = [m[3] for m in raw_metrics if m[3] > 0]
    
    min_cms, max_cms = min(val_cms) if val_cms else 0, max(val_cms) if val_cms else 1
    min_cdc, max_cdc = min(val_cdc) if val_cdc else 0, max(val_cdc) if val_cdc else 1
    min_sup, max_sup = min(val_sup) if val_sup else 0, max(val_sup) if val_sup else 1

    # 2. Assign risk scores
    two_plus_sources = 0
    final_counties = []
    
    for fips, m_cms, m_cdc, m_sup, entry in raw_metrics:
        if entry["data_sources"] >= 2:
            two_plus_sources += 1
            
            s1 = min_max_scale(m_cms, min_cms, max_cms)
            s2 = min_max_scale(m_cdc, min_cdc, max_cdc)
            s3 = min_max_scale(m_sup, min_sup, max_sup)
            
            # Weighted average
            risk_score = (s1 + s2 + s3) / 3.0
            
            if risk_score < 0.25: tier = "Low"
            elif risk_score < 0.50: tier = "Medium"
            elif risk_score < 0.75: tier = "High"
            else: tier = "Critical"
            
            entry["derived_metrics"] = {
                "risk_score": round(risk_score, 4),
                "risk_tier": tier
            }
        else:
            entry["derived_metrics"] = None
            
        final_counties.append(entry)

    print()
    tier_counts = defaultdict(int)
    for c in final_counties:
        if c["derived_metrics"]:
            tier_counts[c["derived_metrics"]["risk_tier"]] += 1
    
    print("Risk Tier Distribution:")
    for t in ["Critical", "High", "Medium", "Low"]:
        print(f"  {t}: {tier_counts[t]}")

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_counties": len(final_counties),
            "counties_with_2plus_sources": two_plus_sources,
            "data_sources_joined": ["CMS Prescribing", "CDC VSRR Mortality", "CMS Medicaid Supply Proxy", "Census ACS"]
        },
        "counties": sorted(final_counties, key=lambda x: x["fips_code"])
    }
    
    with open(config.GEO_PROFILES_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, default=str)
        
    print(f"\n  ✓ Saved final geographic joiner to {config.GEO_PROFILES_OUTPUT}")
    

if __name__ == "__main__":
    build_master_table()
