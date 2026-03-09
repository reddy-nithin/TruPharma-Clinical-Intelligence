# Sub-Plan 12: Platform Overview Page

## Priority: Near-last (all features should be done for live metrics)
## Depends on: All Sub-Plans 01-11

---

## Goal
Create a "Platform Overview" page (reframed from "Business Pitch") that showcases platform capabilities, architecture, market context, and integration readiness. Product-led framing — not a sales deck. Pulls live metrics from actual data for credibility.

## Pre-Requisites
- All Sub-Plans 01-11 should be COMPLETED (for accurate capability showcase)
- Read `00_STATUS.md` first

## Context Files to Read First
1. `opioid_track/dashboard/opioid_app.py` — navigation structure
2. `opioid_track/core/registry.py` — for live drug count metrics
3. `opioid_track/config.py` — for data source listing
4. `opioid_track/ml/risk_scorer.py` — for ML capability metrics
5. `opioid_track/api/app.py` — for API endpoint listing

---

## Agent Assignment

### Single Agent — Create Platform Overview Page

**Create file: `opioid_track/dashboard/pages/platform_overview.py`**

This is a single-page creation task. No parallelization needed.

```python
"""
Platform Overview — showcases TruPharma Opioid Track capabilities.
Product-led framing: "Here's what this platform can do."
Pulls live metrics from actual data for credibility.
"""
import streamlit as st
import json
from pathlib import Path

def render_platform_overview():
    """Main page render function."""

    st.markdown("# Platform Overview")
    st.markdown("##### TruPharma Clinical Intelligence — Opioid Safety Monitoring")

    # ============================================
    # Section 1: Live Platform Metrics
    # ============================================
    st.markdown("### Platform at a Glance")
    # Pull REAL metrics from data files
    # Count actual drugs, signals, counties, etc.
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        # registry.list_all_opioid_rxcuis() count
        st.metric("Drugs Tracked", "85+")
    with col2:
        # len(registry.list_all_opioid_ndcs())
        st.metric("NDC Codes", "12K+")
    with col3:
        # signal results count
        st.metric("Safety Signals", "200+")
    with col4:
        # geographic profiles count
        st.metric("Counties Profiled", "3,148")
    with col5:
        # API endpoint count
        st.metric("API Endpoints", "15+")

    st.markdown("---")

    # ============================================
    # Section 2: Capabilities Grid
    # ============================================
    st.markdown("### Intelligence Modules")

    capabilities = [
        {
            "icon": "💊",
            "name": "Drug Registry",
            "description": "Comprehensive opioid database with RxCUI, NDC, ATC classification, "
                          "DEA scheduling, and active ingredient profiling.",
            "data_sources": "RxNav, RxClass, OpenFDA, Historical NDC (JAMIA 2020)",
            "key_feature": "Real-time NDC synchronization",
        },
        {
            "icon": "⚠️",
            "name": "Signal Detection",
            "description": "Multi-method pharmacovigilance using PRR, ROR, and MGPS/EBGM "
                          "with consensus-based signal confirmation.",
            "data_sources": "FDA FAERS (OpenFDA API)",
            "key_feature": "3-method consensus signals",
        },
        {
            "icon": "🧪",
            "name": "Pharmacology Engine",
            "description": "Receptor binding profiles, potency rankings, therapeutic indices, "
                          "and lethal dose estimation from primary literature sources.",
            "data_sources": "ChemBL, GtoPdb, PubChem",
            "key_feature": "Danger classification system",
        },
        {
            "icon": "📊",
            "name": "Risk Scoring (ML)",
            "description": "Transparent 0-100 Clinical Risk Index with explainable factor "
                          "contributions and ML-calibrated weights.",
            "data_sources": "FAERS, CDC, Pharmacology data",
            "key_feature": "Waterfall explainability chart",
        },
        {
            "icon": "🗺️",
            "name": "Geographic Intelligence",
            "description": "County-level risk scoring combining prescribing rates, mortality, "
                          "and supply chain data. 3D DeckGL visualization.",
            "data_sources": "CDC WONDER, CMS, Medicaid, Census",
            "key_feature": "Prophet-based overdose forecasting",
        },
        {
            "icon": "🔗",
            "name": "NLP Label Mining",
            "description": "Automated extraction of safety signals from FDA structured product "
                          "labels using negation-aware NLP.",
            "data_sources": "DailyMed SPL (XML)",
            "key_feature": "Negex-based annotation",
        },
        {
            "icon": "📦",
            "name": "Supply Chain Monitor",
            "description": "Real-time FDA recall tracking, drug shortage monitoring, and "
                          "supply vulnerability scoring.",
            "data_sources": "FDA Enforcement API, CDER Shortages",
            "key_feature": "Vulnerability composite score",
        },
        {
            "icon": "🔔",
            "name": "Alert Engine",
            "description": "Push notifications for new safety signals, FDA recalls, "
                          "mortality spikes, and drug shortages.",
            "data_sources": "All monitored sources",
            "key_feature": "Webhook-based delivery",
        },
    ]

    # Render as a 2-column grid of cards
    for i in range(0, len(capabilities), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j < len(capabilities):
                cap = capabilities[i + j]
                with col:
                    st.markdown(f"""
                    <div style="background: var(--bg-secondary); border: 1px solid var(--border-primary);
                                border-radius: 8px; padding: 16px; margin-bottom: 12px; min-height: 180px;">
                        <h4 style="margin: 0 0 8px 0;">{cap['icon']} {cap['name']}</h4>
                        <p style="color: var(--text-secondary); font-size: 0.9em; margin-bottom: 8px;">
                            {cap['description']}</p>
                        <p style="font-size: 0.8em; color: var(--text-tertiary);">
                            <b>Sources:</b> {cap['data_sources']}</p>
                        <p style="font-size: 0.8em;">
                            <span style="background: var(--accent-teal-bg); color: var(--accent-teal);
                                         padding: 2px 8px; border-radius: 4px;">
                                {cap['key_feature']}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================
    # Section 3: Architecture Diagram
    # ============================================
    st.markdown("### Data Pipeline Architecture")
    st.markdown("""
    ```
    ┌──────────────────────────────────────────────────────────────────┐
    │                        DATA SOURCES                              │
    │  RxNav │ OpenFDA │ ChemBL │ CDC │ CMS │ DailyMed │ PubChem     │
    └───────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │                     INGESTION PIPELINE                           │
    │  RxClass Fetcher │ NDC Classifier │ FAERS Filter │ CDC Fetcher  │
    │  Pharmacology Fetcher │ Toxicology Fetcher │ CMS Fetcher        │
    └───────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │                   INTELLIGENCE ENGINE                            │
    │  Registry │ Signal Detector │ Risk Scorer │ NLP Miner           │
    │  Geographic Joiner │ Supply Chain Monitor │ Alert Engine         │
    │  Knowledge Indexer │ Forecaster │ Alternative Finder             │
    └───────────┬───────────────────────────────────┬──────────────────┘
                │                                   │
                ▼                                   ▼
    ┌───────────────────────┐           ┌───────────────────────────┐
    │   STREAMLIT DASHBOARD │           │      REST API (FastAPI)   │
    │   8 Interactive Pages │           │   15+ Endpoints + Swagger │
    │   3 View Modes        │           │   FHIR R4 Resources       │
    │   Light/Dark Theme    │           │   Webhook Alerts          │
    └───────────────────────┘           └───────────────────────────┘
    ```
    """)

    st.markdown("---")

    # ============================================
    # Section 4: Market Context
    # ============================================
    st.markdown("### Market Context")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### The Opioid Crisis by Numbers")
        st.markdown("""
        - **80,000+** opioid-involved overdose deaths annually in the US
        - **$1.5 trillion** estimated economic burden (2020)
        - **21-29%** of patients prescribed opioids misuse them
        - **8-12%** develop an opioid use disorder
        """)

    with col2:
        st.markdown("#### Pharmacovigilance Market")
        st.markdown("""
        - **$8.5B** global market (2024), growing at **12% CAGR**
        - **FDA mandate** for post-market surveillance
        - **AI/ML adoption** accelerating signal detection
        - **Real-time monitoring** replacing periodic review
        """)

    # TAM/SAM/SOM chart (Plotly concentric donuts)
    # Build with real market sizing data
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Pie(
        values=[8500, 2400, 480],
        labels=["TAM: Global Pharmacovigilance ($8.5B)",
                "SAM: US Opioid Safety ($2.4B)",
                "SOM: Clinical Intelligence Platforms ($480M)"],
        hole=0.4,
        marker_colors=["#1e2a3a", "#00b89e", "#00e5c8"],
        textfont=dict(color="#e8edf5"),
    ))
    fig.update_layout(
        title="Market Opportunity",
        paper_bgcolor="var(--chart-bg)",
        plot_bgcolor="var(--chart-plot-bg)",
        font=dict(color="#8892a4"),
        showlegend=True,
        legend=dict(font=dict(size=10)),
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ============================================
    # Section 5: Customer Personas
    # ============================================
    st.markdown("### Who Benefits")

    personas = [
        ("🏥", "Hospital Systems", "Real-time opioid safety monitoring for formulary management and prescribing oversight."),
        ("🛡️", "Health Plans / PBMs", "Prior authorization intelligence and opioid utilization management."),
        ("🏛️", "Public Health Agencies", "Geographic hotspot detection and overdose forecasting for resource allocation."),
        ("💊", "Pharma Safety Teams", "Automated FAERS signal detection and label change monitoring."),
        ("🔬", "Clinical Researchers", "Comprehensive opioid pharmacology data and risk analysis tools."),
    ]

    cols = st.columns(len(personas))
    for col, (icon, name, desc) in zip(cols, personas):
        with col:
            st.markdown(f"""
            <div style="text-align: center; padding: 12px; background: var(--bg-secondary);
                        border-radius: 8px; border: 1px solid var(--border-primary); min-height: 150px;">
                <div style="font-size: 2em;">{icon}</div>
                <h5 style="margin: 8px 0 4px 0;">{name}</h5>
                <p style="font-size: 0.8em; color: var(--text-secondary);">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ============================================
    # Section 6: Integration Readiness
    # ============================================
    st.markdown("### Integration Ready")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **REST API**
        - 15+ endpoints
        - Auto-generated Swagger docs
        - API key authentication
        - JSON responses
        """)
    with col2:
        st.markdown("""
        **FHIR R4 Compatible**
        - RiskAssessment resources
        - DetectedIssue resources
        - Valid, downloadable JSON
        - EMR integration ready
        """)
    with col3:
        st.markdown("""
        **Export Formats**
        - PDF risk reports
        - CSV data downloads
        - FHIR JSON resources
        - Webhook notifications
        """)

    st.markdown("---")

    # ============================================
    # Section 7: Contact / Demo Request
    # ============================================
    st.markdown("### Request a Demo")
    with st.form("demo_request"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            org = st.text_input("Organization")
        with col2:
            email = st.text_input("Email")
            use_case = st.selectbox("Primary Use Case", [
                "Formulary Management",
                "Pharmacovigilance",
                "Public Health",
                "Research",
                "Other",
            ])
        notes = st.text_area("Additional Notes", height=80)
        submitted = st.form_submit_button("Submit Request", use_container_width=True)
        if submitted:
            # Store locally (JSON file)
            demo_requests_path = Path(__file__).parent.parent / "data" / "demo_requests.json"
            try:
                existing = json.loads(demo_requests_path.read_text()) if demo_requests_path.exists() else []
            except Exception:
                existing = []
            existing.append({
                "name": name, "org": org, "email": email,
                "use_case": use_case, "notes": notes,
                "submitted_at": datetime.now().isoformat(),
            })
            demo_requests_path.write_text(json.dumps(existing, indent=2))
            st.success("Thank you! We'll be in touch shortly.")
```

**Modify: `opioid_track/dashboard/opioid_app.py`**
- Add "Platform Overview" to sidebar navigation (last item, or first item for demo flow)
- Add page dispatch

**Done criteria:** Platform Overview page loads with all 7 sections. Live metrics pulled from actual data. Contact form stores submissions. TAM/SAM/SOM chart renders.

---

## Execution Order
1. Single agent creates the page file
2. Modify `opioid_app.py` navigation
3. Visual verification: all sections render, form works
4. Commit: `git commit -m "feat(opioid): add Platform Overview page with live metrics and market context"`

## Checkpoint Protocol
- Note which sections are done (metrics? capabilities? architecture? market? personas? integration? form?)

## Final Verification
```bash
# Visual: Platform Overview page renders all 7 sections
# Live metrics show real counts from data files
# Contact form submits and stores data
# TAM/SAM/SOM chart renders correctly
```
Update `00_STATUS.md` to "COMPLETED".
