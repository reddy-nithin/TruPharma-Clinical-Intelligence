"""
Tier 3 Tests — Pharmacology, Toxicology, NLP, and Knowledge Chunks
===================================================================
8 test cases covering Tier 3 outputs as specified in Step 10.
"""

import json
import os
import pytest

from opioid_track import config


@pytest.fixture(scope="module")
def pharmacology_data():
    assert os.path.exists(config.PHARMACOLOGY_OUTPUT), (
        f"opioid_pharmacology.json not found at {config.PHARMACOLOGY_OUTPUT}"
    )
    with open(config.PHARMACOLOGY_OUTPUT, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def nlp_data():
    assert os.path.exists(config.NLP_INSIGHTS_OUTPUT), (
        f"opioid_nlp_insights.json not found at {config.NLP_INSIGHTS_OUTPUT}"
    )
    with open(config.NLP_INSIGHTS_OUTPUT, "r") as f:
        return json.load(f)


class TestPharmacologyData:
    """Tests for opioid_pharmacology.json (Steps 4 + 5)."""

    def test_pharmacology_loads(self, pharmacology_data):
        """Test 1: opioid_pharmacology.json exists and loads successfully."""
        assert isinstance(pharmacology_data, dict)
        assert "metadata" in pharmacology_data
        assert "ingredient_pharmacology" in pharmacology_data

    def test_morphine_mu_receptor(self, pharmacology_data):
        """Test 2: Morphine has mu receptor data with a Ki value."""
        ingredients = pharmacology_data["ingredient_pharmacology"]
        assert "morphine" in ingredients, "Morphine missing from pharmacology data"
        morphine = ingredients["morphine"]
        affinities = morphine.get("receptor_affinities", {})
        assert "mu" in affinities, "Morphine missing mu receptor data"
        assert affinities["mu"].get("ki_nM") is not None, "Morphine mu Ki value is None"
        assert isinstance(affinities["mu"]["ki_nM"], (int, float)), "Ki must be numeric"

    def test_morphine_potency_baseline(self, pharmacology_data):
        """Test 3: Morphine potency_vs_morphine should be 1.0 (reference)."""
        morphine = pharmacology_data["ingredient_pharmacology"]["morphine"]
        potency = morphine.get("potency_vs_morphine")
        assert potency is not None, "Morphine potency_vs_morphine is None"
        assert potency == pytest.approx(1.0, abs=0.01), (
            f"Morphine potency should be 1.0, got {potency}"
        )

    def test_receptor_data_coverage(self, pharmacology_data):
        """Test 4: At least 10 ingredients have receptor affinity data."""
        ingredients = pharmacology_data["ingredient_pharmacology"]
        with_receptor = sum(
            1 for data in ingredients.values()
            if data.get("receptor_affinities")
        )
        assert with_receptor >= 10, (
            f"Expected ≥10 ingredients with receptor data, got {with_receptor}"
        )

    def test_why_opioid_populated(self, pharmacology_data):
        """Test 5: why_its_an_opioid text is populated for at least 10 ingredients."""
        ingredients = pharmacology_data["ingredient_pharmacology"]
        with_explanation = sum(
            1 for data in ingredients.values()
            if data.get("why_its_an_opioid") and len(data["why_its_an_opioid"]) > 20
        )
        assert with_explanation >= 10, (
            f"Expected ≥10 ingredients with why_its_an_opioid, got {with_explanation}"
        )

    def test_ld50_coverage(self, pharmacology_data):
        """Test 6: LD50 data exists for at least 5 ingredients."""
        ingredients = pharmacology_data["ingredient_pharmacology"]
        with_ld50 = sum(
            1 for data in ingredients.values()
            if data.get("ld50_data") and len(data["ld50_data"]) > 0
        )
        assert with_ld50 >= 5, (
            f"Expected ≥5 ingredients with LD50 data, got {with_ld50}"
        )


class TestNLPInsights:
    """Tests for opioid_nlp_insights.json (Step 6)."""

    def test_nlp_source_attribution(self, nlp_data):
        """Test 7: NLP insights metadata contains CDCgov source attribution."""
        metadata = nlp_data.get("metadata", {})
        assert metadata.get("nlp_source") == "CDCgov/Opioid_Involvement_NLP", (
            f"Expected nlp_source='CDCgov/Opioid_Involvement_NLP', "
            f"got '{metadata.get('nlp_source')}'"
        )


class TestVendorRepos:
    """Tests for vendor repository presence (Step 3)."""

    def test_vendor_repos_present(self):
        """Test 8: Vendor repos are cloned and present."""
        cdc_nlp = os.path.join("opioid_track", "vendor", "Opioid_Involvement_NLP")
        dash_demo = os.path.join("opioid_track", "vendor", "dash-opioid-epidemic-demo")

        assert os.path.isdir(cdc_nlp), (
            f"CDCgov/Opioid_Involvement_NLP not found at {cdc_nlp}"
        )
        assert os.path.isdir(dash_demo), (
            f"plotly/dash-opioid-epidemic-demo not found at {dash_demo}"
        )
