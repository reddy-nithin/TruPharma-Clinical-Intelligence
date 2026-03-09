# Sub-Plan 05: Supply Chain Risk Dashboard

## Priority: After Sub-Plan 01 (needs caching)
## Can parallelize with: Sub-Plan 03, 04, 06, 07

---

## Goal
Replace the weak ARIMA recall forecasting from POTENTIAL_UPGRADES.md with a real-time Supply Chain Risk Dashboard. Monitors FDA recalls, drug shortages, and manufacturer concentration to compute a Supply Vulnerability Score for each tracked opioid.

## Pre-Requisites
- Sub-Plan 01 (Performance Caching) must be COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/config.py` — existing API endpoints (OpenFDA is already configured)
2. `opioid_track/core/registry.py` — list of tracked opioid drugs
3. `opioid_track/core/signal_detector.py` — pattern for FDA API calls (reuse approach)
4. `opioid_track/dashboard/opioid_app.py` — navigation structure to add new page

---

## Agent Assignment

### Agent A (Worktree: `supply-chain`) — Create Supply Chain Monitor

**Create file: `opioid_track/core/supply_chain_monitor.py`**

```python
"""
Real-time Supply Chain Risk Monitoring for opioid products.
Tracks FDA recalls, drug shortages, and supply vulnerability.
"""
import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class RecallAlert:
    """Single FDA recall record."""
    recall_number: str
    product_description: str
    reason_for_recall: str
    classification: str          # "Class I", "Class II", "Class III"
    status: str                  # "Ongoing", "Terminated", "Completed"
    recall_initiation_date: str
    city: str
    state: str
    country: str
    voluntary_mandated: str
    matched_opioid: str          # Which opioid from our registry this matches

@dataclass
class ShortageRecord:
    """Drug shortage status."""
    drug_name: str
    status: str                  # "Current", "Resolved", "Discontinued"
    initial_posting_date: str
    resolved_date: Optional[str]
    reason: str                  # "Manufacturing", "Demand increase", "Discontinuation", "Other"
    matched_opioid: str

@dataclass
class VulnerabilityScore:
    """Supply vulnerability assessment for a single drug."""
    drug_name: str
    score: float                 # 0-100 (higher = more vulnerable)
    tier: str                    # "Critical", "High", "Moderate", "Low"
    factors: Dict[str, float]    # Factor name → normalized value
    manufacturer_count: int
    active_recalls: int
    shortage_status: str         # "Active", "Recent", "None"
    recall_history_24m: int


class SupplyChainMonitor:
    """
    Monitors FDA Enforcement API and Drug Shortage Database for opioid supply risks.

    Data Sources:
    1. FDA Enforcement API (api.fda.gov/drug/enforcement.json) — recall alerts
    2. FDA Drug Shortages — current shortage status
    3. OpenFDA Drug Labels — manufacturer count per product

    Computed Metrics:
    - Supply Vulnerability Score (0-100) per drug
    - Recall severity tracking (Class I/II/III)
    - Shortage timeline tracking
    """

    FDA_ENFORCEMENT_URL = "https://api.fda.gov/drug/enforcement.json"
    FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

    VULNERABILITY_WEIGHTS = {
        "manufacturer_concentration": 0.30,  # Fewer manufacturers = more vulnerable
        "recall_severity": 0.25,             # Recent Class I recalls = high vulnerability
        "recall_frequency": 0.20,            # More recalls = more vulnerable
        "shortage_status": 0.25,             # Active shortage = critical
    }

    TIER_THRESHOLDS = {
        "Critical": 75,
        "High": 50,
        "Moderate": 25,
        "Low": 0,
    }

    def __init__(self, registry=None):
        """
        Initialize with opioid registry for drug name matching.
        If registry is None, load from default path.
        """
        ...

    def fetch_recalls(self, limit: int = 100) -> List[RecallAlert]:
        """
        Query FDA Enforcement API for opioid-related recalls.

        API query: search for each opioid ingredient name in product_description field.
        Use @cached decorator with 2-hour TTL.

        Approach:
        1. Build search query: product_description contains any opioid ingredient
        2. Fetch results, paginate if needed
        3. Parse into RecallAlert objects
        4. Match each recall to our registry drugs

        Handle: API rate limits (40 req/min for no API key), 404 for no results.
        """
        ...

    def fetch_shortages(self) -> List[ShortageRecord]:
        """
        Check FDA Drug Shortage Database for opioid shortages.

        Note: FDA shortage data isn't available via a clean REST API like enforcement.
        Options:
        1. Query OpenFDA label endpoint for "discontinued" status
        2. Use the FDA Drug Shortages RSS feed
        3. Cache a manually curated shortage list

        For demo purposes: query OpenFDA for products with recent labeling changes
        that might indicate supply issues, and check enforcement API for
        "market withdrawal" events.
        """
        ...

    def count_manufacturers(self, drug_name: str) -> int:
        """
        Count distinct manufacturers for a drug using OpenFDA labels.
        Query: openfda.generic_name = drug_name, count by openfda.manufacturer_name
        Use @cached decorator.
        """
        ...

    def compute_vulnerability(self, drug_name: str) -> VulnerabilityScore:
        """
        Compute Supply Vulnerability Score for a single drug.

        Factors (normalized 0-1):
        1. manufacturer_concentration: 1.0 if 1 manufacturer, 0.5 if 2-3, 0.2 if 4+, 0.0 if 10+
        2. recall_severity: max(class weights) of recalls in last 24 months
           - Class I = 1.0, Class II = 0.6, Class III = 0.3, None = 0.0
        3. recall_frequency: count of recalls in 24 months / 5 (capped at 1.0)
        4. shortage_status: Active = 1.0, Recent (resolved <6 months) = 0.5, None = 0.0

        Score = weighted sum × 100
        """
        ...

    def compute_all_vulnerabilities(self) -> List[VulnerabilityScore]:
        """Compute vulnerability for all tracked opioids. Sort by score descending."""
        ...

    def get_active_alerts(self) -> List[RecallAlert]:
        """Return only recalls with status 'Ongoing'."""
        ...

    def get_recall_timeline(self) -> Dict:
        """
        Aggregate recalls by month for trend chart.
        Returns: {"months": [...], "class_i": [...], "class_ii": [...], "class_iii": [...]}
        """
        ...

    def get_supply_summary(self) -> Dict:
        """
        Dashboard summary metrics:
        - total_active_recalls: int
        - total_active_shortages: int
        - drugs_critical_vulnerability: int
        - most_vulnerable_drug: str
        - most_recent_recall: RecallAlert
        """
        ...
```

**Create file: `opioid_track/tests/test_supply_chain.py`**

```python
"""
Tests for Supply Chain Monitor.
pytest opioid_track/tests/test_supply_chain.py -v
"""
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "opioid_registry.json").exists(),
    reason="Registry not built yet"
)

from opioid_track.core.supply_chain_monitor import SupplyChainMonitor, VulnerabilityScore

class TestSupplyChainMonitor:
    def setup_method(self):
        self.monitor = SupplyChainMonitor()

    def test_fetch_recalls_returns_list(self):
        recalls = self.monitor.fetch_recalls(limit=10)
        assert isinstance(recalls, list)

    def test_recall_has_required_fields(self):
        recalls = self.monitor.fetch_recalls(limit=5)
        if recalls:
            r = recalls[0]
            assert r.recall_number
            assert r.classification in ["Class I", "Class II", "Class III"]
            assert r.matched_opioid

    def test_count_manufacturers(self):
        count = self.monitor.count_manufacturers("morphine")
        assert isinstance(count, int)
        assert count >= 0

    def test_vulnerability_score_range(self):
        vs = self.monitor.compute_vulnerability("morphine")
        assert 0 <= vs.score <= 100
        assert vs.tier in ["Critical", "High", "Moderate", "Low"]

    def test_vulnerability_factors_present(self):
        vs = self.monitor.compute_vulnerability("morphine")
        assert "manufacturer_concentration" in vs.factors
        assert "recall_severity" in vs.factors

    def test_supply_summary(self):
        summary = self.monitor.get_supply_summary()
        assert "total_active_recalls" in summary
        assert "most_vulnerable_drug" in summary
```

**Done criteria:** Tests pass. Recall fetching works. Vulnerability scores computed.

---

### Agent B (Sequential after A) — Create Dashboard Page

**Create file: `opioid_track/dashboard/pages/supply_chain.py`**

Sections to implement:

1. **Summary Metrics Bar:**
   - 4 metric cards: Active Recalls, Active Shortages, Critically Vulnerable Drugs, Avg Vulnerability Score
   - Use existing metric card CSS styling

2. **Active Recall Alerts Table:**
   - Filterable by: classification (Class I/II/III), date range, drug name
   - Columns: Date, Drug, Classification, Reason, Status
   - Class I rows highlighted red, Class II amber, Class III gray

3. **Supply Vulnerability Heatmap:**
   - Plotly heatmap: rows = opioid drugs, columns = vulnerability factors
   - Cell color intensity = factor value
   - Sorted by total vulnerability score

4. **Recall Frequency Trend Chart:**
   - Plotly bar chart: monthly recall counts stacked by class
   - X-axis: months, Y-axis: count, Color: Class I (red), II (amber), III (gray)

5. **Drug Shortage Status:**
   - Simple table: Drug, Status (Active/Resolved/None), Duration, Reason
   - Active shortages highlighted

**Modify: `opioid_track/dashboard/opioid_app.py`**
- Add "Supply Chain" to the sidebar navigation radio options (after "Watchdog Tools")
- Add the corresponding page dispatch

**Modify: `opioid_track/config.py`**
```python
# === Supply Chain Configuration ===
FDA_ENFORCEMENT_URL = "https://api.fda.gov/drug/enforcement.json"
SUPPLY_CHAIN_RECALL_LOOKBACK_MONTHS = 24
SUPPLY_CHAIN_CACHE_TTL = 7200  # 2 hours
```

**Done criteria:** Supply Chain page loads in the app. Recalls table populates. Vulnerability heatmap renders.

---

## Execution Order
1. **Agent A** creates monitor module + tests (worktree)
2. **Agent B** creates dashboard page + modifies navigation (sequential)
3. Run tests: `pytest opioid_track/tests/test_supply_chain.py -v`
4. Commit: `git commit -m "feat(opioid): add real-time supply chain risk dashboard with FDA recall monitoring"`

## Checkpoint Protocol
- **Mid-Agent A:** Note which API methods are implemented vs stubbed
- **Mid-Agent B:** Note which dashboard sections are done

## Final Verification
```bash
pytest opioid_track/tests/test_supply_chain.py -v
# Visual: Supply Chain page shows recalls, vulnerability heatmap, trend chart
```
Update `00_STATUS.md` to "COMPLETED".
