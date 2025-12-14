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
    
    # Start the scheduler
    try:
        from scheduler import start_scheduler
        started = start_scheduler()
        if started:
            logger.info("✅ Background scheduler started successfully")
        else:
            logger.info("ℹ️ Scheduler was already running")
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")
        logger.error("Dashboard will continue without background tasks")
    
    # Launch Streamlit
    logger.info("Launching Streamlit application...")
    
    # Change to web_dashboard directory so Streamlit can find pages/ correctly
    # Streamlit resolves pages relative to the working directory, not the script location
    os.chdir(web_dashboard_dir)
    
    streamlit_app = "streamlit_app.py"
    
    # Get port from environment or use default
    port = os.environ.get("PORT", "8501")
    
    # Build streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        streamlit_app,
        f"--server.port={port}",
        "--server.address=0.0.0.0",
        "--server.headless=true"
    ]
    
    # Execute streamlit (this will block and run the web server)
    logger.info(f"Running: {' '.join(cmd)}")
    logger.info(f"Working directory: {os.getcwd()}")
    os.execvp(sys.executable, cmd)


if __name__ == "__main__":
    main()
