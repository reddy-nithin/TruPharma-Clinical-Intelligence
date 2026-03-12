
import pytest
from opioid_track.agents.opioid_watchdog import OpioidWatchdog

@pytest.fixture
def watchdog():
    return OpioidWatchdog()

def test_sensitivity_ranking_fentanyl(watchdog):
    """Test sensitivity ranking for a high-potency single ingredient drug."""
    # Fentanyl RxCUI or name
    result = watchdog.rank_ingredient_sensitivity("fentanyl")
    
    assert "error" not in result
    assert result["drug_name"].lower() == "fentanyl"
    assert result["most_sensitive_ingredient"].lower() == "fentanyl"
    
    # Fentanyl should have a high score because of its potency and danger rank
    fent_data = next(i for i in result["ingredients"] if i["name"].lower() == "fentanyl")
    assert fent_data["sensitivity_score"] > 40
    assert fent_data["danger_level"] == "High"

def test_sensitivity_ranking_combination(watchdog):
    """Test sensitivity ranking for a combination product (e.g., Oxycodone/Naloxone)."""
    # Using a known combination name
    result = watchdog.rank_ingredient_sensitivity("naloxone / oxycodone")
    
    assert "error" not in result
    ingredients = [i["name"].lower() for i in result["ingredients"]]
    assert "oxycodone" in ingredients
    assert "naloxone" in ingredients
    
    # Both should be identified as ingredients, and the primary opioid (oxycodone) 
    # or the receptor ligand (naloxone) should be ranked.
    assert len(result["ingredients"]) >= 2
    
def test_sensitivity_ranking_non_opioid(watchdog):
    """Test that non-opioids are handled gracefully or return appropriate errors."""
    # Metformin should not match any opioid products in our registry
    result = watchdog.rank_ingredient_sensitivity("metformin")
    # Should find no opioid components or return an error if not in registry
    assert "error" in result or len([i for i in result.get("ingredients", []) if i.get("is_opioid_component")]) == 0

def test_sensitivity_logic_explanation(watchdog):
    """Verify that the explanation string contains key pharmacological terms."""
    result = watchdog.rank_ingredient_sensitivity("fentanyl")
    explanation = result.get("explanation", "")
    
    assert "potency" in explanation.lower()
    assert "lethal dose" in explanation.lower()
    assert "danger" in explanation.lower()
