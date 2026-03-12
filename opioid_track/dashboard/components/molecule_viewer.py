import streamlit as st
import requests
import py3Dmol
from stmol import showmol

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_pubchem_sdf(drug_name: str) -> str | None:
    """
    Fetches the 3D SDF (Structure Data File) string from PubChem for a given drug name.
    We try the 3D record first. If not found, we fallback to 2D.
    """
    try:
        # Request 3D conformer SDF
        url_3d = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/SDF?record_type=3d"
        res = requests.get(url_3d, timeout=5)
        if res.status_code == 200:
            return res.text
            
        # Fallback to 2D if 3D is not available
        url_2d = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{drug_name}/SDF"
        res = requests.get(url_2d, timeout=5)
        if res.status_code == 200:
            return res.text
            
        return None
    except Exception:
        return None

def render_3d_molecule(drug_name: str, width: int = 500, height: int = 400):
    """
    Renders an interactive 3D molecule viewer using py3Dmol and stmol.
    Matches the dark aesthetic of the TruPharma Opioid Intelligence terminal.
    """
    st.markdown(f"<div class='tp-section-header'>Molecular Structure: {drug_name.title()}</div>", unsafe_allow_html=True)
    
    with st.spinner(f"Acquiring {drug_name} conformer from PubChem..."):
        sdf_data = fetch_pubchem_sdf(drug_name)
        
    if not sdf_data:
        st.warning(f"Could not retrieve 3D structure for {drug_name}.")
        return

    # Create py3Dmol view
    view = py3Dmol.view(width=width, height=height)
    view.addModel(sdf_data, "sdf")
    
    # Apply standard clinical terminal dark styling
    view.setStyle({'stick': {'colorscheme': 'blueCarbon', 'radius': 0.15}})
    view.addStyle({'sphere': {'scale': 0.25, 'colorscheme': 'blueCarbon'}})
    
    # Match the background with the TruPharma UI var(--bg-surface) #111e2e
    view.setBackgroundColor('#111e2e')
    view.zoomTo()
    
    # Animate it to grab attention
    view.spin(True)
    
    # Render using stmol in Streamlit
    showmol(view, width=width, height=height)
    
    st.markdown(
        "<div class='tp-chart-caption'>"
        "<span class='tp-chart-caption-icon'>🧬</span>"
        "<strong>Interactive Viewer:</strong> Rotate (left-click), Zoom (scroll), Pan (right-click)."
        "</div>",
        unsafe_allow_html=True
    )
