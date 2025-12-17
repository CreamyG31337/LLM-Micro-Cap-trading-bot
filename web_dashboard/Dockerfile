# Streamlit Dashboard Dockerfile
# Uses python:3.11-slim to match existing containers on the server
# Includes APScheduler for background tasks

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies and uv (faster Python package installer)
# Note: uv install script installs to ~/.local/bin/uv
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && test -f /root/.local/bin/uv || (echo "uv installation failed" && exit 1) \
    && rm -rf /var/lib/apt/lists/*

# Add uv to PATH
ENV PATH="/root/.local/bin:${PATH}"

# Copy requirements and install Python dependencies with uv (faster than pip)
COPY web_dashboard/requirements.txt ./requirements.txt
RUN /root/.local/bin/uv pip install --system --no-cache -r requirements.txt

# Copy web_dashboard files
COPY web_dashboard/ ./web_dashboard/

# Copy data module for repository access (if needed)
COPY data/ ./data/
COPY config/ ./config/
COPY utils/ ./utils/

# Set PYTHONPATH to include parent directory and web_dashboard
ENV PYTHONPATH=/app:/app/web_dashboard

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"

# Run via entrypoint (starts scheduler + Streamlit)
CMD ["python", "web_dashboard/entrypoint.py"]

