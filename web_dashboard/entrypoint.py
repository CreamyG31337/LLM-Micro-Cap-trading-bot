#!/usr/bin/env python3
"""
Dashboard Entrypoint
====================

Starts the background scheduler before launching Streamlit.
This ensures scheduled tasks run alongside the web application.

Usage:
    python entrypoint.py
    
    # Or via the shell script:
    ./start.sh
"""

import os
import sys
import logging
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Start scheduler and Streamlit."""
    
    # Add web_dashboard to Python path
    web_dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, web_dashboard_dir)
    
    # Also add parent directory for imports like 'data', 'config', etc.
    parent_dir = os.path.dirname(web_dashboard_dir)
    sys.path.insert(0, parent_dir)
    
    logger.info("=" * 50)
    logger.info("Starting Trading Dashboard with Background Tasks")
    logger.info("=" * 50)
    
    # NOTE: Scheduler is initialized inside streamlit_app.py via @st.cache_resource
    # This ensures it runs in the same process as Streamlit (subprocess.run creates a new process)
    logger.info("ℹ️ Scheduler will be initialized by Streamlit on first request")
    
    # Launch Streamlit
    logger.info("Launching Streamlit application...")
    
    # Verify pages directory exists
    pages_dir = os.path.join(web_dashboard_dir, "pages")
    admin_page = os.path.join(pages_dir, "admin.py")
    
    if not os.path.exists(pages_dir):
        logger.error(f"❌ Pages directory not found at: {pages_dir}")
        logger.error("Streamlit pages will not work. Check Dockerfile COPY command.")
    elif not os.path.exists(admin_page):
        logger.warning(f"⚠️ Admin page not found at: {admin_page}")
        logger.warning("Admin dashboard will not be accessible.")
    else:
        logger.info(f"✅ Pages directory found at: {pages_dir}")
        logger.info(f"✅ Admin page found at: {admin_page}")
    
    streamlit_app = os.path.join(web_dashboard_dir, "streamlit_app.py")
    
    # Get port from environment or use default
    port = os.environ.get("PORT", "8501")
    
    # Build streamlit command
    # Run Streamlit from web_dashboard directory so it can find pages/ correctly
    # Streamlit resolves pages relative to the directory containing the main script
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "streamlit_app.py",  # Use relative path - Streamlit will look for pages/ in same directory
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ]
    
    # Execute streamlit from web_dashboard directory (this will block and run the web server)
    # Use subprocess with cwd to ensure Streamlit runs from the correct directory
    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"Working directory: {web_dashboard_dir}")
    subprocess.run(cmd, cwd=web_dashboard_dir, check=False)


if __name__ == "__main__":
    main()
