# TruPharma Visual Enhancements - Implementation Plan

This document outlines the technical approach to integrate three high-fidelity, "wow-factor" visual elements into the TruPharma Opioid Intelligence platform, maintaining the dark-mode "Clinical Intelligence Terminal" aesthetic.

## Proposed Components

### Component 1: 3D Molecular Viewer (Drug Explorer)
We will use `py3Dmol` to render the actual 3D conformation of the selected opioid molecule. 
- **Data Source**: We will fetch the SDF (Structure Data File) dynamically from the PubChem REST API using the drug's name or CID.
- **Rendering**: The molecule will be rendered using a "stick" or "sphere" representation, colored by atom type.
- **Animation**: The viewer will include automatic rotation upon load (the "draw themselves" requirement) to grab attention immediately.

#### Target Implementation: `opioid_track/dashboard/components/molecule_viewer.py`
- Create a reusable Streamlit component `render_3d_molecule(drug_name)` that fetches the PubChem 3D SDF and outputs the `py3Dmol` object using `st_py3dmol`.

---

### Component 2: 3D Heat Globe (Geographic Intelligence)
We will upgrade the 2D Plotly choropleth maps to full 3D environments using Uber's `Deck.GL` via the `pydeck` Python library.
- **Visuals**: A dark map style (`mapbox://styles/mapbox/dark-v11` or Carto Dark Matter).
- **Geometry**: Instead of coloring flat polygons, we will use `pdk.Layer("ColumnLayer")` or `HexagonLayer` to generate 3D pillars that extrude vertically based on the CDC Mortality Rate or CMS Prescribing Rate. This physically demonstrates the magnitude of the crisis.
- **Interactivity**: Users will be able to pitch and rotate the map in 3D space.

#### Target Implementation: `opioid_track/dashboard/components/deckgl_map.py`
- Create `render_3d_geographic_map(dataframe, metric_col, lat_col, lon_col)`.

---

### Component 3: Dynamic Knowledge Graph (Signals / Explorer)
Instead of static tables indicating adverse events or drug relationships, we will build a floating, physics-based network using `streamlit-agraph` (a wrapper for `vis.js`).
- **Nodes**: The central node is the primary Opioid. Connected nodes represent key FDA label warnings (e.g., "Respiratory Depression"), mechanisms of action (e.g., "Mu-Receptor Agonist"), and calculated FAERS signals.
- **Animations**: The graph utilizes force-directed physics. When the page loads, the nodes literally pull together and stabilize on screen. Users can click and drag them.

#### Target Implementation: `opioid_track/dashboard/components/network_graph.py`
- Create `render_knowledge_graph(drug_name, nlp_insights, signal_data)`.

## Technical Requirements
- `py3Dmol>=2.0.4`
- `pydeck>=0.8.0`
- `streamlit-agraph>=0.0.45`
