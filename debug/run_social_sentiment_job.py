#!/usr/bin/env python3
"""
Manually Run Social Sentiment Job
=================================

Run the social sentiment job locally for testing.
This will fetch sentiment data for all watched tickers and save to database.
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root and web_dashboard to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

print("=" * 70)
print("MANUALLY TRIGGERING SOCIAL SENTIMENT JOB")
print("=" * 70)
print()
print("This will:")
print("  1. Fetch tickers from watched_tickers and latest_positions")
print("  2. Fetch sentiment from StockTwits for each ticker")
print("  3. Fetch sentiment from Reddit for each ticker")
print("  4. Save metrics to social_metrics table")
print()
print("=" * 70)
print()

try:
    # Import the job function directly (avoid scheduler dependencies)
    # We need to add the scheduler directory to path first
    import sys
    scheduler_path = project_root / 'web_dashboard' / 'scheduler'
    if str(scheduler_path) not in sys.path:
        sys.path.insert(0, str(scheduler_path.parent))
    
    # Import job tracking utilities (may not be available, but job handles it)
    try:
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
    except ImportError:
        # Create dummy functions if job tracking not available
        def mark_job_started(*args, **kwargs): pass
        def mark_job_completed(*args, **kwargs): pass
        def mark_job_failed(*args, **kwargs): pass
    
    # Import the job function directly from the jobs module
    # We need to manually import dependencies to avoid scheduler_core import
    import logging
    import time
    from datetime import datetime, timezone
    from typing import Dict, Any, Optional, List
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Now we can import the job function
    # But we need to mock the scheduler_core import first
    import sys
    from unittest.mock import MagicMock
    
    # Mock the scheduler_core module before importing jobs
    sys.modules['scheduler.scheduler_core'] = MagicMock()
    from scheduler.jobs import fetch_social_sentiment_job
    
    # Run the job
    print("Starting job execution...")
    print()
    fetch_social_sentiment_job()
    print()
    print("=" * 70)
    print("✅ Job completed successfully!")
    print("=" * 70)
    print()
    print("Check the social_metrics table in Postgres to see the results.")
    print("You can also view the data in the Social Sentiment page in the web dashboard.")
    
except Exception as e:
    print()
    print("=" * 70)
    print(f"❌ Job failed: {e}")
    print("=" * 70)
    import traceback
    traceback.print_exc()
    sys.exit(1)

