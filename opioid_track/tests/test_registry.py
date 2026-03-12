"""
Opioid Registry Tests
======================
Tests for the opioid registry runtime API.
Requires the registry to be built first (run ingestion + registry_builder).
"""

import os
import pytest

# Skip all tests if registry not built yet
REGISTRY_PATH = "opioid_track/data/opioid_registry.json"
pytestmark = pytest.mark.skipif(
    not os.path.exists(REGISTRY_PATH),
    reason=f"Registry not built. Run ingestion pipeline first."
)

from opioid_track.core import registry


class TestRegistryLoads:
    def test_registry_loads_without_error(self):
        stats = registry.registry_stats()
        assert isinstance(stats, dict)
        assert stats["total_opioid_rxcuis"] > 0

    def test_registry_version(self):
        version = registry.registry_version()
        assert version in ("1.0.0", "1.5.0")


class TestIsOpioid:
    def test_morphine_is_opioid(self):
        # Morphine RxCUI = 7052
        assert registry.is_opioid("7052") is True

    def test_non_opioid_returns_false(self):
        # Amoxicillin RxCUI = 723 (antibiotic, not in any opioid combo)
        assert registry.is_opioid("723") is False

    def test_naloxone_is_opioid(self):
        # Naloxone RxCUI = 7242
        assert registry.is_opioid("7242") is True


class TestOpioidProfile:
    def test_morphine_profile(self):
        # Try multiple known morphine RxCUIs
        profile = registry.get_opioid_profile("7052")
        if profile is None:
            # Try the salt form
            profile = registry.get_opioid_profile("235751")
        assert profile is not None
        assert "rxcui" in profile
        assert "drug_name" in profile
        assert "atc_codes" in profile or "opioid_category" in profile

    def test_nonexistent_profile(self):
        assert registry.get_opioid_profile("9999999") is None


class TestMMEFactor:
    def test_morphine_mme(self):
        assert registry.get_mme_factor("morphine") == 1.0

    def test_codeine_mme(self):
        assert registry.get_mme_factor("codeine") == 0.15

    def test_unknown_drug_mme(self):
        assert registry.get_mme_factor("ibuprofen") is None


class TestCalculateDailyMME:
    def test_oxycodone_30mg(self):
        result = registry.calculate_daily_mme("oxycodone", 30)
        assert result["daily_mme"] == 45.0
        assert result["risk_level"] == "normal"

    def test_oxycodone_60mg_high_risk(self):
        result = registry.calculate_daily_mme("oxycodone", 60)
        assert result["daily_mme"] == 90.0
        assert result["risk_level"] == "high"

    def test_oxycodone_40mg_increased_risk(self):
        result = registry.calculate_daily_mme("oxycodone", 40)
        assert result["daily_mme"] == 60.0
        assert result["risk_level"] == "increased"

    def test_unknown_ingredient(self):
        result = registry.calculate_daily_mme("aspirin", 500)
        assert result["daily_mme"] is None
        assert result["risk_level"] == "unknown"


class TestOpioidsByCategory:
    def test_synthetic_includes_expected(self):
        synthetic = registry.get_opioids_by_category("synthetic")
        names = [d["drug_name"].lower() for d in synthetic]
        # At least some synthetic opioids should be present
        assert len(synthetic) > 0
        # Check that well-known synthetics are found
        all_names_str = " ".join(names)
        found_any = any(
            drug in all_names_str
            for drug in ["fentanyl", "tramadol", "methadone", "meperidine"]
        )
        assert found_any, f"Expected synthetic opioids not found in: {names}"


class TestListAllRxcuis:
    def test_rxcui_count(self):
        rxcuis = registry.list_all_opioid_rxcuis()
        assert isinstance(rxcuis, list)
        # We have 85 drugs + their ingredients ≈ 189 unique RxCUIs
        assert len(rxcuis) >= 50, f"Only {len(rxcuis)} RxCUIs found"


class TestNDCNormalization:
    def test_ndc_normalization(self):
        # Test that different NDC formats normalize correctly
        ndc1 = registry.normalize_ndc("0069-0770-20")
        ndc2 = registry.normalize_ndc("00069077020")
        assert ndc1 == ndc2 == "00069077020"

    def test_ndc_with_short_segments(self):
        ndc = registry.normalize_ndc("69-770-20")
        assert ndc == "00069077020"


class TestDataSourceProvenance:
    def test_ripl_org_data_present(self):
        """At least one NDC has source == 'ripl-org-historical'."""
        ndcs = registry.list_all_opioid_ndcs()
        # Just verify the NDC lookup has ripl-org data
        registry._ensure_loaded()
        ndc_lookup = registry._REGISTRY.get("ndc_lookup", {})
        ripl_count = sum(
            1 for e in ndc_lookup.values()
            if e.get("source") == "ripl-org-historical"
        )
        assert ripl_count > 0, "No ripl-org-historical NDCs found"

    def test_jbadger3_data_present(self):
        """At least one RxCUI in mme_reference has jbadger3 source."""
        registry._ensure_loaded()
        mme_ref = registry._REGISTRY.get("mme_reference", {})
        rxcui_map = mme_ref.get("rxcui_mme_map", {})
        jbadger_count = sum(
            1 for e in rxcui_map.values()
            if e.get("source") == "jbadger3/ml_4_pheno_ooe"
        )
        assert jbadger_count > 0, "No jbadger3/ml_4_pheno_ooe entries found"


class TestFAERSBaseline:
    def test_faers_baseline_exists(self):
        baseline = registry.get_faers_baseline()
        assert isinstance(baseline, dict)
        assert "top_reactions" in baseline or "fetched_at" in baseline

class TestTier1_5_Functions:
    def test_search_opioid_products(self):
        results = registry.search_opioid_products("oxycodone")
        assert isinstance(results, list)

    def test_get_newly_approved_opioids(self):
        results = registry.get_newly_approved_opioids(2024)
        assert isinstance(results, list)
