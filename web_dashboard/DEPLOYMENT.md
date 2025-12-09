# Deployment Guide

## Overview

This Streamlit dashboard replaces the previous Flask app. It displays historical portfolio performance graphs and current positions from Supabase.

## Files Created

### Streamlit Application
- `streamlit_app.py` - Main dashboard application
- `streamlit_utils.py` - Data fetching from Supabase
- `chart_utils.py` - Chart generation functions
- `.streamlit/config.toml` - Streamlit configuration

### Deployment Files
- `Dockerfile` - Container definition (uses `python:3.11-slim`)
- `.dockerignore` - Build exclusions
- `Caddyfile` - Reverse proxy configuration
- `.woodpecker.yml` - CI/CD pipeline (in project root)

### Documentation
- `README_STREAMLIT.md` - Streamlit-specific documentation
- `DEPLOYMENT.md` - This file

## Important Files to Keep

- `schema/` - **CRITICAL** - SQL schema files for Supabase
- `supabase_client.py` - Reused by Streamlit app
- `requirements.txt` - Updated with Streamlit

## Files to Archive (Optional)

The following Flask app files are no longer used but kept for reference:
- `app.py` - Old Flask application
- `auth.py` - Flask authentication
- `templates/` - Flask HTML templates
- `vercel.json`, `Procfile`, `railway.json` - Old deployment configs

## Environment Variables

Required for both local and Docker:
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_PUBLISHABLE_KEY` - Your Supabase publishable key (for user authentication)
- `SUPABASE_SECRET_KEY` - Service role key (for admin scripts and debug operations)

## Local Development

1. Activate virtual environment:
   ```powershell
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r web_dashboard/requirements.txt
   ```

3. Create `.env` file in `web_dashboard/`:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_PUBLISHABLE_KEY=your-publishable-key
   SUPABASE_SECRET_KEY=your-secret-key
   ```

4. Run Streamlit:
   ```bash
   cd web_dashboard
   streamlit run streamlit_app.py
   ```

## Docker Build

Build from project root:
```bash
docker build -f web_dashboard/Dockerfile -t trading-dashboard:latest .
```

Run container:
```bash
docker run -d \
  --name trading-dashboard \
  -p 8501:8501 \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_PUBLISHABLE_KEY=your_publishable_key \
  -e SUPABASE_SECRET_KEY=your_secret_key \
  trading-dashboard:latest
```

## Caddy Configuration

1. Update `Caddyfile` with your domain name
2. Place Caddyfile in your Caddy config directory
3. Restart Caddy

The Caddyfile proxies to `localhost:8501` where Streamlit runs.

## Woodpecker CI/CD Setup

1. Add repository to Woodpecker dashboard
2. Set environment variables in Woodpecker:
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_PUBLISHABLE_KEY` - For user authentication
   - `SUPABASE_SECRET_KEY` - For admin scripts and debug operations
   - `SSH_USER` - SSH user for deployment (if using SSH deploy)
   - `SSH_HOST` - Server hostname/IP (if using SSH deploy)
   - `DOCKER_USERNAME` (optional) - For Docker registry
   - `DOCKER_PASSWORD` (optional) - For Docker registry

3. Push to main/master branch to trigger deployment

The `.woodpecker.yml` file will:
- Build Docker image on push/PR
- Deploy to server on push to main/master

## Troubleshooting

### Import Errors
- Make sure `data/` and `config/` directories are copied in Dockerfile
- Check PYTHONPATH is set correctly

### Supabase Connection
- Verify environment variables are set
- Check Supabase URL and key are correct
- Ensure network connectivity to Supabase

### WebSocket Issues
- Caddy must support WebSocket proxying (configured in Caddyfile)
- Check Caddy logs for WebSocket errors

