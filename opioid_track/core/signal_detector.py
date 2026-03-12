"""
FAERS Pharmacovigilance Signal Detector
=======================================
Calculates Disproportionality Analysis (DPA) signals (PRR, ROR, MGPS)
for opioid drug-reaction pairs using the FDA Adverse Event Reporting System
(FAERS) via the OpenFDA API.

This replaces the local SQLite-based `faerslib` dependency by directly
implementing the peer-reviewed statistical methods (PRR, ROR, EBGM/MGPS)
via real-time REST queries, improving reproducibility and speed without
requiring a 100GB+ local database build.

Usage:
    python -m opioid_track.core.signal_detector
"""

import json
import math
import os
import time
from datetime import datetime, timezone

from opioid_track import config
from opioid_track.ingestion import retry_get


def _get_api_count(search_term: str) -> int:
    """Get the total count of FAERS reports for a given search query."""
    base_url = "https://api.fda.gov/drug/event.json"
    
    # If no search term, asking for total FAERS events
    if not search_term:
        url = base_url
    else:
        url = f"{base_url}?search={search_term}"
        
    try:
        resp = retry_get(url, delay_between=0.1, max_retries=3)
        data = resp.json()
        return data.get("meta", {}).get("results", {}).get("total", 0)
    except Exception as e:
        # If openFDA returns a 404 for a search, it means 0 matches.
        if "404" in str(e):
            return 0
        print(f"      API Error on query '{search_term}': {e}")
        return 0


class FaersClient:
    """Client for performing FAERS pharmacovigilance analysis."""
    
    def __init__(self):
        self.cache = self._load_cache()
        self._total_faers = None
        
    def _load_cache(self) -> dict:
        if os.path.exists(config.SIGNAL_CACHE_FILE):
            try:
                with open(config.SIGNAL_CACHE_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
        
    def _save_cache(self):
        os.makedirs(os.path.dirname(config.SIGNAL_CACHE_FILE), exist_ok=True)
        with open(config.SIGNAL_CACHE_FILE, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get_total_events(self) -> int:
        if self._total_faers is None:
            if "total_faers" in self.cache:
                self._total_faers = self.cache["total_faers"]
            else:
                print("  Fetching baseline FAERS total count...")
                val = _get_api_count("")
                self.cache["total_faers"] = val
                self._save_cache()
                self._total_faers = val
        return self._total_faers

    def _get_count_cached(self, entity_type: str, term: str) -> int:
        """Fetch count for either a 'drug' or a 'reaction'."""
        cache_key = f"{entity_type}_{term.lower()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if entity_type == "drug":
            query = f'patient.drug.medicinalproduct:"{term}"'
        else: # reaction
            # Exact phrase match using MedDRA terms
            query = f'patient.reaction.reactionmeddrapt:"{term}"'
            
        val = _get_api_count(query)
        self.cache[cache_key] = val
        self._save_cache()
        return val

    def _get_intersection_cached(self, drug: str, reaction: str) -> int:
        """Fetch count for reports containing BOTH drug and reaction."""
        cache_key = f"both_{drug.lower()}_{reaction.lower()}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        query = f'(patient.drug.medicinalproduct:"{drug}")+AND+(patient.reaction.reactionmeddrapt:"{reaction}")'
        val = _get_api_count(query)
        self.cache[cache_key] = val
        self._save_cache()
        return val

    def get_contingency_table(self, drug: str, reaction: str) -> dict:
        """Construct the 2x2 contingency table for PRR/ROR calculation.
        
                  Target Reaction    Other Reactions
        Target Drug       A                  B
        Other Drugs       C                  D
        """
        A = self._get_intersection_cached(drug, reaction)
        if A == 0:
            return {"A": 0, "B": 0, "C": 0, "D": 0}
            
        A_plus_B = self._get_count_cached("drug", drug)
        A_plus_C = self._get_count_cached("reaction", reaction)
        total = self.get_total_events()
        
        B = max(0, A_plus_B - A)
        C = max(0, A_plus_C - A)
        D = max(0, total - (A + B + C))
        
        # Apply continuity correction for near-zero cells to avoid division by zero
        # standard pharmacovigilance practice (typically +0.5 to cells).
        if A <= 1 or B == 0 or C == 0 or D == 0:
            corr = 0.5
            return {"A": A + corr, "B": B + corr, "C": C + corr, "D": D + corr, "A_raw": A}

        return {"A": A, "B": B, "C": C, "D": D, "A_raw": A}

    def detect_signals(self, drug_name: str, reactions: list[str] = None, 
                       methods: list[str] = None) -> list[dict]:
        """Run requested signal detection methods for a drug across multiple reactions."""
        reactions = reactions or config.OPIOID_SAFETY_TERMS
        methods = methods or config.SIGNAL_METHODS
        
        results = []
        for react in reactions:
            table = self.get_contingency_table(drug_name, react)
            a = table["A"]
            a_raw = table.get("A_raw", a)
            
            # If no actual reports (raw < 1), skip
            if a_raw < 1:
                continue
                
            b = table["B"]
            c = table["C"]
            d = table["D"]
            
            res = {
                "drug_name": drug_name,
                "reaction": react,
                "report_count": int(a_raw),
                "consensus_signal": False,
                "methods_flagging": 0,
                "source_library": "OpenFDA/Mathematical"
            }
            
            method_count = 0
            flagging_count = 0
            
            # 1. PRR (Proportional Reporting Ratio)
            if "prr" in methods:
                try:
                    prr_val = (a / (a + b)) / (c / (c + d))
                    ln_prr = math.log(prr_val)
                    se_prr = math.sqrt((1/a) + (1/b) + (1/c) + (1/d))
                    chi2 = ((a*d - b*c)**2 * (a+b+c+d)) / float((a+b)*(c+d)*(a+c)*(b+d))
                    
                    # Classic Evans criteria: PRR > 2, Chi2 > 4, N > 3
                    is_signal = bool(prr_val > 2.0 and chi2 >= 4.0 and a_raw >= 3)
                    if is_signal: flagging_count += 1
                    
                    res["prr"] = {
                        "value": round(prr_val, 2),
                        "chi2": round(chi2, 2),
                        "signal": is_signal
                    }
                    method_count += 1
                except ZeroDivisionError:
                    res["prr"] = None

            # 2. ROR (Reporting Odds Ratio)
            if "ror" in methods:
                try:
                    ror_val = (a / c) / (b / d)
                    ln_ror = math.log(ror_val)
                    se_ror = math.sqrt((1/a) + (1/b) + (1/c) + (1/d))
                    # 95% CI
                    ci_lower = math.exp(ln_ror - 1.96*se_ror)
                    ci_upper = math.exp(ln_ror + 1.96*se_ror)
                    
                    # Criteria: lower bound of 95% CI > 1, N > 3
                    is_signal = bool(ci_lower > 1.0 and a_raw >= 3)
                    if is_signal: flagging_count += 1
                    
                    res["ror"] = {
                        "value": round(ror_val, 2),
                        "ci_lower": round(ci_lower, 2),
                        "ci_upper": round(ci_upper, 2),
                        "signal": is_signal
                    }
                    method_count += 1
                except ZeroDivisionError:
                    res["ror"] = None

            # 3. MGPS (Multi-Item Gamma Poisson Shrinker) / EBGM approximate
            if "mgps" in methods:
                try:
                    # Expected reports E based on marginal probabilities
                    E = ((a+b)*(a+c)) / (a+b+c+d)
                    
                    # Empirical Bayes Geometric Mean (approximation: A/E)
                    ebgm = a / E if E > 0 else 0
                    # Standard error approximation for EB05 (lower 5% bound)
                    # For a Poisson, lower bound approximation:
                    eb05 = ebgm * math.exp(-1.645 / math.sqrt(a)) if a > 0 else 0
                    
                    # Criteria: EB05 >= 2
                    is_signal = bool(eb05 >= 2.0)
                    if is_signal: flagging_count += 1
                    
                    res["mgps"] = {
                        "ebgm": round(ebgm, 2),
                        "eb05": round(eb05, 2),
                        "signal": is_signal
                    }
                    method_count += 1
                except ZeroDivisionError:
                    res["mgps"] = None
                    
            res["methods_flagging"] = flagging_count
            if flagging_count >= config.SIGNAL_CONSENSUS_THRESHOLD:
                res["consensus_signal"] = True
                
            results.append(res)
            
        return results


def run_opioid_signal_scan() -> list[dict]:
    """Execute the batch script to track safety signals on all tier-1 drugs."""
    print("=" * 60)
    print("Pharmacovigilance Signal Detector — Tier 2 Ingestion")
    print("=" * 60)
    start_time = time.time()
    
    client = FaersClient()
    total = client.get_total_events()
    print(f"  Total FAERS reports in OpenFDA: {total:,}")
    
    target_drugs = config.MUST_INCLUDE_OPIOIDS
    print(f"  Target opioids (n={len(target_drugs)}): {', '.join(target_drugs)}")
    
    all_results = []
    
    for i, drug in enumerate(target_drugs):
        print(f"  [{i+1}/{len(target_drugs)}] Scanning {drug} against safety terms...", end="")
        try:
            drug_results = client.detect_signals(drug_name=drug)
            all_results.extend(drug_results)
            signals_found = sum(1 for r in drug_results if r["consensus_signal"])
            print(f" ✓ ({len(drug_results)} valid pairs, {signals_found} consensus signals)")
        except Exception as e:
            print(f" ✗ FAILED: {e}")
            
    print("\n--- Summary ---")
    consensus_total = sum(1 for r in all_results if r["consensus_signal"])
    
    output = {
        "metadata": {
            "source": "FDA Adverse Event Reporting System (FAERS) via OpenFDA",
            "methods_used": config.SIGNAL_METHODS,
            "consensus_threshold_methods": config.SIGNAL_CONSENSUS_THRESHOLD,
            "total_faers_baseline": total,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_drugs_scanned": len(target_drugs),
            "safety_terms_scanned": len(config.OPIOID_SAFETY_TERMS),
            "total_consensus_signals": consensus_total,
        },
        "signals": all_results
    }
    
    os.makedirs(config.OPIOID_DATA_DIR, exist_ok=True)
    with open(config.SIGNAL_RESULTS_OUTPUT, "w") as f:
        json.dump(output, f, indent=2, default=str)
        
    elapsed = time.time() - start_time
    print(f"  Total drug-reaction pairs analyzed: {len(all_results)}")
    print(f"  Total consensus signals flagged:    {consensus_total}")
    print(f"  Elapsed:                            {elapsed:.1f}s")
    print(f"  Output:                             {config.SIGNAL_RESULTS_OUTPUT}")
    print("=" * 60)
    
    return all_results


if __name__ == "__main__":
    run_opioid_signal_scan()
