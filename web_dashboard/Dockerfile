# Streamlit Dashboard Dockerfile
# Uses python:3.11-slim to match existing containers on the server
# Includes APScheduler for background tasks
# Multi-stage build: Build Tailwind CSS first, then Python app

# Stage 1: Build Tailwind CSS
FROM node:20-alpine AS tailwind-builder
WORKDIR /app

# Copy package files for dependency installation (better layer caching)
COPY package.json ./
COPY tailwind.config.js ./

# Install npm dependencies (cached layer - only rebuilds if package.json changes)
RUN npm install

# Copy Tailwind input CSS
COPY web_dashboard/static/css/input.css ./web_dashboard/static/css/

# Copy source files needed for Tailwind content scanning
COPY web_dashboard/templates ./web_dashboard/templates
COPY web_dashboard/static ./web_dashboard/static

# Build Tailwind CSS (production-optimized, minified)
RUN npm run build:css

# Stage 2: Python app
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

# Copy entire project (cleaner than selective copying)
COPY . /app

# Copy built Tailwind CSS from builder stage
COPY --from=tailwind-builder /app/web_dashboard/static/css/tailwind.css ./web_dashboard/static/css/tailwind.css

# Set PYTHONPATH to include project root FIRST, then web_dashboard
# IMPORTANT: Order matters! /app must come before /app/web_dashboard 
# to prevent web_dashboard/utils/ from shadowing root utils/ directory
ENV PYTHONPATH=/app:/app/web_dashboard

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"

# Run via entrypoint (starts scheduler + Streamlit)
CMD ["python", "web_dashboard/entrypoint.py"]

