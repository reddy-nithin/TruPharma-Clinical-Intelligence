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
import logging
import tempfile

_vertex_initialized = False
_logger = logging.getLogger("trupharma.config")

# #region agent log f1239c
_debug_init_info: dict = {}
# #endregion


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
        # #region agent log f1239c
        _debug_init_info["secrets_source"] = "st.secrets"
        _debug_init_info["project_from_secrets"] = "FOUND" if project_id else "MISSING"
        _debug_init_info["sa_json_from_secrets"] = "FOUND" if sa_json else "MISSING"
        _logger.warning(f"[DEBUG-f1239c-config] st.secrets read: project={'FOUND' if project_id else 'MISSING'}, sa_json={'FOUND' if sa_json else 'MISSING'}")
        # #endregion
    except Exception as e:
        secrets = None
        project_id = ""
        location = "us-central1"
        sa_json = ""
        # #region agent log f1239c
        _debug_init_info["secrets_source"] = f"st.secrets_error: {e}"
        _debug_init_info["project_from_secrets"] = "MISSING"
        _debug_init_info["sa_json_from_secrets"] = "MISSING"
        _logger.warning(f"[DEBUG-f1239c-config] st.secrets unavailable: {e}")
        # #endregion

    # Fall back to environment variables
    project_id = project_id or os.environ.get("GCP_PROJECT_ID", "")
    location = location or os.environ.get("GCP_LOCATION", "us-central1")

    # #region agent log f1239c
    _debug_init_info["final_project_id"] = "FOUND" if project_id else "MISSING"
    _debug_init_info["final_location"] = location
    _logger.warning(f"[DEBUG-f1239c-config] final project_id={'FOUND' if project_id else 'MISSING'}, location={location}")
    # #endregion

    if not project_id:
        # #region agent log f1239c
        _debug_init_info["init_result"] = "SKIPPED_no_project_id"
        _logger.warning("[DEBUG-f1239c-config] Skipping Vertex AI init — no GCP_PROJECT_ID found")
        # #endregion
        return  # No GCP config available — Vertex AI features will be skipped

    # Propagate secrets into os.environ so engine.py can read them via os.environ.get()
    os.environ["GCP_PROJECT_ID"] = project_id
    os.environ["GCP_LOCATION"] = location

    # If service account JSON is provided (Streamlit Cloud), write to temp file
    if sa_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        try:
            sa_dict = json.loads(sa_json) if isinstance(sa_json, str) else dict(sa_json)
            fd, path = tempfile.mkstemp(suffix=".json", prefix="trupharma_sa_")
            with os.fdopen(fd, "w") as f:
                json.dump(sa_dict, f)
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path
            # #region agent log f1239c
            _debug_init_info["adc_path"] = "written"
            _logger.warning(f"[DEBUG-f1239c-config] GOOGLE_APPLICATION_CREDENTIALS written to temp file")
            # #endregion
        except Exception as e:
            # #region agent log f1239c
            _debug_init_info["adc_path"] = f"error: {e}"
            _logger.warning(f"[DEBUG-f1239c-config] SA JSON write error: {e}")
            # #endregion

    try:
        import vertexai
        vertexai.init(project=project_id, location=location)
        _vertex_initialized = True
        # #region agent log f1239c
        _debug_init_info["init_result"] = "SUCCESS"
        _logger.warning("[DEBUG-f1239c-config] vertexai.init() SUCCESS")
        # #endregion
    except ImportError as e:
        # #region agent log f1239c
        _debug_init_info["init_result"] = f"ImportError: {e}"
        _logger.warning(f"[DEBUG-f1239c-config] vertexai ImportError: {e}")
        # #endregion
    except Exception as e:
        # #region agent log f1239c
        _debug_init_info["init_result"] = f"Error: {e}"
        _logger.warning(f"[DEBUG-f1239c-config] vertexai.init() error: {e}")
        # #endregion


def is_vertex_available() -> bool:
    """Check if Vertex AI is configured and initialized."""
    _init_vertex_ai()
    return _vertex_initialized


# Auto-initialize on import
_init_vertex_ai()
