# Sub-Plan 11: Real-Time Alert Engine

## Priority: After Sub-Plans 01, 05 (needs caching + supply chain)
## Depends on: Sub-Plan 01 (Cache for SQLite storage), Sub-Plan 05 (Supply Chain Monitor)

---

## Goal
Build a push notification system that detects new FAERS signals, FDA recalls, mortality spikes, and drug shortages. Displayed via a sidebar notification bell in the dashboard and exposed via webhook in the API.

## Pre-Requisites
- Sub-Plan 01 (Caching) and Sub-Plan 05 (Supply Chain) COMPLETED
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/core/cache.py` — SQLite backend for alert storage
2. `opioid_track/core/supply_chain_monitor.py` — recall/shortage detection
3. `opioid_track/core/signal_detector.py` — FAERS signal detection
4. `opioid_track/ml/geographic_forecaster.py` — mortality predictions (if Sub-Plan 04 done)
5. `opioid_track/dashboard/opioid_app.py` — sidebar structure for bell placement

---

## Agent Assignment

### Agent A (Worktree: `alert-engine`) — Create Alert Engine

**Create file: `opioid_track/core/alert_engine.py`**

```python
"""
Real-time alert engine for opioid safety monitoring.
Detects new signals, recalls, spikes, and shortages.
Stores alerts in SQLite for persistence across sessions.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AlertType(Enum):
    NEW_SIGNAL = "new_signal"
    FDA_RECALL = "fda_recall"
    MORTALITY_SPIKE = "mortality_spike"
    DRUG_SHORTAGE = "drug_shortage"

class AlertSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class Alert:
    id: str
    type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    drug_name: Optional[str]
    created_at: str           # ISO 8601
    read: bool = False
    data: Optional[Dict] = None  # Additional structured data

class AlertEngine:
    """
    Monitors data sources for new alertable events.
    Stores alerts in SQLite table within the cache DB.

    Alert detection logic:
    1. NEW_SIGNAL: Compare current FAERS signals against last-known signals.
       If a new consensus signal appears, create alert.
    2. FDA_RECALL: Compare current FDA recalls against stored recall IDs.
       If a new recall appears for an opioid, create alert.
    3. MORTALITY_SPIKE: Compare actual mortality vs forecast.
       If actual > forecast + 2σ, create alert.
    4. DRUG_SHORTAGE: Compare current shortage status against stored status.
       If a drug enters shortage, create alert.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize with SQLite DB (reuse cache DB)."""
        ...

    def _create_tables(self):
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            drug_name TEXT,
            created_at TEXT NOT NULL,
            read INTEGER DEFAULT 0,
            data TEXT
        );
        CREATE TABLE IF NOT EXISTS alert_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
        ...

    def check_for_new_signals(self) -> List[Alert]:
        """
        Compare current FAERS signals against stored state.
        Returns list of new alerts (if any).

        Process:
        1. Load last-known signal set from alert_state table
        2. Run signal detection (or load cached signals)
        3. Compare: new consensus signals not in last-known set
        4. Create alerts for new signals
        5. Update alert_state with current signal set
        """
        ...

    def check_for_recalls(self) -> List[Alert]:
        """
        Check FDA enforcement API for new opioid recalls.

        Process:
        1. Load last-known recall IDs from alert_state
        2. Fetch current recalls from SupplyChainMonitor
        3. Compare: new recall numbers not in last-known set
        4. Create alerts for new recalls
        5. Severity: Class I = CRITICAL, Class II = HIGH, Class III = MEDIUM
        """
        ...

    def check_for_mortality_spikes(self) -> List[Alert]:
        """
        Compare actual mortality data vs forecasts.
        Only runs if GeographicForecaster is available.

        Process:
        1. Get latest actual mortality data
        2. Get forecast for same period
        3. If actual > upper_95 prediction interval → CRITICAL
        4. If actual > upper_80 prediction interval → HIGH
        """
        ...

    def check_for_shortages(self) -> List[Alert]:
        """
        Check for new drug shortages.

        Process:
        1. Load last-known shortage status from alert_state
        2. Fetch current shortages from SupplyChainMonitor
        3. Compare: drugs that newly entered shortage
        4. Create alerts
        """
        ...

    def check_all(self) -> List[Alert]:
        """Run all checks and return new alerts."""
        new_alerts = []
        new_alerts.extend(self.check_for_new_signals())
        new_alerts.extend(self.check_for_recalls())
        new_alerts.extend(self.check_for_mortality_spikes())
        new_alerts.extend(self.check_for_shortages())

        # Persist new alerts
        for alert in new_alerts:
            self._save_alert(alert)

        return new_alerts

    def get_unread_alerts(self) -> List[Alert]:
        """Get all unread alerts, most recent first."""
        ...

    def get_all_alerts(self, limit: int = 50) -> List[Alert]:
        """Get all alerts (read and unread), most recent first."""
        ...

    def get_unread_count(self) -> int:
        """Count of unread alerts."""
        ...

    def mark_read(self, alert_id: str) -> None:
        """Mark a single alert as read."""
        ...

    def mark_all_read(self) -> None:
        """Mark all alerts as read."""
        ...

    def _save_alert(self, alert: Alert) -> None:
        """Persist alert to SQLite."""
        ...

    def _load_alert(self, row: tuple) -> Alert:
        """Convert SQLite row to Alert dataclass."""
        ...

    def _get_state(self, key: str) -> Optional[str]:
        """Get last-known state for comparison."""
        ...

    def _set_state(self, key: str, value: str) -> None:
        """Update state for next comparison."""
        ...
```

**Done criteria:** Module imports. Alert creation and persistence works.

---

### Agent B (Sequential after A) — Create Sidebar Bell Component

**Create file: `opioid_track/dashboard/components/alert_bell.py`**

```python
"""
Sidebar notification bell for real-time alerts.
Shows unread count badge and expandable alert list.
"""
import streamlit as st
from opioid_track.core.alert_engine import AlertEngine, AlertType, AlertSeverity

# Severity colors
SEVERITY_COLORS = {
    "critical": "#ef4444",
    "high": "#f59e0b",
    "medium": "#3b82f6",
    "low": "#22c55e",
}

# Type icons (Unicode)
TYPE_ICONS = {
    "new_signal": "⚠",
    "fda_recall": "🔄",
    "mortality_spike": "📈",
    "drug_shortage": "📦",
}


def render_alert_bell():
    """
    Render notification bell in the sidebar.
    Shows unread count. Clicking expands to show alert list.

    Call this at the top of the sidebar.
    """
    engine = AlertEngine()

    # Check for new alerts (lightweight — uses cached state)
    # Only run full check periodically (every 5 minutes in session)
    last_check = st.session_state.get("last_alert_check", 0)
    import time
    if time.time() - last_check > 300:  # 5 minutes
        engine.check_all()
        st.session_state.last_alert_check = time.time()

    unread_count = engine.get_unread_count()

    # Bell with badge
    bell_html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between;
                padding: 8px 12px; margin-bottom: 8px;
                background: var(--bg-tertiary); border-radius: 6px;
                border: 1px solid var(--border-primary);">
        <span style="font-size: 1.1em;">🔔 Alerts</span>
        {"<span style='background: #ef4444; color: white; border-radius: 50%; "
         "padding: 2px 8px; font-size: 0.8em; font-weight: bold;'>"
         f"{unread_count}</span>" if unread_count > 0 else
         "<span style='color: var(--text-tertiary);'>None</span>"}
    </div>
    """
    st.sidebar.markdown(bell_html, unsafe_allow_html=True)

    # Expandable alert list
    if unread_count > 0:
        with st.sidebar.expander(f"View {unread_count} alert{'s' if unread_count != 1 else ''}", expanded=False):
            alerts = engine.get_unread_alerts()
            for alert in alerts[:10]:
                icon = TYPE_ICONS.get(alert.type.value, "ℹ")
                color = SEVERITY_COLORS.get(alert.severity.value, "#8892a4")
                st.markdown(
                    f"<div style='border-left: 3px solid {color}; padding: 4px 8px; "
                    f"margin: 4px 0; font-size: 0.85em;'>"
                    f"{icon} <b>{alert.title}</b><br/>"
                    f"<span style='color: var(--text-secondary);'>{alert.description[:80]}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            if st.button("Mark all as read", key="mark_all_read"):
                engine.mark_all_read()
                st.rerun()
```

**Done criteria:** Bell renders in sidebar with unread count. Alert list expandable.

---

### Agent C (Sequential after B) — Integrate into App

**Modify: `opioid_track/dashboard/opioid_app.py`**
1. Import `render_alert_bell` from `alert_bell` component
2. Call `render_alert_bell()` at the top of the sidebar section (after theme toggle and view mode, before navigation)

**Modify: `opioid_track/api/routes/alerts.py`** (if Sub-Plan 10 is done)
- Wire up the `subscribe_alerts` endpoint to store webhook URLs in the alert DB
- Add endpoint to list recent alerts via API

**Done criteria:** App sidebar shows alert bell. New alerts appear when data changes.

---

## Execution Order
1. **Agent A** creates alert engine (worktree)
2. **Agent B** creates sidebar bell component (sequential)
3. **Agent C** integrates into app (sequential)
4. Commit: `git commit -m "feat(opioid): add real-time alert engine with sidebar notification bell"`

## Checkpoint Protocol
- **Mid-Agent A:** Note which check methods are done
- **Mid-Agent B:** Note if bell rendering is done

## Final Verification
```bash
# Visual: Sidebar shows bell icon with count
# Expanding shows alert details
# "Mark all as read" clears the count
```
Update `00_STATUS.md` to "COMPLETED".
