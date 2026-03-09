# Sub-Plan 07: Dynamic Knowledge Graph

## Priority: Early (no dependencies)
## Can parallelize with: Sub-Plan 01, 02, 06

---

## Goal
Build an interactive, force-directed network graph showing drug → reactions, mechanisms, signals, and related drug relationships. Uses `streamlit-agraph` (vis.js wrapper). Integrates into Drug Explorer and Signal Detection pages.

## Pre-Requisites
- Read `00_STATUS.md` first
- No hard dependencies, but benefits from existing NLP insights and signal data

## Context Files to Read First
1. `opioid_track/dashboard/pages/drug_explorer.py` — where graph will be embedded
2. `opioid_track/dashboard/pages/signals.py` — alternate view as graph
3. `opioid_track/core/nlp_miner.py` — NLP insights data structure (warnings, reactions)
4. `opioid_track/data/faers_signal_results.json` — signal data structure
5. `opioid_track/data/opioid_pharmacology.json` — pharmacology data (receptor profiles, mechanisms)
6. `opioid_track/agents/opioid_watchdog.py` — `rank_ingredient_sensitivity()` for data access patterns

---

## Agent Assignment

### Agent A (Worktree: `knowledge-graph`) — Create Network Graph Component

**Create file: `opioid_track/dashboard/components/network_graph.py`**

```python
"""
Dynamic Knowledge Graph using streamlit-agraph (vis.js wrapper).
Renders force-directed network of drug relationships, signals, and mechanisms.
"""
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from streamlit_agraph import agraph, Node, Edge, Config

# Node type configurations
NODE_TYPES = {
    "drug": {
        "color": "#00e5c8",       # Teal (brand accent)
        "size": 40,               # Largest — central node
        "shape": "dot",
        "font_color": "#e8edf5",
    },
    "mechanism": {
        "color": "#a855f7",       # Purple
        "size": 25,
        "shape": "dot",
        "font_color": "#e8edf5",
    },
    "warning": {
        "color": "#f59e0b",       # Amber
        "size": 20,
        "shape": "triangle",
        "font_color": "#e8edf5",
    },
    "signal": {
        "color": "#ef4444",       # Red (intensity varies)
        "size": 22,
        "shape": "diamond",
        "font_color": "#e8edf5",
    },
    "related_drug": {
        "color": "#5a6478",       # Gray
        "size": 18,
        "shape": "dot",
        "font_color": "#8892a4",
    },
    "category": {
        "color": "#3b82f6",       # Blue
        "size": 15,
        "shape": "square",
        "font_color": "#e8edf5",
    },
}


def _create_node(node_id: str, label: str, node_type: str, title: str = "", **kwargs) -> Node:
    """
    Create a styled Node based on type.

    Parameters:
    - node_id: unique identifier
    - label: display text
    - node_type: one of NODE_TYPES keys
    - title: hover tooltip text
    """
    style = NODE_TYPES.get(node_type, NODE_TYPES["related_drug"])
    return Node(
        id=node_id,
        label=label,
        size=kwargs.get("size", style["size"]),
        color=kwargs.get("color", style["color"]),
        shape=style["shape"],
        font={"color": style["font_color"], "size": 12},
        title=title or label,
        **{k: v for k, v in kwargs.items() if k not in ("size", "color")},
    )


def _create_edge(source: str, target: str, label: str = "", width: float = 1.0, color: str = "#1e2a3a") -> Edge:
    """Create a styled Edge."""
    return Edge(
        source=source,
        target=target,
        label=label,
        width=width,
        color=color,
        font={"color": "#5a6478", "size": 10},
    )


def build_knowledge_graph(
    drug_name: str,
    drug_rxcui: str,
    nlp_insights: Optional[Dict] = None,
    signal_data: Optional[List[Dict]] = None,
    pharmacology_data: Optional[Dict] = None,
    related_drugs: Optional[List[Dict]] = None,
) -> tuple:
    """
    Build nodes and edges for a drug's knowledge graph.

    Returns (nodes: List[Node], edges: List[Edge])

    Node construction:
    1. Central drug node (drug_name)
    2. Mechanism nodes from pharmacology_data:
       - Receptor targets (e.g., "μ-Opioid Receptor Agonist")
       - Mechanism of action
    3. Warning nodes from nlp_insights:
       - Boxed warnings from FDA labels
       - Key adverse reactions
       - Contraindications
    4. Signal nodes from signal_data:
       - FAERS consensus signals
       - Node size/color intensity proportional to signal strength
    5. Related drug nodes:
       - Other opioids in same category
       - Edge label shows relationship (e.g., "same category", "similar potency")
    """
    nodes = []
    edges = []

    # 1. Central drug node
    central = _create_node(
        node_id=f"drug_{drug_rxcui}",
        label=drug_name,
        node_type="drug",
        title=f"{drug_name} (RxCUI: {drug_rxcui})",
    )
    nodes.append(central)

    # 2. Mechanism nodes (from pharmacology)
    if pharmacology_data:
        # Extract receptor profile
        receptor_profile = pharmacology_data.get("receptor_profile", {})
        for receptor, activity in receptor_profile.items():
            mech_id = f"mech_{receptor}"
            mech_label = f"{receptor}\n({activity})"
            nodes.append(_create_node(mech_id, mech_label, "mechanism",
                         title=f"Receptor: {receptor}, Activity: {activity}"))
            edges.append(_create_edge(central.id, mech_id, label="targets", width=2.0, color="#a855f7"))

        # Mechanism of action
        moa = pharmacology_data.get("mechanism_of_action", "")
        if moa:
            moa_id = "mech_moa"
            nodes.append(_create_node(moa_id, "Mechanism", "mechanism", title=moa))
            edges.append(_create_edge(central.id, moa_id, label="mechanism", width=1.5, color="#a855f7"))

    # 3. Warning nodes (from NLP insights)
    if nlp_insights:
        warnings = nlp_insights.get("boxed_warnings", [])
        for i, warning in enumerate(warnings[:5]):  # Cap at 5
            warn_id = f"warn_{i}"
            # Truncate long warning text for label
            label = warning[:30] + "..." if len(warning) > 30 else warning
            nodes.append(_create_node(warn_id, label, "warning", title=warning))
            edges.append(_create_edge(central.id, warn_id, label="⚠ warning", width=1.5, color="#f59e0b"))

        adverse = nlp_insights.get("adverse_reactions", [])
        for i, reaction in enumerate(adverse[:8]):  # Cap at 8
            ar_id = f"adverse_{i}"
            nodes.append(_create_node(ar_id, reaction, "warning",
                         title=f"Adverse Reaction: {reaction}", size=16))
            edges.append(_create_edge(central.id, ar_id, label="adverse", width=1.0, color="#f59e0b"))

    # 4. Signal nodes (from FAERS)
    if signal_data:
        for i, signal in enumerate(signal_data[:10]):  # Cap at 10
            reaction = signal.get("reaction", signal.get("term", f"Signal {i}"))
            methods = signal.get("methods_flagged", 1)
            signal_id = f"signal_{i}"
            # Intensity based on number of methods agreeing
            intensity = min(methods / 3.0, 1.0)
            red_value = int(180 + intensity * 75)
            signal_color = f"#{red_value:02x}{int(68 * (1 - intensity)):02x}{int(68 * (1 - intensity)):02x}"

            nodes.append(_create_node(
                signal_id, reaction, "signal",
                title=f"FAERS Signal: {reaction} ({methods} methods)",
                size=int(18 + intensity * 12),
                color=signal_color,
            ))
            edges.append(_create_edge(central.id, signal_id, label="signal",
                         width=1 + intensity * 2, color=signal_color))

    # 5. Related drug nodes
    if related_drugs:
        for i, rd in enumerate(related_drugs[:6]):  # Cap at 6
            rd_name = rd.get("drug_name", f"Drug {i}")
            rd_rxcui = rd.get("rxcui", "")
            relationship = rd.get("relationship", "same category")
            rd_id = f"related_{rd_rxcui or i}"
            nodes.append(_create_node(rd_id, rd_name, "related_drug",
                         title=f"{rd_name} ({relationship})"))
            edges.append(_create_edge(central.id, rd_id, label=relationship,
                         width=0.8, color="#5a6478"))

    return nodes, edges


def render_knowledge_graph(
    drug_name: str,
    drug_rxcui: str,
    nlp_insights: Optional[Dict] = None,
    signal_data: Optional[List[Dict]] = None,
    pharmacology_data: Optional[Dict] = None,
    related_drugs: Optional[List[Dict]] = None,
    height: int = 500,
) -> None:
    """
    Render the full knowledge graph in Streamlit.

    Calls build_knowledge_graph() then agraph() with physics configuration.
    """
    nodes, edges = build_knowledge_graph(
        drug_name, drug_rxcui, nlp_insights, signal_data, pharmacology_data, related_drugs
    )

    if not nodes:
        st.info("No data available to build knowledge graph.")
        return

    config = Config(
        width="100%",
        height=height,
        directed=False,
        physics={
            "enabled": True,
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.005,
                "springLength": 150,
                "springConstant": 0.08,
                "damping": 0.4,
            },
            "solver": "forceAtlas2Based",
            "stabilization": {
                "enabled": True,
                "iterations": 100,
            },
        },
        nodeHighlightBehavior=True,
        highlightColor="#00e5c8",
        collapsible=False,
    )

    # Dark background for the graph canvas
    # Note: streamlit-agraph might need CSS injection for dark bg
    agraph(nodes=nodes, edges=edges, config=config)
```

**Done criteria:** Module imports. `build_knowledge_graph()` returns nodes and edges. `render_knowledge_graph()` callable.

---

### Agent B (Sequential after A) — Integrate into Dashboard Pages

**Modify: `opioid_track/dashboard/pages/drug_explorer.py`**

1. Import `render_knowledge_graph` from the component
2. After the drug identity card + sensitivity analysis section, add:
   ```python
   st.markdown("### Knowledge Graph")
   st.caption("Interactive network showing drug relationships, mechanisms, warnings, and safety signals. Drag nodes to explore.")
   ```
3. Gather data for the graph:
   - `nlp_insights`: from `opioid_watchdog.get_label_insights(drug_name)`
   - `signal_data`: from `opioid_watchdog.get_safety_signals(drug_name)`
   - `pharmacology_data`: from `opioid_watchdog.get_pharmacology(ingredient_name)`
   - `related_drugs`: from registry, get other drugs in same category
4. Call `render_knowledge_graph(drug_name, rxcui, nlp_insights, signal_data, pharmacology_data, related_drugs)`

**Modify: `opioid_track/dashboard/pages/signals.py`**

1. Add a view toggle at the top: `view = st.radio("View", ["Heatmap", "Knowledge Graph"], horizontal=True)`
2. If "Knowledge Graph" selected:
   - Let user select a drug from dropdown
   - Render knowledge graph focused on that drug's signals
3. If "Heatmap" selected:
   - Render existing heatmap (no changes)

**Add to requirements:** `streamlit-agraph>=0.0.45`

**Done criteria:** Knowledge graph renders in Drug Explorer with real data. Signals page has graph/heatmap toggle.

---

## Execution Order
1. **Agent A** creates network graph component (worktree)
2. **Agent B** integrates into Drug Explorer + Signals pages (sequential)
3. Visual verification: graph renders, nodes are draggable, physics stabilizes
4. Commit: `git commit -m "feat(opioid): add dynamic knowledge graph with force-directed physics"`

## Checkpoint Protocol
- **Mid-Agent A:** Note which node types and edge creation are done
- **Mid-Agent B:** Note which page integrations are done

## Final Verification
```bash
# Visual: Drug Explorer → select a drug → knowledge graph renders below
# Nodes are color-coded by type, draggable, physics-based
# Signals page → toggle to graph view → renders correctly
```
Update `00_STATUS.md` to "COMPLETED".
