# Tier 2 — External Data Ingestion + Signal Detection (FINAL)

> All user decisions resolved. Ready for implementation across 4 sessions.

---

## Resolved Decisions

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Census API Key | ✅ User will register at [api.census.gov](https://api.census.gov/data/key_signup.html) (free, instant) |
| 2 | faerslib setup | ✅ Option A — local FAERS SQLite DB via `ChapatiDB/faerslib`. Future migration to BigQuery planned |
| 3 | ARCOS date range | ✅ 2006–2014 accepted. Covers the critical Wave 1→2 period. Fentanyl (Wave 3) is illicit and wouldn't appear in ARCOS anyway |
| 4 | Documentation style | ✅ Detailed (matching `DEV_LOG_TIER1.md` + `TECHNICAL_TIER1.md`) |
| 5 | Data files | ✅ Committed to git (same as Tier 1) |
| 6 | Branch | ✅ Continue on `Week-7-Opioid-track` |
| 7 | Python | ✅ Python 3.11.5 confirmed |

---

## Session Breakdown

### Session A — Config + CMS Fetcher (Steps 2–3)

#### [MODIFY] [config.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/config.py)

Append `# === TIER 2 ADDITIONS ===` block with all new constants: CMS URLs, CDC endpoints, ARCOS settings, signal detection thresholds, Census API base, geographic profile output paths.

#### [NEW] [cms_opioid_fetcher.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/ingestion/cms_opioid_fetcher.py)

- Query CMS Socrata API for Medicare Part D prescribing by geography
- Chunked CSV reading for Provider-and-Drug data (~1.38M rows)
- Filter opioid rows using Tier 1 registry ingredient names
- Flag high prescribers (99th percentile per state+specialty)
- Standardize FIPS codes → 5-digit
- Output: `opioid_prescribing.json`

#### Documentation: Initial `DEV_LOG_TIER2.md` + `TECHNICAL_TIER2.md` scaffolds created and updated

---

### Session B — CDC Mortality + ARCOS Fetcher (Steps 4–5)

#### [NEW] [cdc_mortality_fetcher.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/ingestion/cdc_mortality_fetcher.py)

- **Primary**: CDC VSRR Socrata API (no auth, current data with provisional counts)
- **Supplemental**: CDC WONDER via `alipphardt/cdc-wonder-api` vendor clone (county-level + demographics)
- Graceful degradation if WONDER is unavailable
- Opioid wave tagging (Wave 1/2/3)
- Output: `opioid_mortality.json`

#### [NEW] [arcos_fetcher.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/ingestion/arcos_fetcher.py)

- Try `pip install arcospy` → fallback to vendor clone
- State-level summaries → county-level data for 50 states + DC
- Cached responses in `data/raw/arcos/`, exponential backoff retries
- Output: `opioid_supply_chain.json` (2006–2014)

#### Setup: `opioid_track/vendor/cdc-wonder-api/` (git clone)

---

### Session C — Signal Detection (Step 6)

#### [NEW] [signal_detector.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/core/signal_detector.py)

- Clone `ChapatiDB/faerslib`, install `drugstandards` dependency
- Download raw FAERS quarterly data → build local `faers.db` SQLite
- `detect_signals(drug, reactions, methods)` wrapping PRR/ROR/MGPS
- `run_opioid_signal_scan(top_n_drugs=20)` batch runner
- Consensus signal logic (≥2 methods must agree)
- Cache results to `faers_signal_cache.json`
- Output: `faers_signal_results.json`

---

### Session D — Geographic Joiner + Tests + Validation (Steps 7–9)

#### [NEW] [geographic_joiner.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/core/geographic_joiner.py)

- Join CMS + CDC + ARCOS by county FIPS code
- Census Bureau API for population (with user's API key)
- Derived: `pills_per_death_ratio`, `risk_score` (0–1), `risk_tier` (Low/Medium/High/Critical)
- Output: `opioid_geographic_profiles.json`

#### [NEW] [test_signal_detector.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/tests/test_signal_detector.py) — 6 tests
#### [NEW] [test_geographic_joiner.py](file:///Users/nithinreddy/TruPharma-Clinical-Intelligence/opioid_track/tests/test_geographic_joiner.py) — 5 tests

---

## Final File Structure After Tier 2

```
opioid_track/
├── config.py                            ← APPENDED with Tier 2
├── vendor/
│   ├── cdc-wonder-api/                  ← git clone
│   └── arcos-py/                        ← fallback clone
├── ingestion/
│   ├── cms_opioid_fetcher.py            ← NEW
│   ├── cdc_mortality_fetcher.py         ← NEW
│   └── arcos_fetcher.py                 ← NEW
├── core/
│   ├── signal_detector.py               ← NEW
│   └── geographic_joiner.py             ← NEW
├── data/
│   ├── raw/arcos/                       ← NEW (cache)
│   ├── opioid_prescribing.json          ← NEW
│   ├── opioid_mortality.json            ← NEW
│   ├── opioid_supply_chain.json         ← NEW
│   ├── faers_signal_cache.json          ← NEW
│   ├── faers_signal_results.json        ← NEW
│   └── opioid_geographic_profiles.json  ← NEW
├── tests/
│   ├── test_signal_detector.py          ← NEW
│   └── test_geographic_joiner.py        ← NEW
└── docs/
    ├── DEV_LOG_TIER2.md                 ← NEW
    └── TECHNICAL_TIER2.md               ← NEW
```

## Verification Plan

```bash
# Run each fetcher in order → verify JSON output exists
python -m opioid_track.ingestion.cms_opioid_fetcher
python -m opioid_track.ingestion.cdc_mortality_fetcher
python -m opioid_track.ingestion.arcos_fetcher
python -m opioid_track.core.signal_detector
python -m opioid_track.core.geographic_joiner

# Full test suite (23 existing + 11 new = 34 expected)
pytest opioid_track/tests/ -v

# Verify no Tier 1 files modified
git diff HEAD -- opioid_track/core/registry.py opioid_track/ingestion/rxclass_opioid_fetcher.py
```
