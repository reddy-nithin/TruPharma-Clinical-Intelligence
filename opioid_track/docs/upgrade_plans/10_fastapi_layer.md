# Sub-Plan 10: FastAPI Layer

## Priority: After Sub-Plans 01, 03, 04, 05 (needs all core modules)
## Depends on: Caching, Risk Scorer, Forecaster, Supply Chain

---

## Goal
Build a production-ready REST API exposing all opioid intelligence modules. Auto-generated Swagger UI at `/docs` impresses in demos. API key authentication for enterprise credibility.

## Pre-Requisites
- Sub-Plans 01 (Caching), 03 (Risk Scorer), 04 (Forecaster), 05 (Supply Chain) COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/core/registry.py` — drug lookup methods to expose
2. `opioid_track/ml/risk_scorer.py` — risk scoring to expose
3. `opioid_track/ml/geographic_forecaster.py` — forecasts to expose
4. `opioid_track/core/supply_chain_monitor.py` — alerts to expose
5. `opioid_track/core/signal_detector.py` — signal detection to expose
6. `opioid_track/agents/opioid_watchdog.py` — intelligence queries to expose
7. `opioid_track/core/fhir_generator.py` — FHIR resources to expose

---

## Agent Assignment

### Agent A (Worktree: `fastapi`) — Create API Application + Models

**Create directory:** `opioid_track/api/` with `__init__.py`

**Create file: `opioid_track/api/models.py`**

```python
"""Pydantic response models for the TruPharma Opioid API."""
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

# --- Drug Models ---
class Ingredient(BaseModel):
    rxcui: str
    name: str
    is_opioid_component: bool

class DrugProfile(BaseModel):
    rxcui: str
    drug_name: str
    schedule: str
    opioid_category: str
    active_ingredients: List[Ingredient]
    atc_codes: List[str] = []
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None

class DrugSearchResult(BaseModel):
    results: List[DrugProfile]
    total: int
    query: str

# --- Risk Models ---
class RiskFactors(BaseModel):
    faers_signal_strength: float
    mme_factor: float
    inverse_therapeutic_index: float
    lethal_dose_proximity: float
    schedule_severity: float
    receptor_profile_penalty: float

class RiskAssessment(BaseModel):
    drug_name: str
    score: float = Field(ge=0, le=100)
    tier: str
    factors: RiskFactors
    factor_contributions: Dict[str, float]

# --- Signal Models ---
class SignalDetail(BaseModel):
    reaction: str
    prr: Optional[float] = None
    ror: Optional[float] = None
    ebgm: Optional[float] = None
    methods_flagged: int
    is_consensus: bool
    report_count: int

class DrugSignals(BaseModel):
    drug_name: str
    total_signals: int
    consensus_signals: int
    signals: List[SignalDetail]

# --- MME Models ---
class MMERequest(BaseModel):
    ingredient: str
    daily_dose_mg: float

class MMEResult(BaseModel):
    ingredient: str
    daily_dose_mg: float
    mme_factor: float
    daily_mme: float
    risk_level: str

# --- Geographic Models ---
class StateProfile(BaseModel):
    state: str
    risk_score: float
    death_rate: Optional[float] = None
    prescribing_rate: Optional[float] = None
    pills_per_capita: Optional[float] = None

class ForecastPoint(BaseModel):
    date: str
    predicted: float
    lower_80: float
    upper_80: float
    lower_95: float
    upper_95: float

class StateForecast(BaseModel):
    state: str
    trend: str
    trend_slope: float
    forecast: List[ForecastPoint]

# --- Supply Chain Models ---
class RecallAlert(BaseModel):
    recall_number: str
    product: str
    classification: str
    reason: str
    status: str
    date: str
    matched_opioid: str

class SupplyChainSummary(BaseModel):
    active_recalls: int
    active_shortages: int
    critically_vulnerable: int
    alerts: List[RecallAlert]

# --- Comparison Models ---
class DrugCompareRequest(BaseModel):
    drug1: str
    drug2: str

class DrugComparison(BaseModel):
    drug1: DrugProfile
    drug2: DrugProfile
    risk_comparison: Dict[str, float]
    mme_comparison: Dict[str, float]

# --- Watchdog Models ---
class WatchdogQuery(BaseModel):
    question: str

class WatchdogResponse(BaseModel):
    question: str
    answer: str
    sources: List[str] = []

# --- Alert Subscription ---
class AlertSubscription(BaseModel):
    webhook_url: str
    alert_types: List[str]  # ["new_signal", "fda_recall", "mortality_spike", "drug_shortage"]
    email: Optional[str] = None

class APIStatus(BaseModel):
    status: str = "healthy"
    version: str
    total_drugs: int
    total_signals: int
    last_updated: str
```

**Create file: `opioid_track/api/app.py`**

```python
"""
TruPharma Opioid Intelligence API.
FastAPI application with auto-generated Swagger documentation.
"""
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
import os

# API key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Validate API key. In demo mode, accept any key or no key."""
    valid_keys = os.environ.get("TRUPHARMA_API_KEYS", "demo-key-2024").split(",")
    if api_key and api_key in valid_keys:
        return api_key
    if os.environ.get("TRUPHARMA_API_DEMO_MODE", "true").lower() == "true":
        return "demo"
    raise HTTPException(status_code=403, detail="Invalid API key")

app = FastAPI(
    title="TruPharma Opioid Intelligence API",
    description="REST API for opioid pharmacovigilance, risk assessment, and clinical intelligence.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from opioid_track.api.routes import drugs, analytics, geographic, alerts

app.include_router(drugs.router, prefix="/api/v1", tags=["Drugs"])
app.include_router(analytics.router, prefix="/api/v1", tags=["Analytics"])
app.include_router(geographic.router, prefix="/api/v1", tags=["Geographic"])
app.include_router(alerts.router, prefix="/api/v1", tags=["Alerts"])

@app.get("/", tags=["Status"])
async def root():
    return {"message": "TruPharma Opioid Intelligence API", "docs": "/docs"}

@app.get("/api/v1/status", response_model=APIStatus, tags=["Status"])
async def status():
    """API health check and summary statistics."""
    ...
```

**Done criteria:** `app.py` imports without error. Pydantic models validate correctly.

---

### Agent B (Parallel with Agent A) — Create Route Modules

**Create file: `opioid_track/api/routes/__init__.py`**

**Create file: `opioid_track/api/routes/drugs.py`**

```python
"""Drug lookup, search, and risk assessment endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from opioid_track.api.models import DrugProfile, DrugSearchResult, DrugSignals, RiskAssessment, DrugCompareRequest, DrugComparison
from opioid_track.api.app import get_api_key

router = APIRouter()

@router.get("/drugs/{rxcui}", response_model=DrugProfile)
async def get_drug(rxcui: str, api_key: str = Depends(get_api_key)):
    """Get full opioid drug profile by RxCUI."""
    ...

@router.get("/drugs/search", response_model=DrugSearchResult)
async def search_drugs(q: str = Query(..., min_length=2), api_key: str = Depends(get_api_key)):
    """Free-text search for opioid drugs."""
    ...

@router.get("/drugs/{rxcui}/signals", response_model=DrugSignals)
async def get_drug_signals(rxcui: str, api_key: str = Depends(get_api_key)):
    """Get FAERS safety signals for a drug."""
    ...

@router.get("/drugs/{rxcui}/risk", response_model=RiskAssessment)
async def get_drug_risk(rxcui: str, api_key: str = Depends(get_api_key)):
    """Get Clinical Risk Index for a drug."""
    ...

@router.post("/drugs/compare", response_model=DrugComparison)
async def compare_drugs(request: DrugCompareRequest, api_key: str = Depends(get_api_key)):
    """Side-by-side drug comparison."""
    ...
```

**Create file: `opioid_track/api/routes/analytics.py`**

```python
"""Analytics endpoints: MME, FHIR, watchdog queries."""
from fastapi import APIRouter, Depends
from opioid_track.api.models import MMERequest, MMEResult, WatchdogQuery, WatchdogResponse
from opioid_track.api.app import get_api_key

router = APIRouter()

@router.post("/mme/calculate", response_model=MMEResult)
async def calculate_mme(request: MMERequest, api_key: str = Depends(get_api_key)):
    """Calculate Morphine Milligram Equivalent."""
    ...

@router.get("/fhir/risk-assessment/{rxcui}")
async def get_fhir_risk_assessment(rxcui: str, api_key: str = Depends(get_api_key)):
    """Generate FHIR R4 RiskAssessment resource."""
    ...

@router.post("/watchdog/query", response_model=WatchdogResponse)
async def watchdog_query(request: WatchdogQuery, api_key: str = Depends(get_api_key)):
    """Natural language intelligence query."""
    ...
```

**Create file: `opioid_track/api/routes/geographic.py`**

```python
"""Geographic intelligence endpoints."""
from fastapi import APIRouter, Depends, Query
from typing import List
from opioid_track.api.models import StateProfile, StateForecast
from opioid_track.api.app import get_api_key

router = APIRouter()

@router.get("/geographic/{state}", response_model=StateProfile)
async def get_state(state: str, api_key: str = Depends(get_api_key)):
    """Get state-level opioid risk profile."""
    ...

@router.get("/geographic", response_model=List[StateProfile])
async def list_states(api_key: str = Depends(get_api_key)):
    """List all state profiles ranked by risk."""
    ...

@router.get("/geographic/forecast/{state}", response_model=StateForecast)
async def get_forecast(state: str, horizon_months: int = Query(12, ge=6, le=24), api_key: str = Depends(get_api_key)):
    """Get overdose rate forecast for a state."""
    ...
```

**Create file: `opioid_track/api/routes/alerts.py`**

```python
"""Supply chain alerts and notification endpoints."""
from fastapi import APIRouter, Depends
from opioid_track.api.models import SupplyChainSummary, AlertSubscription, RecallAlert
from opioid_track.api.app import get_api_key
from typing import List

router = APIRouter()

@router.get("/supply-chain/alerts", response_model=SupplyChainSummary)
async def get_supply_chain_alerts(api_key: str = Depends(get_api_key)):
    """Get active FDA recalls and drug shortages for opioids."""
    ...

@router.get("/supply-chain/recalls", response_model=List[RecallAlert])
async def get_recalls(classification: str = None, api_key: str = Depends(get_api_key)):
    """Get detailed recall list, optionally filtered by classification."""
    ...

@router.post("/alerts/subscribe")
async def subscribe_alerts(subscription: AlertSubscription, api_key: str = Depends(get_api_key)):
    """Subscribe to real-time alert notifications via webhook."""
    ...
```

**Done criteria:** All route files import without error. Endpoint signatures match Pydantic models.

---

### Agent C (Sequential after A+B) — Tests and Startup

**Create file: `opioid_track/tests/test_api.py`**

```python
"""API endpoint integration tests using FastAPI TestClient."""
import pytest
from fastapi.testclient import TestClient
from opioid_track.api.app import app

client = TestClient(app)

class TestAPIStatus:
    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "TruPharma" in r.json()["message"]

    def test_status(self):
        r = client.get("/api/v1/status")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

class TestDrugEndpoints:
    def test_search_drugs(self):
        r = client.get("/api/v1/drugs/search?q=morphine")
        assert r.status_code == 200
        assert r.json()["total"] > 0

    def test_get_drug_by_rxcui(self):
        r = client.get("/api/v1/drugs/7052")
        assert r.status_code == 200
        assert "morphine" in r.json()["drug_name"].lower()

    def test_get_drug_risk(self):
        r = client.get("/api/v1/drugs/7052/risk")
        assert r.status_code == 200
        assert 0 <= r.json()["score"] <= 100

class TestAnalyticsEndpoints:
    def test_mme_calculation(self):
        r = client.post("/api/v1/mme/calculate", json={"ingredient": "morphine", "daily_dose_mg": 60})
        assert r.status_code == 200
        assert r.json()["daily_mme"] == 60.0  # morphine factor is 1.0

    def test_fhir_risk_assessment(self):
        r = client.get("/api/v1/fhir/risk-assessment/7052")
        assert r.status_code == 200
        assert r.json()["resourceType"] == "RiskAssessment"

class TestGeographicEndpoints:
    def test_list_states(self):
        r = client.get("/api/v1/geographic")
        assert r.status_code == 200
        assert len(r.json()) > 0

class TestSupplyChainEndpoints:
    def test_alerts(self):
        r = client.get("/api/v1/supply-chain/alerts")
        assert r.status_code == 200
```

**Add to requirements:**
```
fastapi>=0.104.0
uvicorn>=0.24.0
```

**Done criteria:** `pytest opioid_track/tests/test_api.py -v` passes. `uvicorn opioid_track.api.app:app --port 8000` starts and `/docs` shows Swagger UI.

---

## Execution Order
1. **Agent A** creates `app.py` + `models.py` (worktree)
2. **Agent B** creates all route files (parallel with A)
3. **Agent C** creates tests, verifies everything (sequential)
4. Commit: `git commit -m "feat(opioid): add FastAPI REST API with Swagger docs"`

## Checkpoint Protocol
- **Mid-Agent B:** Note which route files are done
- **Mid-Agent C:** Note which test classes pass

## Final Verification
```bash
pytest opioid_track/tests/test_api.py -v
uvicorn opioid_track.api.app:app --port 8000 &
curl http://localhost:8000/docs  # Swagger UI
curl http://localhost:8000/api/v1/status  # Health check
```
Update `00_STATUS.md` to "COMPLETED".
