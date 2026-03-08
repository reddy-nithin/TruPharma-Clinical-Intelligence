import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

def render_knowledge_graph(drug_name: str, drug_data: dict, nlp_data: dict | None, signal_data: list | None):
    """
    Renders an interactive, physics-based dynamic knowledge graph (a "Knowledge Web").
    Centers around the drug and branches out to its components, warnings, and signals.
    """
    nodes = []
    edges = []
    
    # 1. Main Drug Node
    nodes.append(Node(
        id=drug_name,
        label=drug_name.capitalize(),
        size=45,
        color="#3df5c8",  # Teal Bright
        shape="hexagon",
        font={"color": "#e8f0f8", "size": 20, "face": "Syne"}
    ))

    # 2. Add Category Node
    category = drug_data.get("opioid_category", "Unknown Opioid").title()
    cat_node_id = f"cat_{category}"
    nodes.append(Node(
        id=cat_node_id,
        label=category,
        size=25,
        color="#8b5cf6", # Purple
        shape="dot"
    ))
    edges.append(Edge(source=drug_name, target=cat_node_id, label="classified as", color="#2a5278"))

    # 3. Add NLP Boxed Warnings (if any)
    if nlp_data:
        bw = nlp_data.get("boxed_warning", {})
        if bw.get("present"):
            warning_node_id = "label_boxed_warning"
            nodes.append(Node(
                id=warning_node_id,
                label="Boxed Warning",
                size=35,
                color="#ef4444", # Red
                shape="diamond"
            ))
            edges.append(Edge(source=drug_name, target=warning_node_id, label="FDA Warning", color="#ef4444"))
            
            # Add the key warnings as sub-nodes to the boxed warning
            key_warnings = bw.get("key_warnings", [])
            for w in key_warnings[:4]: # Limit to top 4 to prevent clutter
                w_id = f"warn_{w}"
                nodes.append(Node(
                    id=w_id,
                    label=w,
                    size=20,
                    color="#fca5a5", # Light Red
                    shape="box"
                ))
                edges.append(Edge(source=warning_node_id, target=w_id, color="#fca5a5"))

        # Add Overdose Symptoms
        od = nlp_data.get("overdosage", {})
        symptoms = od.get("symptoms", [])
        if symptoms:
            od_node_id = "overdose_symptoms"
            nodes.append(Node(
                id=od_node_id,
                label="Overdose Profile",
                size=30,
                color="#f59e0b", # Amber
                shape="diamond"
            ))
            edges.append(Edge(source=drug_name, target=od_node_id, label="can cause", color="#f59e0b"))
            
            for sym in symptoms[:3]:
                sym_id = f"sym_{sym}"
                nodes.append(Node(
                    id=sym_id,
                    label=sym,
                    size=15,
                    color="#fcd34d", # Light Amber
                    shape="dot"
                ))
                edges.append(Edge(source=od_node_id, target=sym_id, color="#fcd34d"))

    # 4. Add FAERS Signal Nodes
    if signal_data:
        # Filter for consensus signals to keep the graph readable
        consensus = [s for s in signal_data if s.get("consensus_signal")]
        if consensus:
            faers_node = "faers_safety_signals"
            nodes.append(Node(
                id=faers_node,
                label="FAERS Consensus Signals",
                size=30,
                color="#1ec9a0", # Teal Mid
                shape="diamond"
            ))
            edges.append(Edge(source=drug_name, target=faers_node, label="associated with", color="#1ec9a0"))
            
            # Add top 5 reactions
            top_sigs = sorted(consensus, key=lambda x: -x.get("report_count", 0))[:5]
            for sig in top_sigs:
                rxn = sig["reaction"]
                prr = round(sig.get("prr", {}).get("value", 0), 1)
                rxn_id = f"rxn_{rxn}"
                nodes.append(Node(
                    id=rxn_id,
                    label=f"{rxn}\n(PRR: {prr})",
                    size=20,
                    color="#3d5a74", # Muted Blue
                    shape="box"
                ))
                edges.append(Edge(source=faers_node, target=rxn_id, color="#3d5a74"))

    # If the network is just the drug and category, it might be too small, but it works.
    
    # Configure the physics logic and visual style of the graph using valid vis-network options
    config = Config(
        width='100%',
        height=500,
        directed=True, 
        physics=True, 
        hierarchical=False,
    )
    
    # Overcome a known streamlit-agraph bug where groups=None crashes the network by injecting an empty dict
    config.__dict__["groups"] = {}
    
    # Manually inject valid vis-network configurations into the kwargs dictionary
    config.__dict__.update({
        "interaction": {
            "hover": True,
            "dragNodes": True,
            "zoomView": True,
            "dragView": True,
        },
        "nodes": {
            "borderWidth": 2,
            "borderWidthSelected": 4,
            "font": {"color": "#e8f0f8", "face": "Syne"}
        },
        "edges": {
            "color": {"color": "#475569", "highlight": "#94a3b8"}, 
            "smooth": {"type": "continuous"}
        }
    })

    st.markdown("<div class='tp-section-header'>Interactive Knowledge Web</div>", unsafe_allow_html=True)
    
    with st.spinner("Initializing physics engine for Knowledge Web..."):
        agraph(nodes=nodes, edges=edges, config=config)
        
    st.markdown(
        "<div class='tp-chart-caption'>"
        "<span class='tp-chart-caption-icon'>🕸️</span>"
        "<strong>Knowledge Web:</strong> A physics-based view of clinical relationships. Click and drag nodes to interact with the web."
        "</div>",
        unsafe_allow_html=True
    )
