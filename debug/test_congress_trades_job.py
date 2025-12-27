#!/usr/bin/env python3
"""
Test script for Congress Trades Job
====================================

Tests the fetch_congress_trades_job() function locally to verify:
- FMP API connectivity
- Data parsing (JSON/RSS)
- Pagination logic
- Data cleaning
- Duplicate detection
- AI analysis (if Ollama available)

Usage:
    python debug/test_congress_trades_job.py
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to current directory

print("=" * 70)
print("CONGRESS TRADES JOB TEST")
print("=" * 70)
print()

# Check for FMP_API_KEY
fmp_api_key = os.getenv("FMP_API_KEY")
if not fmp_api_key:
    print("❌ ERROR: FMP_API_KEY not found in environment")
    print("   Please add it to web_dashboard/.env file")
    print("   Example: FMP_API_KEY=your-api-key-here")
    sys.exit(1)

print(f"✅ FMP_API_KEY found: {fmp_api_key[:10]}...{fmp_api_key[-4:]}")
print()

# Check for Supabase credentials
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
supabase_secret = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not supabase_url or not supabase_key:
    print("⚠️  WARNING: Supabase credentials not found")
    print("   The job will fail when trying to save to database")
    print("   But we can still test API connectivity and parsing")
    print()
else:
    print(f"✅ Supabase URL found: {supabase_url}")
    print()

# Check for Ollama
ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
print(f"ℹ️  Ollama URL: {ollama_url}")
print("   (AI analysis will be skipped if Ollama unavailable)")
print()

print("=" * 70)
print("SETTING UP TEST ENVIRONMENT")
print("=" * 70)
print()

try:
    # Mock scheduler_core to avoid scheduler dependencies
    from unittest.mock import MagicMock
    sys.modules['scheduler.scheduler_core'] = MagicMock()
    
    # Create a mock log_job_execution function
    def mock_log_job_execution(job_id, success, message, duration_ms):
        status = "✅" if success else "❌"
        print(f"{status} [{job_id}] {message} ({duration_ms}ms)")
    
    import sys
    mock_module = sys.modules['scheduler.scheduler_core']
    mock_module.log_job_execution = mock_log_job_execution
    
    # Mock job tracking
    try:
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
    except ImportError:
        def mark_job_started(*args, **kwargs): pass
        def mark_job_completed(*args, **kwargs): pass
        def mark_job_failed(*args, **kwargs): pass
    
    # Set up logging
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("✅ Test environment set up")
    print()
    
    print("=" * 70)
    print("RUNNING CONGRESS TRADES JOB")
    print("=" * 70)
    print()
    print("Note: This will fetch data from FMP API and attempt to save to Supabase")
    print("      If you want to limit pages for testing, modify the job function")
    print()
    
    # Import the job function
    from scheduler.jobs import fetch_congress_trades_job
    
    # Run the job
    print("Starting job execution...")
    print()
    fetch_congress_trades_job()
    print()
    print("=" * 70)
    print("✅ Job execution completed!")
    print("=" * 70)
    print()
    print("Check the congress_trades table in Supabase to see the results.")
    print("You can query it with:")
    print("  SELECT * FROM congress_trades ORDER BY created_at DESC LIMIT 10;")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print()
    print("Make sure you're running from the project root and dependencies are installed:")
    print("  pip install -r web_dashboard/requirements.txt")
    sys.exit(1)
except Exception as e:
    print()
    print("=" * 70)
    print("❌ Job execution failed!")
    print("=" * 70)
    print(f"Error: {e}")
    print()
    import traceback
    traceback.print_exc()
    sys.exit(1)

