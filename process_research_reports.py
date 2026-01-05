#!/usr/bin/env python3
"""
Process Research Reports
========================

Processes PDF research reports from the Research/ directory:
- Scans for new PDF files
- Adds date prefixes if missing
- Sanitizes filenames (spaces → underscores)
- Extracts text and generates AI summaries
- Stores in database
- Uploads to server if running locally and configured
"""

import sys
from pathlib import Path

# Add project root and web_dashboard to path
PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DASHBOARD_PATH = PROJECT_ROOT / "web_dashboard"

if str(WEB_DASHBOARD_PATH) not in sys.path:
    sys.path.insert(0, str(WEB_DASHBOARD_PATH))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables (needed for server upload config)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from root .env
    load_dotenv(PROJECT_ROOT / "web_dashboard" / ".env")  # Also try web_dashboard/.env
except ImportError:
    pass  # dotenv not available, will use system env vars

# Import and run the job
try:
    from web_dashboard.scheduler.jobs_research import process_research_reports_job
    
    if __name__ == "__main__":
        process_research_reports_job()
except ImportError as e:
    print(f"❌ Error importing job module: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error processing research reports: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

