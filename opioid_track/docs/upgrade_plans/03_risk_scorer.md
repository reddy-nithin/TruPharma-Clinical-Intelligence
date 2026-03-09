# Sub-Plan 03: Clinical Risk Probability Score

## Priority: After Sub-Plan 01 (needs caching)
## Can parallelize with: Sub-Plan 04, 05, 06, 07

---

## Goal
Build a transparent, explainable 0-100 Clinical Risk Index for opioid drugs. Uses a weighted composite of pharmacological and safety factors with logistic regression to learn optimal weights. Every score comes with a factor-by-factor breakdown (waterfall chart) for clinical credibility.

## Pre-Requisites
- Sub-Plan 01 (Performance Caching) must be COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/core/registry.py` — access to drug profiles, MME factors, schedules
2. `opioid_track/agents/opioid_watchdog.py` — existing `rank_ingredient_sensitivity()` and `assess_dose_risk()` methods
3. `opioid_track/config.py` — MME reference, safety terms, danger classifications
4. `opioid_track/dashboard/pages/drug_explorer.py` — where risk badge will be added
5. `opioid_track/dashboard/pages/watchdog.py` — where risk scores go in comparator
6. `opioid_track/data/opioid_pharmacology.json` — pharmacology data (potency, therapeutic index, LD50, receptor profiles)
7. `opioid_track/data/faers_signal_results.json` — FAERS signal data

---

## Agent Assignment

### Agent A (Worktree: `risk-scorer`) — Create Risk Scorer Module
**Task:** Build the ML-backed risk scoring engine.

**Create directory:** `opioid_track/ml/` (if it doesn't exist, create `__init__.py` too)

**Create file: `opioid_track/ml/risk_scorer.py`**

```python
"""
Clinical Risk Probability Score for opioid drugs.
Transparent weighted composite with ML-learned weights.
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class RiskFactors:
    """Individual risk factor values (all normalized 0-1)."""
    faers_signal_strength: float     # Consensus signal count × avg method agreement
    mme_factor: float                # MME conversion factor (normalized)
    inverse_therapeutic_index: float # 1/TI — lower TI = higher risk
    lethal_dose_proximity: float     # At standard dose, how close to estimated LD
    schedule_severity: float         # CII=1.0, CIII=0.7, CIV=0.4, CV=0.2
    receptor_profile_penalty: float  # Full mu-agonist=1.0, partial=0.5, antagonist=0.1

@dataclass
class RiskResult:
    """Complete risk assessment output."""
    score: float                     # 0-100
    tier: str                        # Critical / High / Elevated / Moderate / Lower
    factors: RiskFactors             # Individual factor values
    factor_contributions: Dict[str, float]  # Factor name → contribution to final score
    tier_thresholds: Dict[str, int]  # Tier name → minimum score


class RiskScorer:
    """
    Computes Clinical Risk Index for opioid drugs.

    Architecture:
    1. Extract 6 pharmacological/safety features for a drug
    2. Normalize each to 0-1 range
    3. Apply learned weights (from logistic regression calibration)
    4. Produce 0-100 composite score
    5. Classify into risk tier
    6. Generate per-factor contribution breakdown
    """

    # Tier thresholds
    TIERS = {
        "Critical": 80,
        "High": 60,
        "Elevated": 40,
        "Moderate": 20,
        "Lower": 0,
    }

    # Default weights (will be overridden by calibration)
    DEFAULT_WEIGHTS = {
        "faers_signal_strength": 0.20,
        "mme_factor": 0.20,
        "inverse_therapeutic_index": 0.20,
        "lethal_dose_proximity": 0.15,
        "schedule_severity": 0.10,
        "receptor_profile_penalty": 0.15,
    }

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Load pharmacology, signal, and registry data.
        Try to load calibrated weights; fall back to defaults.
        """
        ...

    def _load_data(self):
        """Load opioid_pharmacology.json, faers_signal_results.json, opioid_registry.json"""
        ...

    def _load_or_calibrate_weights(self):
        """
        Try to load saved weights from calibration.
        If not found, run calibration and save.
        """
        ...

    def calibrate(self) -> Dict[str, float]:
        """
        Learn optimal weights using logistic regression.

        Training data:
        - Known HIGH risk: fentanyl, carfentanil, sufentanil, remifentanil, oxymorphone
        - Known LOWER risk: codeine, tramadol, dihydrocodeine
        - Everything else: use danger_classification from pharmacology data

        Process:
        1. Extract RiskFactors for all drugs with sufficient data
        2. Label: high-risk = 1, lower-risk = 0 (from known lists + danger classification)
        3. Fit sklearn LogisticRegression (no regularization, small dataset)
        4. Extract coefficients as weights, normalize to sum to 1.0
        5. Save weights to opioid_track/data/risk_weights.json
        """
        ...

    def extract_factors(self, drug_name_or_rxcui: str) -> Optional[RiskFactors]:
        """
        Extract and normalize all 6 risk factors for a given drug.

        Normalization strategy:
        - faers_signal_strength: count of consensus signals / max across all drugs
        - mme_factor: drug's MME factor / max MME factor (fentanyl transdermal ~ 2.4, but
          consider that buprenorphine is 12.6 — cap at sensible max)
        - inverse_therapeutic_index: (1/TI) / max(1/TI) across drugs
        - lethal_dose_proximity: (standard_daily_dose / estimated_LD50) capped at 1.0
        - schedule_severity: CII=1.0, CIII=0.7, CIV=0.4, CV=0.2
        - receptor_profile_penalty: full_mu_agonist=1.0, partial_agonist=0.5,
          mixed_agonist_antagonist=0.3, antagonist=0.1
        """
        ...

    def score(self, drug_name_or_rxcui: str) -> Optional[RiskResult]:
        """
        Compute the full risk assessment for a drug.

        Returns RiskResult with:
        - score: weighted sum of factors × 100
        - tier: based on score thresholds
        - factors: raw factor values
        - factor_contributions: each factor's weighted contribution
        """
        factors = self.extract_factors(drug_name_or_rxcui)
        if factors is None:
            return None

        # Compute weighted score
        contributions = {}
        total = 0.0
        for factor_name, weight in self.weights.items():
            factor_value = getattr(factors, factor_name)
            contribution = factor_value * weight
            contributions[factor_name] = contribution
            total += contribution

        score = min(total * 100, 100.0)
        tier = self._classify_tier(score)

        return RiskResult(
            score=round(score, 1),
            tier=tier,
            factors=factors,
            factor_contributions={k: round(v * 100, 1) for k, v in contributions.items()},
            tier_thresholds=self.TIERS,
        )

    def _classify_tier(self, score: float) -> str:
        """Map score to tier label."""
        for tier, threshold in sorted(self.TIERS.items(), key=lambda x: -x[1]):
            if score >= threshold:
                return tier
        return "Lower"

    def explain_score(self, drug_name_or_rxcui: str) -> Optional[Dict]:
        """
        Returns data formatted for a waterfall chart.
        Output: list of {"factor": str, "contribution": float, "label": str}
        where label is human-readable (e.g., "FAERS Signal Strength: 15.2/100")
        """
        ...

    def compare_risks(self, drug1: str, drug2: str) -> Optional[Dict]:
        """Side-by-side risk comparison. Returns both RiskResults + delta."""
        ...

    def rank_all_drugs(self) -> List[Tuple[str, float, str]]:
        """Returns all scoreable drugs ranked by risk: [(drug_name, score, tier), ...]"""
        ...
```

**Create file: `opioid_track/tests/test_risk_scorer.py`**

```python
"""
Tests for Clinical Risk Probability Score.
pytest opioid_track/tests/test_risk_scorer.py -v
"""
import pytest
from pathlib import Path

# Skip if data files don't exist
DATA_DIR = Path(__file__).parent.parent / "data"
pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "opioid_pharmacology.json").exists(),
    reason="Pharmacology data not built yet"
)

from opioid_track.ml.risk_scorer import RiskScorer, RiskResult

class TestRiskScorer:
    def setup_method(self):
        self.scorer = RiskScorer()

    def test_fentanyl_scores_higher_than_morphine(self):
        fent = self.scorer.score("fentanyl")
        morph = self.scorer.score("morphine")
        assert fent is not None and morph is not None
        assert fent.score > morph.score

    def test_morphine_scores_higher_than_codeine(self):
        morph = self.scorer.score("morphine")
        cod = self.scorer.score("codeine")
        assert morph is not None and cod is not None
        assert morph.score > cod.score

    def test_score_in_valid_range(self):
        result = self.scorer.score("morphine")
        assert result is not None
        assert 0 <= result.score <= 100

    def test_tier_assignment(self):
        result = self.scorer.score("fentanyl")
        assert result is not None
        assert result.tier in ["Critical", "High", "Elevated", "Moderate", "Lower"]

    def test_factor_contributions_sum_to_score(self):
        result = self.scorer.score("morphine")
        assert result is not None
        contrib_sum = sum(result.factor_contributions.values())
        assert abs(contrib_sum - result.score) < 1.0  # within rounding tolerance

    def test_explain_score_returns_waterfall_data(self):
        data = self.scorer.explain_score("morphine")
        assert data is not None
        assert isinstance(data, list)
        assert all("factor" in d and "contribution" in d for d in data)

    def test_compare_risks(self):
        comparison = self.scorer.compare_risks("fentanyl", "codeine")
        assert comparison is not None
        assert "drug1" in comparison and "drug2" in comparison

    def test_rank_all_drugs(self):
        ranked = self.scorer.rank_all_drugs()
        assert len(ranked) > 0
        # Should be sorted descending
        scores = [r[1] for r in ranked]
        assert scores == sorted(scores, reverse=True)
```

**Done criteria:** Tests pass. Fentanyl > morphine > codeine in risk scoring.

---

### Agent B (Sequential after A) — Integrate into Dashboard
**Task:** Add risk badges and waterfall charts to the UI.

**Modify: `opioid_track/dashboard/pages/drug_explorer.py`**
1. Import `RiskScorer` from `opioid_track.ml.risk_scorer`
2. After the drug identity card section, add:
   - Risk badge: colored circle with score number + tier label
     - Critical = red, High = orange-red, Elevated = amber, Moderate = yellow, Lower = green
   - Waterfall chart: Plotly horizontal bar chart showing factor contributions
     - Use `explain_score()` data
     - Bars colored by factor type
     - Total bar at bottom
3. Use theme-aware colors (from Sub-Plan 02 if complete, otherwise hardcode with TODO comment)

**Modify: `opioid_track/dashboard/pages/watchdog.py`**
1. In the Danger Comparator tab:
   - Add risk score display for each drug being compared
   - Show side-by-side factor comparison
2. In the Dose Risk Calculator tab:
   - Show the drug's base risk score alongside the dose-specific risk

**Modify: `opioid_track/agents/opioid_watchdog.py`**
1. Add `get_risk_score(drug_name_or_rxcui)` method
2. Include risk score in `get_pharmacology()` and `compare_drugs()` responses
3. Include risk tier in `query_intelligence_brief()` when relevant

**Done criteria:** Drug Explorer shows risk badge and waterfall chart for any selected drug. Watchdog comparator shows risk scores.

---

## Execution Order
1. **Agent A** creates `risk_scorer.py` + tests (worktree)
2. **Agent B** integrates into dashboard (sequential, needs Agent A)
3. Run all tests: `pytest opioid_track/tests/test_risk_scorer.py -v`
4. Commit: `git commit -m "feat(opioid): add ML-backed Clinical Risk Index with explainability"`

## Checkpoint Protocol
- **Mid-Agent A (calibration):** Note if weight learning is done, which normalization functions are complete
- **Mid-Agent B (dashboard):** Note which page integrations are done

## Final Verification
```bash
pytest opioid_track/tests/test_risk_scorer.py -v
# Visual: Drug Explorer shows risk badge + waterfall for selected drug
```
Update `00_STATUS.md` to "COMPLETED".
