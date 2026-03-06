import os
import json
import pytest
from opioid_track import config
from opioid_track.core import signal_detector


def test_faers_client_initializes():
    """Test that FaersClient initializes correctly."""
    client = signal_detector.FaersClient()
    assert hasattr(client, 'cache')
    assert hasattr(client, '_total_faers')


def test_detect_signals_structure():
    """Test the structure of detect_signals output."""
    client = signal_detector.FaersClient()
    
    # Passing specific method and limited reaction to speed up test and avoid many API calls
    results = client.detect_signals(
        "morphine", 
        reactions=["Respiratory depression"], 
        methods=["prr", "ror"]
    )
    
    assert isinstance(results, list)
    assert len(results) > 0
    
    res = results[0]
    assert "drug_name" in res
    assert res["drug_name"] == "morphine"
    assert "reaction" in res
    assert "report_count" in res
    assert "consensus_signal" in res
    assert "methods_flagging" in res
    assert "source_library" in res
    assert "prr" in res or "ror" in res


def test_source_library_field():
    """Test that the source library field matches expected."""
    client = signal_detector.FaersClient()
    results = client.detect_signals(
        "morphine", 
        reactions=["Respiratory depression"], 
        methods=["prr"]
    )
    assert len(results) > 0
    assert results[0]["source_library"] == "OpenFDA/Mathematical"


def test_cache_file_written(tmp_path):
    """Test that cache mechanism successfully saves."""
    # Temporarily override config to avoid messing with production cache
    original_cache = config.SIGNAL_CACHE_FILE
    temp_cache = str(tmp_path / "test_cache.json")
    config.SIGNAL_CACHE_FILE = temp_cache
    
    try:
        client = signal_detector.FaersClient()
        client.cache["test_key"] = 123
        client._save_cache()
        
        assert os.path.exists(temp_cache)
        with open(temp_cache, "r") as f:
            data = json.load(f)
            assert data.get("test_key") == 123
    finally:
        config.SIGNAL_CACHE_FILE = original_cache
