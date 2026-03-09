# Sub-Plan 09: Premium Calls to Action

## Priority: After Sub-Plan 03 (needs Risk Scorer)
## Depends on: Sub-Plan 03 (Risk Scorer for alternative ranking and FHIR resources)

---

## Goal
Add three high-value CTAs: Safer Alternative Suggestions, FHIR RiskAssessment generation, and PDF Risk Report export. These demonstrate real clinical decision support value in demos.

## Pre-Requisites
- Sub-Plan 03 (Risk Scorer) must be COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/ml/risk_scorer.py` — risk scores for alternative ranking
2. `opioid_track/core/registry.py` — drug profiles, categories, MME factors
3. `opioid_track/agents/opioid_watchdog.py` — existing compare_drugs() method
4. `opioid_track/dashboard/pages/drug_explorer.py` — where CTA buttons go
5. `opioid_track/dashboard/pages/watchdog.py` — where CTA buttons go

---

## Agent Assignment

### Agent A (Worktree: `premium-ctas`) — Create Three Core Modules

All three modules can be created in parallel (independent files).

**Create file: `opioid_track/core/alternative_finder.py`**

```python
"""
Safer Alternative Suggestions for opioid prescribing decisions.
Given a drug + dose, finds lower-risk alternatives in the same therapeutic category.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Alternative:
    """A suggested safer alternative."""
    drug_name: str
    rxcui: str
    risk_score: float
    risk_tier: str
    mme_factor: float
    mme_reduction_pct: float       # % reduction vs. current drug
    risk_reduction_pct: float      # % reduction in risk score
    category: str                  # same category as original
    schedule: str
    switching_notes: str           # clinical considerations for switching

@dataclass
class AlternativeReport:
    """Complete alternatives assessment."""
    current_drug: str
    current_risk_score: float
    current_mme_factor: float
    alternatives: List[Alternative]
    non_opioid_note: str           # Always suggest considering non-opioid options


class AlternativeFinder:
    """
    Finds safer opioid alternatives by comparing risk scores and MME factors.

    Logic:
    1. Get current drug's category, risk score, and MME factor
    2. Find all other opioids in the same category
    3. Score each by: risk_score, mme_factor, therapeutic_index
    4. Rank by combined improvement (lower risk + lower MME)
    5. Filter to only those that are genuinely safer (lower risk score)
    6. Add switching considerations
    """

    def __init__(self):
        """Load registry and risk scorer."""
        ...

    def find_alternatives(self, drug_name_or_rxcui: str, current_daily_dose_mg: float = None) -> Optional[AlternativeReport]:
        """
        Find safer alternatives for a given drug.

        Parameters:
        - drug_name_or_rxcui: the current opioid
        - current_daily_dose_mg: optional, used to calculate equianalgesic doses

        Returns AlternativeReport with ranked alternatives.
        Always includes a non_opioid_note suggesting non-opioid options.
        """
        ...

    def _get_switching_notes(self, from_drug: str, to_drug: str) -> str:
        """
        Clinical switching considerations.
        Based on: category match, potency difference, receptor profile match.
        Returns human-readable note about the switch.
        """
        ...

    def _compute_equianalgesic_dose(self, from_drug: str, from_dose_mg: float, to_drug: str) -> Optional[float]:
        """
        Calculate equianalgesic dose for the alternative.
        Uses MME factors: to_dose = from_dose × (from_mme / to_mme)
        """
        ...
```

**Create file: `opioid_track/core/fhir_generator.py`**

```python
"""
FHIR R4 Resource Generator for clinical integration.
Generates valid RiskAssessment and DetectedIssue resources.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional

class FhirGenerator:
    """
    Generates FHIR R4 compliant resources for opioid risk assessments.

    Resources:
    1. RiskAssessment — overall drug risk assessment
    2. DetectedIssue — individual safety signals
    """

    FHIR_VERSION = "4.0.1"

    def generate_risk_assessment(
        self,
        drug_name: str,
        drug_rxcui: str,
        risk_score: float,
        risk_tier: str,
        factor_contributions: Dict[str, float],
        alternatives: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Generate a FHIR R4 RiskAssessment resource.

        Structure:
        {
            "resourceType": "RiskAssessment",
            "id": "trupharma-risk-{rxcui}-{timestamp}",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://trupharma.ai/risk-assessment",
                    "code": "opioid-clinical-risk-index",
                    "display": "Opioid Clinical Risk Index"
                }]
            },
            "subject": {
                "display": "General population assessment"
            },
            "occurrenceDateTime": "ISO 8601 timestamp",
            "basis": [
                {"display": "FAERS Pharmacovigilance Data"},
                {"display": "CDC MME Conversion Factors"},
                {"display": "Pharmacological Profile Data"}
            ],
            "prediction": [{
                "outcome": {
                    "text": "Opioid-related adverse event risk"
                },
                "probabilityDecimal": risk_score / 100,
                "qualitativeRisk": {
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/risk-probability",
                        "code": tier_to_fhir_code(risk_tier),
                        "display": risk_tier
                    }]
                }
            }],
            "mitigation": "Consider alternatives: ..." if alternatives else None,
            "note": [{
                "text": "Generated by TruPharma Clinical Intelligence Platform. "
                        "Risk factors: ..."
            }]
        }
        """
        ...

    def generate_detected_issue(
        self,
        drug_name: str,
        drug_rxcui: str,
        signal_reaction: str,
        signal_methods: List[str],
        signal_strength: float,
    ) -> Dict:
        """
        Generate a FHIR R4 DetectedIssue resource for a safety signal.

        Structure:
        {
            "resourceType": "DetectedIssue",
            "id": "trupharma-signal-{rxcui}-{reaction_hash}",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                    "code": "DRG",
                    "display": "Drug Interaction Alert"
                }]
            },
            "severity": "high" | "moderate" | "low",
            "detail": "FAERS consensus signal: {reaction} detected for {drug}",
            "evidence": [{
                "detail": [{"display": f"Method: {method}"}]
            }]
        }
        """
        ...

    def to_json(self, resource: Dict, pretty: bool = True) -> str:
        """Serialize FHIR resource to JSON string."""
        return json.dumps(resource, indent=2 if pretty else None, default=str)

    def validate_resource(self, resource: Dict) -> bool:
        """
        Basic FHIR validation:
        - Has resourceType
        - Has id
        - Has status
        - Required fields present based on resourceType
        """
        ...
```

**Create file: `opioid_track/core/report_generator.py`**

```python
"""
PDF Risk Report Generator for TruPharma Opioid Track.
Generates branded clinical risk reports using fpdf2.
"""
from fpdf import FPDF
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import io

class OpioidRiskReport(FPDF):
    """
    Custom PDF report with TruPharma branding.

    Sections:
    1. Header with TruPharma branding
    2. Drug Profile Summary
    3. Clinical Risk Index (score + tier + factor breakdown)
    4. Active FAERS Signals
    5. Safer Alternatives
    6. Geographic Context (if state selected)
    7. Methodology Notes
    8. Footer with timestamp + disclaimer
    """

    # Brand colors
    TEAL = (0, 229, 200)
    DARK_BG = (10, 15, 26)
    TEXT = (232, 237, 245)

    def header(self):
        """TruPharma branded header."""
        self.set_fill_color(*self.DARK_BG)
        self.rect(0, 0, 210, 25, 'F')
        self.set_text_color(*self.TEAL)
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 15, 'TruPharma Clinical Intelligence', ln=True, align='C')
        self.set_font('Helvetica', '', 10)
        self.set_text_color(*self.TEXT)
        self.cell(0, 8, 'Opioid Risk Assessment Report', ln=True, align='C')
        self.ln(5)

    def footer(self):
        """Footer with timestamp and disclaimer."""
        self.set_y(-20)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 5, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")}', ln=True, align='C')
        self.cell(0, 5, 'For informational purposes only. Not a substitute for clinical judgment.', align='C')


class ReportGenerator:
    """
    Generates PDF risk reports.

    Usage:
        gen = ReportGenerator()
        pdf_bytes = gen.generate(
            drug_name="Fentanyl",
            drug_profile={...},
            risk_result=RiskResult(...),
            signals=[...],
            alternatives=AlternativeReport(...),
            geographic_context={"state": "OH", ...}
        )
        # pdf_bytes is a bytes object ready for download
    """

    def generate(
        self,
        drug_name: str,
        drug_profile: Dict,
        risk_result=None,           # RiskResult from risk_scorer
        signals: Optional[List[Dict]] = None,
        alternatives=None,          # AlternativeReport from alternative_finder
        geographic_context: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate complete PDF report.

        Returns bytes object (use st.download_button with this).

        Sections:
        1. Drug Profile: name, schedule, category, active ingredients, RxCUI
        2. Risk Assessment: score gauge, tier badge, factor contributions table
        3. Safety Signals: table of consensus signals with method agreement
        4. Alternatives: ranked list with risk/MME comparison
        5. Geographic Context: state-level metrics if provided
        6. Methodology: brief description of data sources and scoring method
        """
        pdf = OpioidRiskReport()
        pdf.add_page()

        self._add_drug_profile(pdf, drug_name, drug_profile)
        if risk_result:
            self._add_risk_assessment(pdf, risk_result)
        if signals:
            self._add_signals(pdf, signals)
        if alternatives:
            self._add_alternatives(pdf, alternatives)
        if geographic_context:
            self._add_geographic(pdf, geographic_context)
        self._add_methodology(pdf)

        return bytes(pdf.output())

    def _add_drug_profile(self, pdf, drug_name, profile):
        """Drug identity section."""
        ...

    def _add_risk_assessment(self, pdf, risk_result):
        """Risk score with factor breakdown table."""
        ...

    def _add_signals(self, pdf, signals):
        """Safety signals table."""
        ...

    def _add_alternatives(self, pdf, alternatives):
        """Safer alternatives list."""
        ...

    def _add_geographic(self, pdf, context):
        """Geographic context metrics."""
        ...

    def _add_methodology(self, pdf):
        """Data sources and methodology notes."""
        ...
```

**Create file: `opioid_track/tests/test_premium_ctas.py`**

```python
"""Tests for Premium CTAs: Alternative Finder, FHIR Generator, Report Generator."""
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

class TestAlternativeFinder:
    pytestmark = pytest.mark.skipif(
        not (DATA_DIR / "opioid_registry.json").exists(), reason="No registry"
    )

    def test_finds_alternatives_for_fentanyl(self):
        from opioid_track.core.alternative_finder import AlternativeFinder
        finder = AlternativeFinder()
        report = finder.find_alternatives("fentanyl")
        assert report is not None
        assert len(report.alternatives) > 0
        # All alternatives should have lower risk
        for alt in report.alternatives:
            assert alt.risk_score < report.current_risk_score

    def test_includes_non_opioid_note(self):
        from opioid_track.core.alternative_finder import AlternativeFinder
        finder = AlternativeFinder()
        report = finder.find_alternatives("morphine")
        assert report is not None
        assert report.non_opioid_note  # Should always be present


class TestFhirGenerator:
    def test_risk_assessment_valid(self):
        from opioid_track.core.fhir_generator import FhirGenerator
        gen = FhirGenerator()
        resource = gen.generate_risk_assessment(
            drug_name="Morphine", drug_rxcui="7052",
            risk_score=55.0, risk_tier="Elevated",
            factor_contributions={"mme_factor": 15.0, "faers_signal_strength": 20.0}
        )
        assert resource["resourceType"] == "RiskAssessment"
        assert resource["status"] == "final"
        assert gen.validate_resource(resource)

    def test_detected_issue_valid(self):
        from opioid_track.core.fhir_generator import FhirGenerator
        gen = FhirGenerator()
        resource = gen.generate_detected_issue(
            drug_name="Morphine", drug_rxcui="7052",
            signal_reaction="Respiratory Depression",
            signal_methods=["PRR", "ROR"],
            signal_strength=0.8
        )
        assert resource["resourceType"] == "DetectedIssue"
        assert gen.validate_resource(resource)

    def test_json_serialization(self):
        from opioid_track.core.fhir_generator import FhirGenerator
        gen = FhirGenerator()
        resource = gen.generate_risk_assessment("Test", "0000", 50.0, "Moderate", {})
        json_str = gen.to_json(resource)
        assert '"resourceType": "RiskAssessment"' in json_str


class TestReportGenerator:
    def test_generates_pdf_bytes(self):
        from opioid_track.core.report_generator import ReportGenerator
        gen = ReportGenerator()
        pdf_bytes = gen.generate(
            drug_name="Morphine",
            drug_profile={"schedule": "CII", "category": "natural"},
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:4] == b'%PDF'  # Valid PDF header
```

**Done criteria:** All three modules importable. Tests pass. PDF has valid header.

---

### Agent B (Sequential after A) — Integrate CTAs into Dashboard

**Modify: `opioid_track/dashboard/pages/drug_explorer.py`**

Add CTA section after the main drug information:

```python
# --- Premium Actions ---
st.markdown("### Actions")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("Suggest Safer Alternatives", use_container_width=True):
        from opioid_track.core.alternative_finder import AlternativeFinder
        finder = AlternativeFinder()
        report = finder.find_alternatives(selected_drug_rxcui)
        if report:
            st.markdown(f"**Current Risk Score:** {report.current_risk_score}")
            for alt in report.alternatives:
                st.markdown(f"- **{alt.drug_name}**: Risk {alt.risk_score} "
                           f"({alt.risk_reduction_pct:.0f}% lower)")
            st.info(report.non_opioid_note)

with col2:
    if st.button("Generate EMR Alert (FHIR)", use_container_width=True):
        from opioid_track.core.fhir_generator import FhirGenerator
        gen = FhirGenerator()
        resource = gen.generate_risk_assessment(...)
        st.json(resource)
        st.download_button("Download FHIR JSON", gen.to_json(resource),
                          file_name=f"risk_assessment_{selected_drug}.json",
                          mime="application/json")

with col3:
    if st.button("Export PDF Report", use_container_width=True):
        from opioid_track.core.report_generator import ReportGenerator
        gen = ReportGenerator()
        pdf_bytes = gen.generate(drug_name=..., drug_profile=..., risk_result=..., signals=...)
        st.download_button("Download PDF", pdf_bytes,
                          file_name=f"risk_report_{selected_drug}.pdf",
                          mime="application/pdf")
```

**Modify: `opioid_track/dashboard/pages/watchdog.py`**
- Add "Export Report" button to Dose Risk Calculator (after risk assessment display)
- Add "Compare & Export" button to Danger Comparator

**Add to requirements:** `fpdf2>=2.7.0`

**Done criteria:** All 3 CTA buttons work on Drug Explorer. PDF downloads. FHIR JSON is valid and downloadable. Alternatives display correctly.

---

## Execution Order
1. **Agent A** creates all 3 modules + tests (worktree — independent files)
2. **Agent B** integrates CTAs into dashboard pages (sequential)
3. Run tests: `pytest opioid_track/tests/test_premium_ctas.py -v`
4. Commit: `git commit -m "feat(opioid): add safer alternatives, FHIR generation, and PDF risk reports"`

## Checkpoint Protocol
- **Mid-Agent A:** Note which of the 3 modules are done
- **Mid-Agent B:** Note which page integrations are done

## Final Verification
```bash
pytest opioid_track/tests/test_premium_ctas.py -v
# Visual: Drug Explorer → click each CTA button → verify output
# Download PDF → verify it's valid and readable
# Download FHIR JSON → verify valid structure
```
Update `00_STATUS.md` to "COMPLETED".
