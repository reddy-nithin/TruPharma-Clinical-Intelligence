"""
FAERS Opioid Filter
====================
Creates pre-built FAERS query templates and fetches baseline opioid
adverse event statistics from the OpenFDA FAERS API.

Usage:
    python -m opioid_track.ingestion.faers_opioid_filter
"""

import json
import os
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


def build_query_templates():
    """Define parameterized FAERS query templates."""
    base = config.OPENFDA_BASE
    epc_search = 'patient.drug.openfda.pharm_class_epc:"Opioid+Agonist"'

    return {
        "all_opioid_reactions": {
            "description": "Top adverse reactions for all opioid drugs",
            "url": (f"{base}/event.json?search={epc_search}"
                    "&count=patient.reaction.reactionmeddrapt.exact&limit=100"),
            "parameterized": False,
        },
        "opioid_by_drug": {
            "description": "Adverse events for a specific opioid by RxCUI",
            "url": (f"{base}/event.json"
                    '?search=patient.drug.openfda.rxcui:"{{rxcui}}"'
                    "&count=patient.reaction.reactionmeddrapt.exact&limit=100"),
            "parameterized": True,
            "parameters": ["rxcui"],
        },
        "opioid_deaths": {
            "description": "Opioid-associated death reports",
            "url": (f"{base}/event.json?search={epc_search}"
                    "+AND+seriousnessdeath:1"
                    "&count=patient.reaction.reactionmeddrapt.exact&limit=50"),
            "parameterized": False,
        },
        "opioid_by_sex": {
            "description": "Demographic breakdown by sex",
            "url": (f"{base}/event.json?search={epc_search}"
                    "&count=patient.patientsex"),
            "parameterized": False,
        },
        "opioid_by_age": {
            "description": "Age distribution of reporters",
            "url": (f"{base}/event.json?search={epc_search}"
                    "&count=patient.patientonsetage"),
            "parameterized": False,
        },
        "opioid_by_year": {
            "description": "Reporting trend over time",
            "url": (f"{base}/event.json?search={epc_search}"
                    "&count=receivedate"),
            "parameterized": False,
        },
        "specific_reaction": {
            "description": "Events for a specific opioid + specific reaction",
            "url": (f"{base}/event.json"
                    '?search=patient.drug.openfda.rxcui:"{{rxcui}}"'
                    '+AND+patient.reaction.reactionmeddrapt:"{{reaction}}"'),
            "parameterized": True,
            "parameters": ["rxcui", "reaction"],
        },
    }


def fetch_query(name, url):
    """Execute a single FAERS query and return results."""
    print(f"  Fetching: {name}")
    try:
        resp = retry_get(url, delay_between=config.OPENFDA_DELAY_SECONDS)
        data = resp.json()
        results = data.get("results", [])
        print(f"    Got {len(results)} results")
        return results
    except Exception as e:
        print(f"    WARNING: Failed: {e}")
        return []


def fetch_baseline_snapshot(templates):
    """Execute non-parameterized queries to build a baseline snapshot."""
    print("\nFetching FAERS baseline snapshot...")

    snapshot = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    query_map = {
        "top_reactions": "all_opioid_reactions",
        "death_reactions": "opioid_deaths",
        "sex_distribution": "opioid_by_sex",
        "age_distribution": "opioid_by_age",
        "yearly_trend": "opioid_by_year",
    }

    for snapshot_key, template_key in query_map.items():
        template = templates[template_key]
        results = fetch_query(template_key, template["url"])
        snapshot[snapshot_key] = results

    return snapshot


def main():
    """Run the FAERS opioid filter pipeline."""
    print("=" * 60)
    print("FAERS Opioid Filter — Building query templates and baseline")
    print("=" * 60)

    # Step 1: Build templates
    templates = build_query_templates()
    print(f"Defined {len(templates)} query templates")

    # Step 2: Fetch baseline
    snapshot = fetch_baseline_snapshot(templates)

    # Step 3: Save
    output = {
        "query_templates": templates,
        "baseline_snapshot": snapshot,
    }

    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.FAERS_QUERIES_OUTPUT, "w") as f:
        json.dump(output, f, indent=2)

    # Summary
    print(f"\n{'=' * 40}")
    print(f"FAERS Baseline Summary")
    print(f"{'=' * 40}")
    print(f"Top reactions:    {len(snapshot.get('top_reactions', []))} terms")
    print(f"Death reactions:  {len(snapshot.get('death_reactions', []))} terms")
    print(f"Sex categories:   {len(snapshot.get('sex_distribution', []))} entries")
    print(f"Age buckets:      {len(snapshot.get('age_distribution', []))} entries")
    print(f"Yearly trend:     {len(snapshot.get('yearly_trend', []))} data points")
    print(f"\nSaved to {config.FAERS_QUERIES_OUTPUT}")

    return output


if __name__ == "__main__":
    main()
