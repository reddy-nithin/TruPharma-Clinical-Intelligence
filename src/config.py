"""
config.py · Shared Vertex AI Initialization
============================================
Initializes Vertex AI SDK once at import time.
Reads GCP_PROJECT_ID, GCP_LOCATION from environment or Streamlit secrets.
For Streamlit Cloud: reads service account JSON from st.secrets and writes
to a temp file for Application Default Credentials.
"""

import os
import json
import tempfile

_vertex_initialized = False


def _init_vertex_ai():
    """Initialize Vertex AI SDK. Safe to call multiple times (idempotent)."""
    global _vertex_initialized
    if _vertex_initialized:
        return

    # Try Streamlit secrets first (for Streamlit Cloud deployment)
    try:
        import streamlit as st
        secrets = st.secrets
        project_id = secrets.get("GCP_PROJECT_ID", "")
        location = secrets.get("GCP_LOCATION", "us-central1")
        sa_json = secrets.get("GCP_SERVICE_ACCOUNT_JSON", "")
    except Exception:
        secrets = None
        project_id = ""
        location = "us-central1"
        sa_json = ""

    # Fall back to environment variables
    project_id = project_id or os.environ.get("GCP_PROJECT_ID", "")
    location = location or os.environ.get("GCP_LOCATION", "us-central1")

    if not project_id:
        return  # No GCP config available — Vertex AI features will be skipped

    # If service account JSON is provided (Streamlit Cloud), write to temp file
    if sa_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            sa_dict = json.loads(sa_json) if isinstance(sa_json, str) else dict(sa_json)
            fd, path = tempfile.mkstemp(suffix=".json", prefix="trupharma_sa_")
            with os.fdopen(fd, "w") as f:
                json.dump(sa_dict, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
        except Exception:
            pass  # Best effort — ADC may work via other means

    try:
        import vertexai
        vertexai.init(project=project_id, location=location)
        _vertex_initialized = True
    except ImportError:
        pass  # google-cloud-aiplatform not installed


def is_vertex_available() -> bool:
    """Check if Vertex AI is configured and initialized."""
    _init_vertex_ai()
    return _vertex_initialized


# Auto-initialize on import
_init_vertex_ai()
