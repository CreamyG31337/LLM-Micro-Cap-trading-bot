"""
Manual dividend backfill script.
Runs process_dividends_job with a 30-day lookback window.
"""
import sys
from pathlib import Path

# Setup paths
current_dir = Path(__file__).resolve().parent
project_root = current_dir

# 1. Add web_dashboard (needed to import scheduler package)
web_dashboard_path = current_dir / 'web_dashboard'
if str(web_dashboard_path) not in sys.path:
    sys.path.append(str(web_dashboard_path))

# 2. Add root (needed for utils)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scheduler.jobs_dividends import process_dividends_job

if __name__ == "__main__":
    print("🚀 Starting Dividend Backfill (180 Days)...")
    # Run the job with 180-day lookback (approx 6 months back to July/Aug)
    process_dividends_job(lookback_days=180)
    print("✅ Backfill Complete.")
