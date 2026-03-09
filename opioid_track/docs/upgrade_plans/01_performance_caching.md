# Sub-Plan 01: Performance Caching Layer

## Priority: FIRST (no dependencies)
## Can parallelize with: Sub-Plan 02, 06, 07

---

## Goal
Replace raw 44MB `opioid_registry.json` loading with SQLite-backed cache. Add `@cached` decorator for all external API calls. This is the foundation — all ML and analytics features depend on fast data access.

## Pre-Requisites
- Read `00_STATUS.md` first. If this sub-plan shows "IN_PROGRESS", skip to the Last Checkpoint.
- Update `00_STATUS.md` to mark this as "IN_PROGRESS" before starting.

## Context Files to Read First
These files contain the current implementation you'll be modifying:
1. `opioid_track/config.py` — current config structure (262 lines)
2. `opioid_track/core/registry.py` — current JSON-loading singleton (255 lines)
3. `opioid_track/core/signal_detector.py` — current OpenFDA API calls (308 lines)

---

## Agent Assignment

### Agent A (Worktree: `cache-core`) — Create Cache Module
**Task:** Create the new cache module from scratch.

**Create file: `opioid_track/core/cache.py`**

```python
"""
SQLite-backed cache with TTL expiration for TruPharma Opioid Track.
Replaces raw JSON loading and caches external API responses.
"""
import sqlite3
import json
import time
import hashlib
import functools
from pathlib import Path
from typing import Any, Optional, Callable

# Default cache DB location
DEFAULT_CACHE_DB = Path(__file__).parent.parent / "data" / "cache.db"

class CacheManager:
    """
    Singleton SQLite cache manager.

    Tables:
    - kv_cache: general key-value store with TTL
      Columns: key TEXT PRIMARY KEY, value TEXT, created_at REAL, ttl_seconds INTEGER

    Usage:
        cache = CacheManager()
        cache.set("registry:drugs", json.dumps(drugs), ttl=86400)
        drugs = cache.get("registry:drugs")  # returns None if expired
    """
    _instance = None

    def __new__(cls, db_path=None):
        # Singleton pattern
        ...

    def __init__(self, db_path=None):
        # Initialize SQLite DB, create tables if not exist
        # Use WAL mode for concurrent reads
        ...

    def _create_tables(self):
        """
        CREATE TABLE IF NOT EXISTS kv_cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL,
            ttl_seconds INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_kv_cache_created ON kv_cache(created_at);
        """
        ...

    def get(self, key: str) -> Optional[str]:
        """
        Get value by key. Returns None if key doesn't exist or TTL expired.
        Automatically deletes expired entries on access.
        """
        ...

    def get_json(self, key: str) -> Optional[Any]:
        """Get and JSON-deserialize. Returns None if missing/expired."""
        ...

    def set(self, key: str, value: str, ttl: int = 3600) -> None:
        """Set value with TTL in seconds. Overwrites existing."""
        ...

    def set_json(self, key: str, value: Any, ttl: int = 3600) -> None:
        """JSON-serialize and set."""
        ...

    def invalidate(self, key: str) -> None:
        """Delete specific key."""
        ...

    def invalidate_prefix(self, prefix: str) -> None:
        """Delete all keys starting with prefix. E.g., invalidate_prefix('registry:')"""
        ...

    def clear_expired(self) -> int:
        """Delete all expired entries. Returns count deleted."""
        ...

    def clear_all(self) -> None:
        """Nuclear option — clear entire cache."""
        ...


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator that caches function return values in SQLite.

    Cache key = prefix + function_name + hash(args, kwargs)

    Usage:
        @cached(ttl=86400, key_prefix="registry")
        def load_opioid_drugs():
            ...

        @cached(ttl=3600, key_prefix="openfda")
        def fetch_adverse_events(drug_name: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key from prefix + func name + hashed args
            cache = CacheManager()
            cache_key = _build_key(key_prefix, func.__name__, args, kwargs)

            # Try cache first
            result = cache.get_json(cache_key)
            if result is not None:
                return result

            # Cache miss — call function
            result = func(*args, **kwargs)

            # Store in cache
            if result is not None:
                cache.set_json(cache_key, result, ttl=ttl)

            return result
        return wrapper
    return decorator


def _build_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """Build deterministic cache key from function signature."""
    raw = f"{prefix}:{func_name}:{repr(args)}:{repr(sorted(kwargs.items()))}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
```

**Create file: `opioid_track/tests/test_cache.py`**

```python
"""
Tests for CacheManager and @cached decorator.
Test with: pytest opioid_track/tests/test_cache.py -v
"""
import pytest
import time
import tempfile
from opioid_track.core.cache import CacheManager, cached

class TestCacheManager:
    def setup_method(self):
        """Use temp DB for each test."""
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        # Reset singleton for testing
        CacheManager._instance = None
        self.cache = CacheManager(db_path=self.tmp.name)

    def test_set_and_get(self):
        self.cache.set("key1", "value1", ttl=60)
        assert self.cache.get("key1") == "value1"

    def test_get_missing_key_returns_none(self):
        assert self.cache.get("nonexistent") is None

    def test_ttl_expiration(self):
        self.cache.set("key1", "value1", ttl=1)
        time.sleep(1.1)
        assert self.cache.get("key1") is None

    def test_json_round_trip(self):
        data = {"drugs": [{"rxcui": "7052", "name": "Morphine"}]}
        self.cache.set_json("registry:drugs", data, ttl=60)
        assert self.cache.get_json("registry:drugs") == data

    def test_invalidate(self):
        self.cache.set("key1", "value1", ttl=60)
        self.cache.invalidate("key1")
        assert self.cache.get("key1") is None

    def test_invalidate_prefix(self):
        self.cache.set("registry:drugs", "d", ttl=60)
        self.cache.set("registry:ndc", "n", ttl=60)
        self.cache.set("openfda:events", "e", ttl=60)
        self.cache.invalidate_prefix("registry:")
        assert self.cache.get("registry:drugs") is None
        assert self.cache.get("registry:ndc") is None
        assert self.cache.get("openfda:events") == "e"

    def test_clear_expired(self):
        self.cache.set("exp1", "v1", ttl=1)
        self.cache.set("fresh", "v2", ttl=60)
        time.sleep(1.1)
        count = self.cache.clear_expired()
        assert count >= 1
        assert self.cache.get("fresh") == "v2"

    def test_overwrite_existing_key(self):
        self.cache.set("key1", "old", ttl=60)
        self.cache.set("key1", "new", ttl=60)
        assert self.cache.get("key1") == "new"


class TestCachedDecorator:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        CacheManager._instance = None
        CacheManager(db_path=self.tmp.name)
        self.call_count = 0

    def test_caches_return_value(self):
        @cached(ttl=60, key_prefix="test")
        def expensive_func(x):
            self.call_count += 1
            return x * 2

        result1 = expensive_func(5)
        result2 = expensive_func(5)
        assert result1 == result2 == 10
        assert self.call_count == 1  # called only once

    def test_different_args_different_cache(self):
        @cached(ttl=60, key_prefix="test")
        def func(x):
            self.call_count += 1
            return x

        func(1)
        func(2)
        assert self.call_count == 2
```

**Done criteria:** `pytest opioid_track/tests/test_cache.py -v` — all tests pass.

---

### Agent B (Same branch, sequential after Agent A) — Integrate Cache into Registry
**Task:** Modify the existing registry to use the new cache layer.

**Read first:** `opioid_track/core/registry.py` (the current implementation)

**Modify: `opioid_track/core/registry.py`**
Changes needed:
1. Import `CacheManager` from `opioid_track.core.cache`
2. In `_load_registry()` method:
   - Before loading JSON, try `cache.get_json("registry:full")`
   - If cache hit, use cached data
   - If cache miss, load from JSON file (current behavior), then `cache.set_json("registry:full", data, ttl=86400)`
3. Add lazy-loading for subsections:
   - `_load_drugs()` — loads only `opioid_drugs` array, cached separately as `registry:drugs`
   - `_load_ndc_lookup()` — loads only `ndc_lookup`, cached as `registry:ndc`
   - `_load_mme_reference()` — loads only `mme_reference`, cached as `registry:mme`
4. Modify accessor methods to use lazy-loaded sections instead of full registry

**Done criteria:** App loads and all existing `test_registry.py` tests still pass.

---

### Agent C (Same branch, sequential after Agent A) — Integrate Cache into Signal Detector
**Task:** Add caching to OpenFDA API calls in signal_detector.py.

**Read first:** `opioid_track/core/signal_detector.py`

**Modify: `opioid_track/core/signal_detector.py`**
Changes needed:
1. Import `cached` decorator from `opioid_track.core.cache`
2. Wrap `_fetch_count()` or equivalent API call method with `@cached(ttl=21600, key_prefix="openfda")` (6h TTL)
3. Remove any existing manual caching logic (the current code has a cache mechanism — replace it with the unified SQLite cache)
4. Ensure the cache key includes drug name + reaction term so different queries get different cache entries

**Done criteria:** `pytest opioid_track/tests/test_signal_detector.py -v` passes. Signal detection still works with cached API responses.

---

### Agent D (Same branch, sequential after Agent A) — Config Updates
**Task:** Add cache configuration to config.py.

**Modify: `opioid_track/config.py`**
Add these constants:
```python
# === Cache Configuration ===
CACHE_DB_PATH = DATA_DIR / "cache.db"
CACHE_TTL = {
    "registry": 86400,      # 24 hours
    "api_response": 3600,   # 1 hour
    "signal": 21600,        # 6 hours
    "forecast": 43200,      # 12 hours
    "supply_chain": 7200,   # 2 hours
}
```

---

## Execution Order
1. **Agent A** creates `cache.py` + `test_cache.py` (can use worktree)
2. **Agent B** integrates cache into registry (sequential, needs Agent A's files)
3. **Agent C** integrates cache into signal detector (can run parallel with B)
4. **Agent D** updates config (can run parallel with B and C)
5. Run all tests: `pytest opioid_track/tests/ -v`
6. Commit: `git commit -m "feat(opioid): add SQLite-backed caching layer for registry and API calls"`

## Checkpoint Protocol
After each agent completes, update `00_STATUS.md`:
- Mark completed sub-tasks with [x]
- Set "Last Checkpoint" to: "Agent [A/B/C/D] complete. Next: Agent [X]"
- If hitting limits mid-agent, describe exactly which function/method you were working on

## Final Verification
```bash
pytest opioid_track/tests/test_cache.py -v
pytest opioid_track/tests/test_registry.py -v
pytest opioid_track/tests/test_signal_detector.py -v
```
All must pass. Then update `00_STATUS.md` status to "COMPLETED".
