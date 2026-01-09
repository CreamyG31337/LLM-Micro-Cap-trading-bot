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

# Copy Tailwind input CSS and source files needed for content scanning
# Copy in order: config, input CSS, then templates (for better caching)
COPY web_dashboard/static/css/input.css ./web_dashboard/static/css/input.css
COPY web_dashboard/templates ./web_dashboard/templates

# Build Tailwind CSS (production-optimized, minified)
# Ensure output directory exists and build with error handling
RUN mkdir -p web_dashboard/static/css && \
    npm run build:css && \
    ls -lh web_dashboard/static/css/tailwind.css || \
    (echo "ERROR: Tailwind CSS build failed - output file not found" && exit 1)

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
# Ensure directory exists first, then copy the built CSS file
RUN mkdir -p web_dashboard/static/css
COPY --from=tailwind-builder /app/web_dashboard/static/css/tailwind.css ./web_dashboard/static/css/tailwind.css
RUN test -f web_dashboard/static/css/tailwind.css || (echo "ERROR: Tailwind CSS file not found after copy from builder stage" && exit 1)

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

