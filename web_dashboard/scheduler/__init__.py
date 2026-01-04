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
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from scheduler.scheduler_core import (
    get_scheduler,
    start_scheduler,
    shutdown_scheduler,
    get_job_status,
    run_job_now,
    pause_job,
    resume_job,
    get_all_jobs_status
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
    'AVAILABLE_JOBS',
    'refresh_exchange_rates_job',
    'social_sentiment_ai_job',
]
