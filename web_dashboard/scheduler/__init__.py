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
]
