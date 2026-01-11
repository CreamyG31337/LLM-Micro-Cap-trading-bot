"""
Background Task Scheduler for Web Dashboard
============================================

Uses APScheduler to run background jobs inside the Docker container.
Jobs are managed via the Streamlit admin interface.

Usage:
    from scheduler import get_scheduler, start_scheduler
    
    # Start scheduler (call once at app startup)
    start_scheduler()
    
    # Get scheduler for management
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
"""

import sys
from pathlib import Path

# Add project root to path for utils imports
# This must happen before any imports that use utils.job_tracking
current_dir = Path(__file__).resolve().parent
if current_dir.name == 'scheduler':
    project_root = current_dir.parent.parent
else:
    project_root = current_dir.parent.parent

# CRITICAL: Project root must be FIRST in sys.path to ensure utils.job_tracking
# is found from the project root, not from web_dashboard/utils
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
elif sys.path[0] != str(project_root):
    # If it is in path but not first, move it to front
    if str(project_root) in sys.path:
        sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

# Also ensure web_dashboard is in path for supabase_client imports
# (but AFTER project root so it doesn't shadow utils)
web_dashboard_path = str(current_dir.parent)
if web_dashboard_path not in sys.path:
    sys.path.insert(1, web_dashboard_path)  # Insert at index 1, after project_root

from scheduler.scheduler_core import (
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
    get_job_status,
    run_job_now,
    pause_job,
    resume_job,
    get_all_jobs_status,
    is_scheduler_running,
    get_scheduler_status
)

from scheduler.jobs import (
    AVAILABLE_JOBS,
    refresh_exchange_rates_job,
    social_sentiment_ai_job,
)

__all__ = [
    'get_scheduler',
    'start_scheduler', 
    'shutdown_scheduler',
    'get_job_status',
    'run_job_now',
    'pause_job',
    'resume_job',
    'get_all_jobs_status',
    'is_scheduler_running',
    'get_scheduler_status',
    'AVAILABLE_JOBS',
    'refresh_exchange_rates_job',
    'social_sentiment_ai_job',
]
