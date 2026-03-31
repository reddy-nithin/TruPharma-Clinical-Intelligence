# ══════════════════════════════════════════════════════════════
#  TruPharma Clinical Intelligence — Dockerfile
# ══════════════════════════════════════════════════════════════
#  Single-stage Python 3.11 image for the Streamlit app.
#  Data/assets are volume-mounted at runtime (not baked in).
#  Runs as non-root user for security.
# ══════════════════════════════════════════════════════════════

FROM python:3.11.12-slim-bookworm

LABEL maintainer="TruPharma Team"
LABEL description="TruPharma Clinical Intelligence — AI-powered drug safety platform"

WORKDIR /app

# ── System dependencies ──────────────────────────────────────
# build-essential: needed for numpy/scikit-learn/faiss C extensions
# curl: needed for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl && \
    rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
# Copy requirements first for Docker layer caching
COPY requirements.txt ./requirements.txt
COPY opioid_track/requirements.txt ./requirements_opioid.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        -r requirements.txt \
        -r requirements_opioid.txt && \
    pip install --no-cache-dir requests lxml

# ── Application source code ──────────────────────────────────
# (Data, assets, logs are volume-mounted — not copied here)
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY opioid_track/__init__.py ./opioid_track/__init__.py
COPY opioid_track/config.py ./opioid_track/config.py
COPY opioid_track/core/ ./opioid_track/core/
COPY opioid_track/dashboard/ ./opioid_track/dashboard/
COPY opioid_track/ingestion/ ./opioid_track/ingestion/
COPY opioid_track/agents/ ./opioid_track/agents/
COPY opioid_track/tests/ ./opioid_track/tests/
COPY .streamlit/ ./.streamlit/

# ── Create volume mount points ───────────────────────────────
# These directories will be populated by docker-compose volumes
RUN mkdir -p data/kg \
             opioid_track/data \
             logs \
             src/frontend/assets \
             src/frontend/static

# ── Non-root user (security) ─────────────────────────────────
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# ── Expose Streamlit port ────────────────────────────────────
EXPOSE 8501

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────
ENTRYPOINT ["streamlit", "run", "src/frontend/app.py", \
    "--server.port=8501", \
    "--server.address=0.0.0.0", \
    "--server.headless=true", \
    "--browser.gatherUsageStats=false"]
