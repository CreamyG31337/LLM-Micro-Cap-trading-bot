# Streamlit Portfolio Dashboard

This is the new Streamlit-based dashboard for viewing portfolio performance. It replaces the previous Flask app.

## Structure

- `streamlit_app.py` - Main Streamlit application
- `streamlit_utils.py` - Data fetching utilities from Supabase
- `chart_utils.py` - Chart generation functions
- `supabase_client.py` - Supabase client (reused from Flask app)
- `schema/` - SQL schema files (critical - do not remove)

## Flask App Files

The old Flask app files (app.py, auth.py, templates/, etc.) are still in this directory but are no longer used. They can be archived or removed if needed. The SQL schemas in `schema/` are critical and must be kept.

## Running Locally

1. Activate virtual environment:
   ```powershell
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables (create `.env` file):
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_PUBLISHABLE_KEY=your_publishable_key
   SUPABASE_SECRET_KEY=your_secret_key
   ```

4. Run Streamlit:
   ```bash
   streamlit run streamlit_app.py
   ```

## Docker Deployment

The Dockerfile is in `web_dashboard/Dockerfile` and should be built from the project root:

```bash
docker build -f web_dashboard/Dockerfile -t trading-dashboard:latest .
```

## Caddy Configuration

The `Caddyfile` is configured for reverse proxy. Update the domain name in the file before use.

## Woodpecker CI/CD

The `.woodpecker.yml` file in the project root handles CI/CD. Make sure to:
1. Add the repository to Woodpecker dashboard
2. Set environment variables in Woodpecker:
   - `SUPABASE_URL`
   - `SUPABASE_PUBLISHABLE_KEY` (for user authentication)
   - `SUPABASE_SECRET_KEY` (for admin scripts)
   - `SSH_USER` (if using SSH deploy)
   - `SSH_HOST` (if using SSH deploy)
   - `DOCKER_USERNAME` (optional, if using Docker registry)
   - `DOCKER_PASSWORD` (optional)

